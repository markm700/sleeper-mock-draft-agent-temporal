from typing import Dict, Any, List
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import Player

@activity.defn(name="get_all_player_data")
async def get_all_player_data() -> Dict[str, Any]:
    """
    Fetch all NFL player data from the Sleeper API and batch upsert to the database.

    Returns:
        Dict[str, Any]: {"total_found_players": int, "upserted_players": int}
    """
    sleeper = get_sleeper_client_manager()
    postgres = get_postgres_client_manager()
    
    try:
        # Sleeper API returns Dict[player_id, player_data]
        all_player_data = await sleeper.get_nfl_players()
        activity.logger.info(f"Fetched data for {len(all_player_data)} NFL players from Sleeper API")
        
        # Convert dict to list of records for batch upsert
        player_records: List[Dict[str, Any]] = []
        
        for player_id, player_data in all_player_data.items():
            if not player_id or not isinstance(player_data, dict):
                activity.logger.info(f"Skipping invalid player entry: player_id={player_id}, full_name={player_data.get('full_name') if isinstance(player_data, dict) else 'N/A'}")
                continue
            player_record = {
                "player_id": player_id,
                # Identity fields
                "first_name": player_data.get("first_name"),
                "last_name": player_data.get("last_name"),
                "full_name": player_data.get("full_name"),
                # Status fields
                "status": player_data.get("status"),
                "position": player_data.get("position"),
                "team": player_data.get("team"),
                "number": player_data.get("number"),
                # Player details
                "age": player_data.get("age"),
                "years_exp": player_data.get("years_exp"),
                "height": player_data.get("height"),
                "weight": player_data.get("weight"),
                "college": player_data.get("college"),
                "high_school": player_data.get("high_school"),
                # Birth info
                "birth_date": player_data.get("birth_date"),
                "birth_city": player_data.get("birth_city"),
                "birth_state": player_data.get("birth_state"),
                "birth_country": player_data.get("birth_country"),
                # External IDs
                "espn_id": player_data.get("espn_id"),
                "yahoo_id": player_data.get("yahoo_id"),
                "fantasy_data_id": player_data.get("fantasy_data_id"),
                "rotowire_id": player_data.get("rotowire_id"),
                "sportradar_id": player_data.get("sportradar_id"),
                "gsis_id": player_data.get("gsis_id"),
                "stats_id": player_data.get("stats_id"),
                "rotoworld_id": player_data.get("rotoworld_id"),
                # Injury info
                "injury_status": player_data.get("injury_status"),
                "injury_body_part": player_data.get("injury_body_part"),
                "injury_notes": player_data.get("injury_notes"),
                "injury_start_date": player_data.get("injury_start_date"),
                # Store complete API response for reference
                "api_metadata": player_data.get('metadata', {}),
            }
            player_records.append(player_record)
        
        # Batch upsert all players (more efficient than individual upserts)
        if len(player_records) > 0:
            upserted_count = postgres.upsert_records(
                model=Player,
                records=player_records
            )
            activity.logger.info(f"Successfully batch upserted {upserted_count} players to database")
        else:
            activity.logger.info("No valid player records to upsert")
            upserted_count = 0
        
        return {
            "total_found_players": len(all_player_data),
            "upserted_players": upserted_count
        }
    except Exception as e:
        activity.logger.error(f"Failed to fetch and upsert player data: {str(e)}")
        raise