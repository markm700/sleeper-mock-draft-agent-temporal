"""
Activity to calculate Average Draft Position (ADP) from stored DraftPick records.

Output is structured to feed directly into get_player_features_from_db as adp_data.
"""

import math
from collections import defaultdict
from pydantic.dataclasses import dataclass
from typing import Dict, Any, List, Optional
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import DraftPick, Draft


@dataclass(frozen=True, kw_only=True)
class CalculateADPFromPicksParams:
    """
    Parameters for calculating ADP from stored draft pick records.

    Args:
        league_id: Primary Sleeper league identifier to scope the calculation.
        season: Season year filter, e.g. "2025". None includes all seasons.
        weighted: Apply recency decay across drafts (factor 0.7, default True).
        min_times_drafted: Exclude players drafted fewer than this many times.
        additional_league_ids: Extra league_ids (prior seasons) to include in ADP.
    """
    league_id: str
    season: Optional[str] = None        # e.g. "2025" — if None, includes all seasons
    weighted: bool = True               # Apply recency decay across drafts (factor 0.7)
    min_times_drafted: int = 1          # Exclude players drafted fewer than this many times
    additional_league_ids: Optional[List[str]] = None


@activity.defn(name="calculate_adp_from_picks")
async def calculate_adp_from_picks(input: CalculateADPFromPicksParams) -> Dict[str, Any]:
    """
    Calculate Average Draft Position for each player from stored DraftPick records.

    Queries draft_picks for all picks in the given league, optionally filtered by season.
    When weighted=True, picks from more recent drafts are up-weighted using exponential
    decay (factor 0.7 per draft, oldest to newest).

    Args:
        input: CalculateADPFromPicksParams with league_id, optional season, weighted flag,
            and min_times_drafted threshold.

    Returns:
        Dict[str, Any]: {"adp_data": {player_id: {"adp": float, "std_dev": float, "times_drafted": int}}, "num_players": int, "num_picks": int, "num_drafts": int, "league_id": str, "season": str | None, "weighted": bool}
    """
    postgres = get_postgres_client_manager()

    try:
        with postgres.get_session() as session:
            # Build the set of league_ids to query across
            all_league_ids = [input.league_id]
            if input.additional_league_ids:
                all_league_ids.extend(input.additional_league_ids)

            # Resolve draft_ids for these leagues (+ optional season filter)
            draft_query = session.query(Draft.draft_id).filter(
                Draft.league_id.in_(all_league_ids)
            )
            if input.season:
                draft_query = draft_query.filter(Draft.season == input.season)

            draft_ids: List[str] = [row[0] for row in draft_query.all()]

            if not draft_ids:
                print(
                    f"No drafts found for league_id={input.league_id} "
                    f"season={input.season}"
                )
                return {
                    "adp_data": {},
                    "num_players": 0,
                    "num_picks": 0,
                    "num_drafts": 0,
                    "league_id": input.league_id,
                    "season": input.season,
                    "weighted": input.weighted,
                }

            # Fetch all picks for those drafts
            picks = (
                session.query(DraftPick.player_id, DraftPick.pick_no, DraftPick.draft_id)
                .filter(
                    DraftPick.draft_id.in_(draft_ids),
                    DraftPick.player_id.isnot(None),
                )
                .all()
            )

        print(
            f"Calculating ADP from {len(picks)} picks across {len(draft_ids)} drafts "
            f"(league={input.league_id}, season={input.season}, weighted={input.weighted})"
        )

        # Assign recency weight per draft_id.
        # draft_ids are sorted ascending (oldest first) so the last draft has weight 1.0,
        # the one before 0.7, the one before that 0.49, etc.
        DECAY = 0.7
        sorted_draft_ids = sorted(draft_ids)  # oldest → newest (lexicographic; works for Sleeper IDs)
        n_drafts = len(sorted_draft_ids)
        draft_weight: Dict[str, float] = {
            d_id: DECAY ** (n_drafts - 1 - idx)
            for idx, d_id in enumerate(sorted_draft_ids)
        }

        # Accumulate weighted pick positions per player
        # Structure: { player_id: [(pick_no, weight), ...] }
        player_picks: Dict[str, List[tuple]] = defaultdict(list)
        for player_id, pick_no, draft_id in picks:
            w = draft_weight[draft_id] if input.weighted else 1.0
            player_picks[player_id].append((float(pick_no), w))

        adp_data: Dict[str, Dict[str, Any]] = {}
        for player_id, weighted_picks in player_picks.items():
            times_drafted = len(weighted_picks)
            if times_drafted < input.min_times_drafted:
                continue

            pick_nos = [p for p, _ in weighted_picks]
            weights  = [w for _, w in weighted_picks]
            total_w  = sum(weights)

            # Weighted mean
            w_mean = sum(p * w for p, w in weighted_picks) / total_w

            # Weighted std dev (population formula)
            w_var = sum(w * (p - w_mean) ** 2 for p, w in weighted_picks) / total_w
            w_std = math.sqrt(w_var)

            adp_data[player_id] = {
                "adp": round(w_mean, 2),
                "std_dev": round(w_std, 2),
                "times_drafted": times_drafted,
            }

        print(
            f"ADP calculated for {len(adp_data)} players "
            f"(filtered out {len(player_picks) - len(adp_data)} below "
            f"min_times_drafted={input.min_times_drafted})"
        )

        return {
            "adp_data": adp_data,
            "num_players": len(adp_data),
            "num_picks": len(picks),
            "num_drafts": len(draft_ids),
            "league_id": input.league_id,
            "season": input.season,
            "weighted": input.weighted,
        }

    except Exception as e:
        print(f"Failed to calculate ADP for league {input.league_id}: {str(e)}")
        raise
