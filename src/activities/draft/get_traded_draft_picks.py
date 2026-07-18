from pydantic.dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import TradedDraftPick

@dataclass(frozen=True, kw_only=True)
class GetTradedDraftPicksParams:
    """
    Parameters for fetching traded picks for a league.

    Fields:
        league_id: Sleeper league identifier.
        season: Season year to filter picks, e.g. "2025".
    """

    league_id: str
    season: str = "2025"

@activity.defn(name="get_traded_draft_picks")
async def get_traded_draft_picks(input: GetTradedDraftPicksParams) -> Dict[str, Any]:
    """
    Fetch traded draft picks for a league, filter by season, and upsert to the database.

    Args:
        input: GetTradedDraftPicksParams with league_id and season.

    Returns:
        Dict[str, Any]: {"traded_draft_picks": [...]} season-filtered list from Sleeper.
    """
    sleeper = get_sleeper_client_manager()
    postgres = get_postgres_client_manager()

    try:
        all_traded_picks = await sleeper.get_traded_draft_picks(league_id=input.league_id)
    
        # Filter traded picks by season
        traded_picks = [
            pick for pick in all_traded_picks 
            if pick.get("season") == input.season
        ]

        # DB data - Traded Draft Picks
        pick_records = []
        for pick in traded_picks:
            roster_id = pick.get("roster_id")
            round_num = pick.get("round")
            
            if roster_id is None or round_num is None:
                print(f"Skipping traded pick with missing required fields: roster_id={roster_id}, round={round_num}")
                continue
            
            pick_records.append({
                    "league_id": input.league_id,
                    "owner_id": pick.get("owner_id"),
                    "previous_owner_id": pick.get("previous_owner_id"),
                    "roster_id": roster_id,
                    "season": input.season,
                    "round": round_num,
                }
            )
            print(f"Successfully added traded draft pick (roster {roster_id}, round {round_num}) for {input.season} season to be batch upserted into database")
        postgres.upsert_records(
            model=TradedDraftPick,
            records=pick_records,
            conflict_columns=["league_id", "season", "round", "roster_id"],
        )
        print(f"Successfully batch upserted {len(pick_records)} traded draft picks for league {input.league_id} to database")

        return { "traded_draft_picks": traded_picks }
    except Exception as e:
        print(f"Failed to fetch traded draft picks for {input.league_id}: {str(e)}")
        raise