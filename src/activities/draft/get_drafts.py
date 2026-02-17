from dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager

@dataclass
class GetLeagueDraftsParams:
    """Parameters for fetching all drafts for a league."""

    league_id: str

@activity.defn(name="get_league_drafts")
async def get_league_drafts(input: GetLeagueDraftsParams) -> Dict[str, Any]:
    """Activity to fetch all drafts associated with a league."""
    sleeper = get_sleeper_client_manager()

    league_drafts = await sleeper.get_league_drafts(league_id=input.league_id)

    return { "league_drafts": league_drafts }