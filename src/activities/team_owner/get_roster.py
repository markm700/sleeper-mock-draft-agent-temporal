from pydantic.dataclasses import dataclass
from typing import Optional, Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager

@dataclass(frozen=True, kw_only=True)
class GetLeagueRosterParams:
    """
    Parameters for fetching league rosters, optionally filtered by owner.

    Args:
        league_id: Sleeper league identifier.
        user_id: Owner's Sleeper user ID to filter rosters. None returns all rosters.
    """

    league_id: str
    user_id: Optional[str] = None

@activity.defn(name="get_team_owner_rosters")
async def get_team_owner_rosters(input: GetLeagueRosterParams) -> Dict[str, Any]:
    """
    Fetch rosters for a league, optionally filtered to a single owner.

    Args:
        input: GetLeagueRosterParams with league_id and optional user_id.

    Returns:
        Dict[str, Any]: {"roster": [...]} if user_id provided, else {"rosters": [...]}.
    """

    sleeper = get_sleeper_client_manager()

    try:
        league_rosters = await sleeper.get_league_rosters(league_id=input.league_id)

        # DB data - League Rosters
        # handled in league/get_data activity

        if input.user_id is not None:
            team_owner_roster = [
                roster for roster in league_rosters if roster.get("owner_id") == input.user_id
            ]
            return {"roster": team_owner_roster }

        return {"rosters": league_rosters }
       
    except Exception as e:
        activity.logger.error(f"Failed to fetch team owner rosters for league {input.league_id}: {str(e)}")
        raise