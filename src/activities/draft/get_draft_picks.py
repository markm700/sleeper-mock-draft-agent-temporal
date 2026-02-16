from dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager

@dataclass
class GetSpecificDraftPicksParams:
    """Parameters for fetching picks from a specific draft."""

    draft_id: str

@activity.defn(name="get_specific_draft_picks")
async def get_specific_draft_picks(input: GetSpecificDraftPicksParams) -> Dict[str, Any]:
    """Activity to fetch all picks for a given draft ID."""
    sleeper = get_sleeper_client_manager()

    draft_picks = await sleeper.get_draft_picks(draft_id=input.draft_id)

    return { "draft_picks": draft_picks }