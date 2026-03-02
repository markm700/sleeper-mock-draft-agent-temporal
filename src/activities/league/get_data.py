from dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import League, Roster, User

@dataclass
class GetLeagueDataParams:
    """Parameters for fetching data about a Sleeper league."""

    league_id: str

@activity.defn(name="get_league_data")
async def get_league_data(input: GetLeagueDataParams) -> Dict[str, Any]:
    """Activity to fetch league metadata, users, and rosters via league_id."""

    sleeper = get_sleeper_client_manager()
    postgres = get_postgres_client_manager()
    
    try:
        league_data = await sleeper.get_league(input.league_id)
        print(f"League {input.league_id} League Id =  {input.league_id}")
        # DB data - League
        postgres.upsert_record(
            model=League,
            data={
                "league_id": input.league_id,
                "previous_league_id": league_data.get("previous_league_id"),
                "draft_id": league_data.get("draft_id"),
                "name": league_data.get("name"),
                "shard": league_data.get("shard"),
                "season": league_data.get("season"),
                "season_type": league_data.get("season_type"),
                "roster_positions": league_data.get("roster_positions", []),
                "total_rosters": league_data.get("total_rosters"),
                "league_settings": league_data.get("settings", {}),
                "scoring_settings": league_data.get("scoring_settings", {}),
                "api_metadata": league_data.get("metadata"),
                "status": league_data.get("status"),
                "bracket_id": league_data.get("bracket_id"),
                "loser_bracket_id": league_data.get("loser_bracket_id"),
                "bracket_overrides_id": league_data.get("bracket_overrides_id"),
                "loser_bracket_overrides_id": league_data.get("loser_bracket_overrides_id"),
            }
        )
        print(f"Successfully upserted league {input.league_id} to database")

        league_users = await sleeper.get_league_users(league_id=input.league_id)
        print(f"League {input.league_id} League Users =  {len(league_users)}")
        # DB data - League Users/Team Owners
        for user in league_users:
            postgres.upsert_record(
                model=User,
                data={
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "display_name": user["display_name"],
                    "real_name": user.get("real_name"),
                    "is_bot": user.get("is_bot", False),
                }
            )
            print(f"Successfully upserted user {user['username']} to database")
        print(f"Successfully upserted all {len(league_users)} users for league {input.league_id} to database")
        
        league_rosters = await sleeper.get_league_rosters(league_id=input.league_id)
        print(f"League {input.league_id} League Rosters =  {len(league_rosters)}")
        # DB data - League Rosters
        for roster in league_rosters:
            postgres.upsert_record(
                model=Roster,
                data={
                    "league_id": input.league_id,
                    "owner_id": roster["owner_id"],
                    "roster_id": roster["roster_id"],
                    "players": roster.get("players", []),
                    "starters": roster.get("starters", []),
                    "keepers": roster.get("keepers", []),
                    "roster_settings": roster.get("roster_settings", {}),
                    "reserve": roster.get("reserve", []),
                    "taxi": roster.get("taxi", []),
                    "co_owners": roster.get("co_owners"),
                    "api_metadata": roster.get("metadata"),
                }
            )
            print(f"Successfully upserted roster {roster['roster_id']} to database")
        print(f"Successfully upserted all {len(league_rosters)} rosters for league {input.league_id} to database")

        return {
            "league_data": league_data,
            "league_users": league_users,
            "league_rosters": league_rosters
        }
    except Exception as e:
            print(f"Failed to fetch league data for {input.league_id}: {str(e)}")
            raise