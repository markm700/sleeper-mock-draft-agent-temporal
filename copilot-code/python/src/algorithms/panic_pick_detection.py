"""Panic pick detection algorithm"""
import logging
from typing import Dict, Optional
from src.models.types import PanicPick
from src.database.player_utils import get_player_position

logger = logging.getLogger(__name__)


def is_panic_pick(
    user_id: str,
    pick_number: int,
    player_id: str,
    historical_tendencies: Dict,
    threshold: float = 3.0
) -> Optional[PanicPick]:
    """
    Detect if a pick significantly deviates from owner's historical patterns
    
    Args:
        user_id: Owner's user ID
        pick_number: Current pick number
        player_id: Player being picked
        historical_tendencies: Owner's historical draft tendencies
        threshold: Standard deviation threshold for panic (default 3.0)
    
    Returns:
        PanicPick object if detected, None otherwise
    """
    try:
        position = get_player_position(player_id)
        
        # Get owner's typical round for this position
        avg_round_key = f'avg_{position.lower()}_round'
        avg_round = historical_tendencies.get(avg_round_key, 0)
        
        if avg_round == 0:
            return None  # No historical data
        
        # Calculate current round from pick number (assuming 10 teams)
        current_round = (pick_number - 1) // 10 + 1
        
        # Calculate deviation
        deviation = abs(current_round - avg_round)
        
        # Check if deviation exceeds threshold (simplified 3-sigma check)
        if deviation >= threshold:
            panic = PanicPick(
                user_id=user_id,
                pick_number=pick_number,
                player_id=player_id,
                position=position,
                deviation_score=deviation
            )
            
            logger.warning(f'Panic pick detected: {user_id} drafting {position} at round {current_round} (avg: {avg_round})')
            return panic
        
        return None
        
    except Exception as error:
        logger.error('Failed to detect panic pick', exc_info=True)
        return None
