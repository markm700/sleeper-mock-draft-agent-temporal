from dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager

@dataclass
class GetTradedDraftPicksParams:
    """Parameters for fetching traded picks for a league."""

    league_id: str
    season: str = "2025"

@activity.defn(name="get_traded_draft_picks")
async def get_traded_draft_picks(input: GetTradedDraftPicksParams) -> Dict[str, Any]:
    """Activity to fetch all traded draft picks for a given league, filtered by season."""
    sleeper = get_sleeper_client_manager()

    all_traded_picks = await sleeper.get_traded_draft_picks(league_id=input.league_id)
    
    # Filter traded picks by season
    traded_picks = [
        pick for pick in all_traded_picks 
        if pick.get("season") == input.season
    ]

    return { "traded_draft_picks": traded_picks }