from dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager

@dataclass
class GetLeagueDraftsParams:
    league_id: str

@activity.defn(name="get_league_drafts")
async def get_league_drafts(input: GetLeagueDraftsParams) -> Dict[str, Any]:
    # Get team owner data by username -> user_id -> all leagues for season
    sleeper = get_sleeper_client_manager()

    league_drafts = await sleeper.get_league_drafts(league_id=input.league_id)

    return { "league_drafts": league_drafts }