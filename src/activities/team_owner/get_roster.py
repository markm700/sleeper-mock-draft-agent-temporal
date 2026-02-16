from dataclasses import dataclass
from typing import Optional, Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager

@dataclass
class GetLeagueRosterParams:
    """Parameters for fetching league rosters, optionally filtered by owner."""

    league_id: str
    user_id: Optional[str] = None

@activity.defn(name="get_team_owner_rosters")
async def get_team_owner_rosters(input: GetLeagueRosterParams) -> Dict[str, Any]:
    """Activity to fetch rosters for a league, optionally by owner ID."""

    sleeper = get_sleeper_client_manager()

    league_rosters = await sleeper.get_league_rosters(league_id=input.league_id)

    if input.user_id is not None:
        team_owner_roster = [
            roster for roster in league_rosters if roster.get("owner_id") == input.user_id
        ]
        return {"roster": team_owner_roster }

    return {"roster": league_rosters }