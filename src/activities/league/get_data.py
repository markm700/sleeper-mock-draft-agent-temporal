from dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager

@dataclass
class GetLeagueDataParams:
    """Parameters for fetching data about a Sleeper league."""

    league_id: str

@activity.defn(name="get_league_data")
async def get_league_data(input: GetLeagueDataParams) -> Dict[str, Any]:
    """Activity to fetch league metadata, users, and rosters via league_id."""

    sleeper = get_sleeper_client_manager()
    
    league_data = await sleeper.get_league(input.league_id)
    print(f"League {input.league_id} League Id =  {input.league_id}")
    
    league_users = await sleeper.get_league_users(league_id=input.league_id)
    print(f"League {input.league_id} League Users =  {len(league_users)}")

    league_rosters = await sleeper.get_league_rosters(league_id=input.league_id)
    print(f"League {input.league_id} League Rosters =  {len(league_rosters)}")
          
    return {
        "league_data": league_data,
        "league_users": league_users,
        "league_rosters": league_rosters
    }