from pydantic.dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import DraftPick

@dataclass(frozen=True, kw_only=True)
class GetSpecificDraftPicksParams:
    """
    Parameters for fetching picks from a specific draft.

    Fields:
        draft_id: Sleeper draft identifier.
    """

    draft_id: str

@activity.defn(name="get_specific_draft_picks")
async def get_specific_draft_picks(input: GetSpecificDraftPicksParams) -> Dict[str, Any]:
    """
    Fetch all picks for a specific draft and upsert to the database.

    Args:
        input: GetSpecificDraftPicksParams with draft_id.

    Returns:
        Dict[str, Any]: {"draft_picks": [...]} raw list of pick dicts from Sleeper.
    """
    sleeper = get_sleeper_client_manager()
    postgres = get_postgres_client_manager()

    try:
        draft_picks = await sleeper.get_draft_picks(draft_id=input.draft_id)

        # DB data - Draft Picks
        pick_records = []
        for pick in draft_picks:
            draft_id = pick.get("draft_id")
            pick_no = pick.get("pick_no")
            
            if not draft_id or pick_no is None:
                activity.logger.info(f"Skipping pick with missing required fields: draft_id={draft_id}, pick_no={pick_no}")
                continue
            
            pick_records.append({
                    "draft_id": draft_id,
                    "player_id": pick.get("player_id"),
                    "roster_id": pick.get("roster_id"),
                    "picked_by": pick.get("picked_by"),
                    "pick_no": pick_no,
                    "round": pick.get("round"),
                    "draft_slot": pick.get("draft_slot"),
                    "is_keeper": pick.get("is_keeper", False),
                    "api_metadata": pick.get("metadata", {}),
                }
            )
            activity.logger.info(f"Successfully added draft pick #{pick_no} to be batch upserted into database")
        postgres.upsert_records(
            model=DraftPick,
            records=pick_records,
            conflict_columns=["draft_id", "pick_no"],
            update_columns=[
                "player_id",
                "roster_id",
                "picked_by",
                "round",
                "draft_slot",
                "is_keeper",
                "api_metadata"
            ]
        )
        activity.logger.info(f"Successfully batch upserted {len(pick_records)} draft picks for draft {input.draft_id} to database")

        return { "draft_picks": draft_picks }
    except Exception as e:
        activity.logger.error(f"Failed to fetch draft picks for {input.draft_id}: {str(e)}")
        raise