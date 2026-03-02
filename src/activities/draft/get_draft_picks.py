from dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import DraftPick
@dataclass
class GetSpecificDraftPicksParams:
    """Parameters for fetching picks from a specific draft."""

    draft_id: str

@activity.defn(name="get_specific_draft_picks")
async def get_specific_draft_picks(input: GetSpecificDraftPicksParams) -> Dict[str, Any]:
    """Activity to fetch all picks for a given draft ID."""
    sleeper = get_sleeper_client_manager()
    postgres = get_postgres_client_manager()

    try:
        draft_picks = await sleeper.get_draft_picks(draft_id=input.draft_id)

        # DB data - Draft Picks
        for pick in draft_picks:
            postgres.upsert_record(
                model=DraftPick,
                data={
                    "draft_id": pick["draft_id"],
                    "pick_id": pick["pick_id"],
                    "player_id": pick["player_id"],
                    "roster_id": pick["roster_id"],
                    "picked_by": pick["picked_by"],
                    "pick_no": pick["pick_no"],
                    "round": pick["round"],
                    "draft_slot": pick["draft_slot"],
                }
            )
            print(f"Successfully upserted draft pick {pick['pick_id']} to database")
        print(f"Successfully upserted all {len(draft_picks)} draft picks for draft {input.draft_id} to database")

        return { "draft_picks": draft_picks }
    except Exception as e:
        print(f"Failed to fetch draft picks for {input.draft_id}: {str(e)}")
        raise