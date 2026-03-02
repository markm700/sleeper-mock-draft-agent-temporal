from dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import Draft

@dataclass
class GetLeagueDraftsParams:
    """Parameters for fetching all drafts for a league."""

    league_id: str

@activity.defn(name="get_league_drafts")
async def get_league_drafts(input: GetLeagueDraftsParams) -> Dict[str, Any]:
    """Activity to fetch all drafts associated with a league."""
    sleeper = get_sleeper_client_manager()
    postgres = get_postgres_client_manager()

    try:
        league_drafts = await sleeper.get_league_drafts(league_id=input.league_id)

        # DB data - League Drafts
        for draft in league_drafts:
            postgres.upsert_record(
                model=Draft,
                data={
                    "draft_id": draft["draft_id"],
                    "league_id": input.league_id,
                    "type": draft["type"],
                    "status": draft["status"],
                    "season": draft["season"],
                    "season_type": draft["season_type"],
                    "draft_order": draft.get("draft_order"),
                    "draft_settings": draft.get("settings", {}),
                    "api_metadata": draft.get("metadata", {}),
                    "creator": draft.get("creator", "unknown"),
                    "created": draft.get("created"),
                }
            )
            print(f"Successfully upserted draft {draft['draft_id']} to database")
        print(f"Successfully upserted all {len(league_drafts)} drafts for league {input.league_id} to database")

        return { "league_drafts": league_drafts }
    except Exception as e:
        print(f"Failed to fetch league drafts for {input.league_id}: {str(e)}")
        raise