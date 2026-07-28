"""
Activity to fetch all context needed for a mock draft simulation.

Retrieves draftable players (top N by ADP), owner profiles from historical
picks, and draft order from the league's most recent draft configuration.
"""

from collections import defaultdict
from pydantic.dataclasses import dataclass
from typing import Any, Dict, List, Optional

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import Draft, DraftPick, Player, TeamOwner


@dataclass(frozen=True, kw_only=True)
class GetDraftSimulationContextParams:
    """
    Parameters for fetching mock draft simulation context.

    Fields:
        league_id: Primary Sleeper league identifier (current season).
        additional_league_ids: Historical league_ids to compute owner profiles from.
        num_rounds: Number of draft rounds to simulate (default 15).
        roster_size: Number of roster spots / teams in the league (default 10).
        positions: Fantasy-relevant positions to include in candidate pool.
        adp_data: Pre-computed ADP dict from calculate_adp_from_picks.
    """

    league_id: str
    additional_league_ids: Optional[List[str]] = None
    num_rounds: int = 15
    roster_size: int = 10
    positions: Optional[List[str]] = None
    adp_data: Optional[Dict[str, Any]] = None


@activity.defn(name="get_draft_simulation_context")
async def get_draft_simulation_context(
    input: GetDraftSimulationContextParams,
) -> Dict[str, Any]:
    """
    Fetch draftable players, owner profiles, and draft order for a simulation.

    Args:
        input: GetDraftSimulationContextParams with league and draft config.

    Returns:
        Dict[str, Any]: {
            "draft_order": [{user_id, display_name, draft_slot}, ...],
            "candidate_players": [{player_id, full_name, position, ...}, ...],
            "owner_profiles": {user_id: {profile_dict}},
            "num_rounds": int,
            "num_teams": int,
            "total_picks": int,
        }
    """
    postgres = get_postgres_client_manager()
    positions = input.positions or ["QB", "RB", "WR", "TE", "K", "DEF"]

    try:
        with postgres.session_scope() as session:
            # --- Draft Order ---
            # Get the most recent draft for this league to determine order
            draft = (
                session.query(Draft)
                .filter(Draft.league_id == input.league_id)
                .order_by(Draft.created.desc())
                .first()
            )

            # Get team owners in the current league
            owners = (
                session.query(TeamOwner)
                .filter(
                    TeamOwner.league_id == input.league_id,
                    TeamOwner.is_bot == False,
                )
                .all()
            )

            # Build draft order from draft_order JSON or fallback to roster order
            draft_order_list: List[Dict[str, Any]] = []
            if draft and draft.draft_order:
                # draft_order is {user_id: draft_position} mapping
                owner_display_names = {o.user_id: o.display_name for o in owners}

                sorted_slots = sorted(draft.draft_order.items(), key=lambda x: int(x[1]))
                draft_order_list = [{
                            "user_id": user_id_key,
                            "display_name": display_name,
                            "draft_slot": int(slot),
                            "roster_id": int(slot),
                        } for user_id_key, slot in sorted_slots 
                        if (display_name := owner_display_names.get(user_id_key)) is not None
                    ]
            else:
                # Fallback: alphabetical by display_name
                for idx, owner in enumerate(sorted(owners, key=lambda o: o.display_name or ""), 1):
                    draft_order_list.append({
                        "user_id": owner.user_id,
                        "display_name": owner.display_name,
                        "draft_slot": idx,
                        "roster_id": idx,
                    })

            num_teams = len(draft_order_list)
            total_picks = num_teams * input.num_rounds

            # --- Candidate Players ---
            # Get top draftable players by ADP (or all active in fantasy positions)
            player_query = (
                session.query(Player)
                .filter(
                    Player.position.in_(positions),
                    Player.status == "Active",
                )
            )
            all_players = player_query.all()

            # Enrich with ADP and sort
            adp_lookup = input.adp_data or {}
            candidate_players: List[Dict[str, Any]] = [{
                    "player_id": player.player_id,
                    "full_name": player.full_name,
                    "position": player.position,
                    "age": player.age,
                    "years_exp": player.years_exp,
                    "status": player.status,
                    "team": player.team,
                    "injury_status": player.injury_status,
                    "adp": adp_val,
                    "adp_std": adp_info.get("std_dev", 0.0),
                    "times_drafted": adp_info.get("times_drafted", 0),
                    "projected_points": 0.0,
                    "position_rank": 999,
                } for player in all_players 
                if (adp_info := adp_lookup.get(player.player_id, {})) is not None and 
                    (adp_val := adp_info.get("adp", 999.0)) is not None
            ]

            # Sort by ADP (best first), limit to 2x total picks for efficiency
            candidate_players.sort(key=lambda p: p["adp"])
            max_candidates = max(total_picks * 2, 300)
            candidate_players = candidate_players[:max_candidates]

            # --- Owner Profiles ---
            # Compute historical profile for each owner from their picks
            all_league_ids = [input.league_id]
            if input.additional_league_ids:
                all_league_ids.extend(input.additional_league_ids)

            # Get all drafts across leagues
            drafts = (
                session.query(Draft)
                .filter(Draft.league_id.in_(all_league_ids))
                .all()
            )
            draft_ids = [d.draft_id for d in drafts]

            # Get all picks from those drafts
            all_picks: List[DraftPick] = []
            if draft_ids:
                all_picks = (
                    session.query(DraftPick)
                    .filter(DraftPick.draft_id.in_(draft_ids))
                    .order_by(DraftPick.draft_id, DraftPick.pick_no)
                    .all()
                )

            # Build player lookup for profile computation
            all_player_ids = list({p.player_id for p in all_picks if p.player_id})
            players_map: Dict[str, Player] = {}
            if all_player_ids:
                players_db = (
                    session.query(Player)
                    .filter(Player.player_id.in_(all_player_ids))
                    .all()
                )
                players_map = {p.player_id: p for p in players_db}

            # Compute per-owner profiles
            owner_profiles: Dict[str, Dict[str, Any]] = {}
            owner_user_ids = {entry["user_id"] for entry in draft_order_list}

            for user_id in owner_user_ids:
                owner_picks = [p for p in all_picks if p.picked_by == user_id]
                if owner_picks:
                    owner_profiles[user_id] = _compute_owner_profile(
                        owner_picks, players_map, adp_lookup
                    )
                else:
                    owner_profiles[user_id] = _default_owner_profile()

        activity.logger.info(
            f"Draft simulation context: {num_teams} teams, {total_picks} picks, "
            f"{len(candidate_players)} candidates, {len(owner_profiles)} profiles"
        )

        return {
            "draft_order": draft_order_list,
            "candidate_players": candidate_players,
            "owner_profiles": owner_profiles,
            "num_rounds": input.num_rounds,
            "num_teams": num_teams,
            "total_picks": total_picks,
        }

    except Exception as e:
        activity.logger.error(f"Failed to get draft simulation context: {str(e)}")
        raise


