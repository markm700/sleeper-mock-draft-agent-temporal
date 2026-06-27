"""
Workflow to simulate a full mock draft using trained owner models.

Orchestrates the entire draft: fetches context, then for each pick in snake
draft order, runs the prediction activity with the appropriate owner's model
and removes the selected player from the available pool.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.ml.calculate_adp import CalculateADPFromPicksParams, calculate_adp_from_picks
    from activities.ml.models.manage_model import list_models
    from activities.ml.predictions.get_draft_simulation_context import (
        GetDraftSimulationContextParams,
        get_draft_simulation_context,
    )
    from activities.ml.predictions.predict_player_pick import (
        BatchPredictOwnerParams,
        batch_predict_owner,
    )


@dataclass
class MockDraftSimulationWorkflowParams:
    """
    Input parameters for MockDraftSimulationWorkflow.

    Fields:
        league_id: Primary Sleeper league identifier (current season).
        additional_league_ids: Historical league_ids for ADP + owner profiles.
        num_rounds: Number of draft rounds (default 15).
        draft_type: Draft format — "snake" or "linear" (default "snake").
        personality_influence_scale: Personality weight 0.0–1.0. None randomizes per pick.
    """

    league_id: str
    additional_league_ids: Optional[List[str]] = None
    num_rounds: int = 15
    draft_type: str = "snake"
    personality_influence_scale: Optional[float] = None
    adp_influence_scale: float = 4.0


@workflow.defn(name="mock-draft-simulation")
class MockDraftSimulationWorkflow:
    """
    Simulate a complete mock draft using trained team owner models.

    Orchestrates the following steps:

    1. **list_models** — discover which owner models are available.
    2. **calculate_adp_from_picks** — compute ADP for player ranking.
    3. **get_draft_simulation_context** — fetch draft order, candidate players,
       and owner profiles from the database.
    4. **batch_predict_owner** (per pick) — for each pick in draft order,
       score remaining candidates and select the top prediction.

    Returns the full simulated draft board with pick-by-pick results.
    """

    @workflow.run
    async def run(self, params: MockDraftSimulationWorkflowParams) -> Dict[str, Any]:
        """
        Execute the mock draft simulation.

        Args:
            params: MockDraftSimulationWorkflowParams with league and draft config.

        Returns:
            Dict[str, Any]: {
                "draft_board": [{pick_no, round, user_id, display_name, player_id, ...}],
                "summary_by_owner": {user_id: {picks: [...], display_name: str}},
                "num_picks": int,
                "num_rounds": int,
            }
        """
        wf_hex = workflow.info().run_id[-4:]
        print(
            f"MockDraftSimulationWorkflow starting — league={params.league_id} "
            f"rounds={params.num_rounds} type={params.draft_type}"
        )

        activity_retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=5),
            maximum_interval=timedelta(minutes=2),
            backoff_coefficient=2.0,
        )

        # ------------------------------------------------------------------
        # Step 1: List available trained models
        # ------------------------------------------------------------------
        models_result = await workflow.execute_activity(
            list_models,
            start_to_close_timeout=timedelta(seconds=15),
            activity_id=f"activity-list_models-{wf_hex}",
            retry_policy=activity_retry_policy,
        )
        available_models: List[Dict[str, Any]] = models_result.get("models", [])
        # Map user_id → model_name from naming convention: owner_{user_id}_{league_id}_v1
        model_map: Dict[str, str] = {}
        for m in available_models:
            name = m["model_name"]
            parts = name.split("_")
            # Expected: owner_{user_id}_{league_id}_v1
            if len(parts) >= 3 and parts[0] == "owner":
                user_id = parts[1]
                model_map[user_id] = name

        print(f"Found {len(model_map)} trained owner models")

        if not model_map:
            print("No trained models found — cannot simulate draft.")
            return {
                "draft_board": [],
                "summary_by_owner": {},
                "num_picks": 0,
                "num_rounds": params.num_rounds,
                "error": "no_trained_models",
            }

        # ------------------------------------------------------------------
        # Step 2: Calculate ADP
        # ------------------------------------------------------------------
        adp_result = await workflow.execute_activity(
            calculate_adp_from_picks,
            CalculateADPFromPicksParams(
                league_id=params.league_id,
                weighted=True,
                additional_league_ids=params.additional_league_ids,
            ),
            start_to_close_timeout=timedelta(seconds=60),
            activity_id=f"activity-calculate_adp-{params.league_id}-{wf_hex}",
            retry_policy=activity_retry_policy,
        )
        adp_data = adp_result.get("adp_data", {})
        print(
            f"ADP calculated: {adp_result['num_players']} players, "
            f"{adp_result['num_picks']} picks"
        )

        # ------------------------------------------------------------------
        # Step 3: Get draft simulation context
        # ------------------------------------------------------------------
        context_result = await workflow.execute_activity(
            get_draft_simulation_context,
            GetDraftSimulationContextParams(
                league_id=params.league_id,
                additional_league_ids=params.additional_league_ids,
                num_rounds=params.num_rounds,
                adp_data=adp_data,
            ),
            start_to_close_timeout=timedelta(seconds=60),
            activity_id=f"activity-get_draft_context-{params.league_id}-{wf_hex}",
            retry_policy=activity_retry_policy,
        )

        draft_order = context_result["draft_order"]
        candidate_players = context_result["candidate_players"]
        owner_profiles = context_result["owner_profiles"]
        num_teams = context_result["num_teams"]

        print(
            f"Draft context ready: {num_teams} teams, "
            f"{len(candidate_players)} candidates"
        )

        # ------------------------------------------------------------------
        # Step 4: Simulate draft pick by pick
        # ------------------------------------------------------------------
        draft_board: List[Dict[str, Any]] = []
        available_players = list(candidate_players)  # mutable copy
        drafted_player_ids: set = set()

        # Build roster trackers for draft context computation
        owner_rosters: Dict[str, List[Dict[str, Any]]] = {
            entry["user_id"]: [] for entry in draft_order
        }

        total_picks = num_teams * params.num_rounds

        for round_num in range(1, params.num_rounds + 1):
            # Snake draft: odd rounds go 1→N, even rounds go N→1
            if params.draft_type == "snake":
                if round_num % 2 == 1:
                    round_order = draft_order
                else:
                    round_order = list(reversed(draft_order))
            else:
                round_order = draft_order

            for slot_idx, drafter in enumerate(round_order):
                pick_no = len(draft_board) + 1
                user_id = drafter["user_id"]
                display_name = drafter["display_name"]

                # Get remaining candidates (exclude already drafted)
                remaining = [
                    p for p in available_players
                    if p["player_id"] not in drafted_player_ids
                ]

                if not remaining:
                    print(f"Pick {pick_no}: No candidates remaining — ending draft")
                    break

                # Build draft context for this pick
                roster = owner_rosters[user_id]
                draft_context = _build_draft_context(
                    roster, round_num, pick_no, total_picks, num_teams
                )

                # Get owner profile
                profile = owner_profiles.get(user_id, {})

                # Check if owner has a trained model
                model_name = model_map.get(user_id)

                if model_name:
                    # Use model to predict
                    # Limit candidates to top 50 by ADP for efficiency
                    scored_candidates = remaining[:50]

                    prediction_result = await workflow.execute_activity(
                        batch_predict_owner,
                        BatchPredictOwnerParams(
                            player_features=scored_candidates,
                            draft_context=draft_context,
                            owner_profile=profile,
                            user_id=user_id,
                            model_name=model_name,
                            personality_influence_scale=params.personality_influence_scale,
                            adp_influence_scale=params.adp_influence_scale,
                        ),
                        start_to_close_timeout=timedelta(seconds=30),
                        activity_id=f"activity-predict-r{round_num}-p{pick_no}-{wf_hex}",
                        retry_policy=activity_retry_policy,
                    )

                    predictions = prediction_result.get("predictions", [])
                    if predictions:
                        # Pick the top-ranked player
                        top_pick = predictions[0]
                        picked_player_id = top_pick["player_id"]
                    else:
                        # Fallback to ADP
                        picked_player_id = remaining[0]["player_id"]
                else:
                    # No model — use ADP-based pick (first available)
                    picked_player_id = remaining[0]["player_id"]

                # Find picked player info
                picked_player = next(
                    (p for p in remaining if p["player_id"] == picked_player_id),
                    remaining[0],
                )

                # Record the pick
                pick_entry = {
                    "pick_no": pick_no,
                    "round": round_num,
                    "draft_slot": drafter["draft_slot"],
                    "user_id": user_id,
                    "display_name": display_name,
                    "player_id": picked_player["player_id"],
                    "player_name": picked_player["full_name"],
                    "position": picked_player["position"],
                    "team": picked_player.get("team"),
                    "adp": picked_player.get("adp", 999.0),
                    "model_used": model_name or "adp_fallback",
                }
                draft_board.append(pick_entry)
                drafted_player_ids.add(picked_player_id)
                owner_rosters[user_id].append(picked_player)

                if pick_no % 10 == 0 or pick_no <= 5:
                    print(
                        f"Pick {pick_no} (R{round_num}): "
                        f"{display_name} → {picked_player['full_name']} "
                        f"({picked_player['position']})"
                    )

        # ------------------------------------------------------------------
        # Build summary by owner
        # ------------------------------------------------------------------
        summary_by_owner: Dict[str, Dict[str, Any]] = {}
        for entry in draft_order:
            uid = entry["user_id"]
            owner_picks = [p for p in draft_board if p["user_id"] == uid]
            summary_by_owner[uid] = {
                "display_name": entry["display_name"],
                "draft_slot": entry["draft_slot"],
                "picks": owner_picks,
                "positions_drafted": [p["position"] for p in owner_picks],
            }

        print(
            f"MockDraftSimulationWorkflow complete — "
            f"{len(draft_board)} picks across {params.num_rounds} rounds"
        )

        return {
            "draft_board": draft_board,
            "summary_by_owner": summary_by_owner,
            "num_picks": len(draft_board),
            "num_rounds": params.num_rounds,
            "num_teams": num_teams,
            "draft_type": params.draft_type,
            "league_id": params.league_id,
        }


def _build_draft_context(
    roster: List[Dict[str, Any]],
    round_num: int,
    pick_no: int,
    total_picks: int,
    num_teams: int,
) -> Dict[str, Any]:
    """
    Build the 8-key draft context dict for the current pick.

    Args:
        roster: Players already drafted by this owner.
        round_num: Current round number.
        pick_no: Overall pick number.
        total_picks: Total picks in the draft.
        num_teams: Number of teams in the league.

    Returns:
        Dict[str, Any]: Context dict matching _prepare_draft_context_features keys.
    """
    # Count positions already on roster
    pos_counts: Dict[str, int] = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "K": 0, "DEF": 0}
    for p in roster:
        pos = p.get("position", "")
        if pos in pos_counts:
            pos_counts[pos] += 1

    # Standard league needs
    rb_slots = max(0, 4 - pos_counts["RB"])
    wr_slots = max(0, 5 - pos_counts["WR"])
    qb_need = 1.0 if pos_counts["QB"] < 2 else 0.0
    flex_need = 0.5 if (rb_slots + wr_slots) > 3 else 0.2

    # Roster needs score: higher = more positions needed
    filled = sum(pos_counts.values())
    total_slots = 15  # typical roster size
    roster_needs_score = max(0.0, (total_slots - filled) / total_slots)

    picks_remaining = total_picks - pick_no

    return {
        "roster_needs_score": roster_needs_score,
        "draft_position": pick_no,
        "picks_remaining": picks_remaining,
        "round": round_num,
        "qb_need": qb_need,
        "rb_slots_remaining": rb_slots,
        "wr_slots_remaining": wr_slots,
        "flex_need": flex_need,
    }
