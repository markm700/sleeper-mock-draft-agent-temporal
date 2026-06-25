from dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import Draft

@dataclass
class GetLeagueDraftsParams:
    """
    Parameters for fetching all drafts for a league.

    Fields:
        league_id: Sleeper league identifier.
    """

    league_id: str

@activity.defn(name="get_league_drafts")
async def get_league_drafts(input: GetLeagueDraftsParams) -> Dict[str, Any]:
    """
    Fetch all drafts for a league from the Sleeper API and upsert to the database.

    Args:
        input: GetLeagueDraftsParams with league_id.

    Returns:
        Dict[str, Any]: {"league_drafts": [...]} raw list of draft dicts from Sleeper.
    """
    sleeper = get_sleeper_client_manager()
    postgres = get_postgres_client_manager()

    try:
        league_drafts = await sleeper.get_league_drafts(league_id=input.league_id)

        # DB data - League Drafts
        draft_records = []
        for draft in league_drafts:
            draft_id = draft.get("draft_id")
            if not draft_id:
                print(f"Skipping draft with missing draft_id")
                continue
                
            draft_records.append({
                    "draft_id": draft_id,
                    "league_id": input.league_id,
                    "type": draft.get("type"),
                    "status": draft.get("status"),
                    "season": draft.get("season"),
                    "season_type": draft.get("season_type"),
                    "sport": draft.get("sport", "nfl"),
                    "draft_order": draft.get("draft_order"),
                    "draft_settings": draft.get("settings", {}),
                    "api_metadata": draft.get("metadata", {}),
                    "creator_id": draft.get("creator"),
                    "created": draft.get("created"),
                }
            )
            print(f"Successfully added draft {draft_id} to be batch upserted into database")
        postgres.upsert_records(
            model=Draft,
            records=draft_records,
            conflict_columns=["draft_id"],
            update_columns=[
                "type",
                "status",
                "season",
                "season_type",
                "sport",
                "draft_order",
                "draft_settings",
                "api_metadata",
                "creator_id",
                "created"
            ]
        )
        print(f"Successfully batch upserted {len(draft_records)} drafts for league {input.league_id} to database")

        return { "league_drafts": league_drafts }
    except Exception as e:
        print(f"Failed to fetch league drafts for {input.league_id}: {str(e)}")
        raise