from dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import League, Roster, TeamOwner, User
    from schema.constants import TEAM_OWNER_FUN_FACT_MAP

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
        user_records = []
        owner_records = []
        for user in league_users:
            user_id = user.get("user_id")
            username = user.get("username", user.get("display_name")),  # Fallback to display_name if username is missing
            # Skip users without required fields
            if not user_id:
                print(f"Skipping user with missing required fields: user_id={user_id}")
                continue
            
            # Add personality fun fact if available
            if TEAM_OWNER_FUN_FACT_MAP.keys().__contains__(username):
                personality_fun_fact = TEAM_OWNER_FUN_FACT_MAP.get(username)
            else:
                personality_fun_fact = "No current fun fact, please set for user in TEAM_OWNER_FUN_FACT_MAP"

            user_records.append({
                    "user_id": user_id,
                    "username": username,
                    "display_name": user.get("display_name", "Unknown"),
                    "real_name": user.get("real_name"),
                    "is_bot": user.get("is_bot", False),
                    "personality_fun_fact": personality_fun_fact
                }
            )
            print(f"Successfully added user {user_id} for league {input.league_id} to be batch upserted into database")
            owner_records.append({
                    "league_id": input.league_id,
                    "user_id": user_id,
                    "display_name": user.get("display_name", "Unknown"),
                    "is_owner": user.get("is_owner", False),
                    "is_bot": user.get("is_bot", False)
                }
            )
            print(f"Successfully added team owner {user_id} for league {input.league_id} to be batch upserted into database")
        postgres.upsert_records(
            model=User,
            records=user_records,
            conflict_columns=["user_id"],
            update_columns=["username", "display_name", "real_name", "is_bot"]
        )
        print(f"Successfully batch upserted {len(user_records)} users for league {input.league_id} to database")
        postgres.upsert_records(
            model=TeamOwner,
            records=owner_records,
            conflict_columns=["league_id", "user_id"],
            update_columns=["display_name", "is_owner", "is_bot"]
        )
        print(f"Successfully batch upserted {len(owner_records)} team owners for league {input.league_id} to database")
        
        league_rosters = await sleeper.get_league_rosters(league_id=input.league_id)
        print(f"League {input.league_id} League Rosters =  {len(league_rosters)}")
        # DB data - League Rosters
        roster_records = []
        for roster in league_rosters:
            roster_records.append({
                "league_id": input.league_id,
                "owner_id": roster.get("owner_id"),
                "roster_id": roster.get("roster_id"),
                "players": roster.get("players", []),
                "starters": roster.get("starters", []),
                "keepers": roster.get("keepers", []),
                "roster_settings": roster.get("settings", {}),
                "reserve": roster.get("reserve", []),
                "taxi": roster.get("taxi", []),
                "co_owners": roster.get("co_owners"),
                "api_metadata": roster.get("metadata"),
            })
            print(f"Successfully added roster {roster.get('roster_id')} to be batch upserted into database")
        postgres.upsert_records(
            model=Roster,
            records=roster_records,
            conflict_columns=["league_id", "roster_id"],
            update_columns=["owner_id", "players", "starters", "keepers", "roster_settings", "reserve", "taxi", "co_owners", "api_metadata"]
        )
        print(f"Successfully batch upserted {len(roster_records)} rosters for league {input.league_id} to database")

        return {
            "league_data": league_data,
            "league_users": league_users,
            "league_rosters": league_rosters
        }
    except Exception as e:
            print(f"Failed to fetch league data for {input.league_id}: {str(e)}")
            raise