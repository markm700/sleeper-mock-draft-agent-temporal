"""Player utility functions"""
import logging
from typing import Optional, Dict
from src.database.db import db

logger = logging.getLogger(__name__)

# In-memory cache for player lookups
_player_cache: Dict[str, Dict] = {}


def get_player_by_id(player_id: str) -> Optional[Dict]:
    """Get player by ID from cache or database"""
    # Check cache first
    if player_id in _player_cache:
        return _player_cache[player_id]
    
    # TODO: Query from database
    # query = 'SELECT * FROM players WHERE player_id = %s'
    # results = db.execute_dict_query(query, (player_id,))
    # if results:
    #     player = results[0]
    #     _player_cache[player_id] = player
    #     return player
    
    return None


def get_player_position(player_id: str) -> str:
    """Get player position - centralized function used across algorithms"""
    player = get_player_by_id(player_id)
    if player:
        return player.get('position', 'UNKNOWN')
    return 'UNKNOWN'


def load_player_cache() -> None:
    """Load all players into cache for quick lookups"""
    try:
        logger.info('Loading player cache...')
        # TODO: Load all players from database
        # query = 'SELECT * FROM players'
        # players = db.execute_dict_query(query)
        # for player in players:
        #     _player_cache[player['player_id']] = player
        logger.info(f'Player cache loaded: {len(_player_cache)} players')
    except Exception as error:
        logger.error('Failed to load player cache', exc_info=True)
        raise


def clear_player_cache() -> None:
    """Clear player cache"""
    _player_cache.clear()
