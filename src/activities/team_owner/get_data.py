from dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import User

@dataclass
class GetTeamOwnerDataParams:
    """Parameters for fetching data about a team owner in a league."""

    username: str
    league_name: str

@activity.defn(name="get_team_owner_data")
async def get_team_owner_data(input: GetTeamOwnerDataParams) -> Dict[str, Any]:
    """Activity to fetch team-owner metadata and their leagues."""

    sleeper = get_sleeper_client_manager()
    pg_client = get_postgres_client_manager()
    
    user_data = await sleeper.get_user(input.username)
    user_id = user_data["user_id"]
    print(f"Team Owner {input.username} User Id =  {user_id}")

    user_leagues = await sleeper.get_user_leagues(user_id=user_id, league_name=input.league_name)
    
    # Method 1: Using session_scope (recommended)
    with pg_client.session_scope() as session:
        user = User(
            user_id=user_data["user_id"],
            username=user_data["username"],
            real_name=user_data["real_name"],
            display_name=user_data["display_name"]
        )
        session.add(user)
        # Auto-commits here

    return {
        "user_id": user_id,
        "user_data": user_data,
        "user_leagues": user_leagues
    }