def _compute_owner_profile(
    owner_picks: List[DraftPick],
    players_map: Dict[str, Any],
    adp_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute 26-dim owner profile from historical picks.

    Args:
        owner_picks: All picks made by this owner across drafts.
        players_map: Mapping of player_id to Player ORM objects.
        adp_data: ADP lookup for deviation calculation.

    Returns:
        Dict[str, Any]: Named profile features matching _prepare_owner_profile_features keys.
    """
    total = len(owner_picks)
    if total == 0:
        return _default_owner_profile()

    # Split picks into early (rounds 1-5), mid (6-10), late (11+)
    early_picks = [p for p in owner_picks if p.round <= 5]
    mid_picks = [p for p in owner_picks if 6 <= p.round <= 10]
    late_picks = [p for p in owner_picks if p.round > 10]

    def position_rates(picks: List[DraftPick]) -> Dict[str, float]:
        if not picks:
            return {"QB": 0.0, "RB": 0.0, "WR": 0.0, "TE": 0.0, "K": 0.0, "DEF": 0.0}
        n = len(picks)
        counts: Dict[str, int] = defaultdict(int)
        for p in picks:
            player = players_map.get(p.player_id)
            pos = player.position if player else "UNK"
            counts[pos] += 1
        return {pos: counts.get(pos, 0) / n for pos in ["QB", "RB", "WR", "TE", "K", "DEF"]}

    early_rates = position_rates(early_picks)
    mid_rates = position_rates(mid_picks)
    late_rates = position_rates(late_picks)

    # ADP deviation: how far from expected ADP do they pick?
    deviations = [(p.pick_no - expected_adp) for p in owner_picks 
                if (adp_info := adp_data.get(p.player_id, {})) is not None and 
                (expected_adp := adp_info.get("adp", p.pick_no)) is not None
        ]

    avg_deviation = sum(deviations) / len(deviations) if deviations else 0.0
    # Normalize to 0-1 range (negative = reaching, positive = value picks)
    adp_deviation_norm = min(max((avg_deviation + 50) / 100, 0.0), 1.0)

    # Sleeper pick rate (picks much earlier than ADP)
    sleeper_picks = sum(1 for d in deviations if d < -10)
    sleeper_rate = sleeper_picks / total

    # Pick consistency (lower std in deviation = more consistent)
    if len(deviations) > 1:
        mean_d = sum(deviations) / len(deviations)
        var_d = sum((d - mean_d) ** 2 for d in deviations) / len(deviations)
        consistency = max(0.0, 1.0 - (var_d ** 0.5) / 50.0)
    else:
        consistency = 0.5

    return {
        "early_qb_rate": early_rates["QB"],
        "early_rb_rate": early_rates["RB"],
        "early_wr_rate": early_rates["WR"],
        "early_te_rate": early_rates["TE"],
        "early_k_rate": early_rates["K"],
        "early_def_rate": early_rates["DEF"],
        "mid_qb_rate": mid_rates["QB"],
        "mid_rb_rate": mid_rates["RB"],
        "mid_wr_rate": mid_rates["WR"],
        "mid_te_rate": mid_rates["TE"],
        "mid_k_rate": mid_rates["K"],
        "mid_def_rate": mid_rates["DEF"],
        "late_qb_rate": late_rates["QB"],
        "late_rb_rate": late_rates["RB"],
        "late_wr_rate": late_rates["WR"],
        "late_te_rate": late_rates["TE"],
        "late_k_rate": late_rates["K"],
        "late_def_rate": late_rates["DEF"],
        "adp_deviation": adp_deviation_norm,
        "sleeper_pick_rate": sleeper_rate,
        "handcuff_rate": 0.0,
        "qb_early_tendency": early_rates["QB"] * 2.0,
        "te_premium_tendency": early_rates["TE"] * 2.0,
        "rb_heavy_early": early_rates["RB"],
        "wr_heavy_early": early_rates["WR"],
        "pick_consistency": consistency,
    }


def _default_owner_profile() -> Dict[str, Any]:
    """
    Return a neutral default profile when no historical picks are available.

    Returns:
        Dict[str, Any]: Zero-filled 26-key profile dict.
    """
    return {
        "early_qb_rate": 0.0, "early_rb_rate": 0.0, "early_wr_rate": 0.0,
        "early_te_rate": 0.0, "early_k_rate": 0.0, "early_def_rate": 0.0,
        "mid_qb_rate": 0.0, "mid_rb_rate": 0.0, "mid_wr_rate": 0.0,
        "mid_te_rate": 0.0, "mid_k_rate": 0.0, "mid_def_rate": 0.0,
        "late_qb_rate": 0.0, "late_rb_rate": 0.0, "late_wr_rate": 0.0,
        "late_te_rate": 0.0, "late_k_rate": 0.0, "late_def_rate": 0.0,
        "adp_deviation": 0.5, "sleeper_pick_rate": 0.0, "handcuff_rate": 0.0,
        "qb_early_tendency": 0.0, "te_premium_tendency": 0.0,
        "rb_heavy_early": 0.0, "wr_heavy_early": 0.0, "pick_consistency": 0.5,
    }
