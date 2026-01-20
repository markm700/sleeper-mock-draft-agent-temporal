"""Position run detection algorithm"""
import logging
from typing import List, Optional
from src.models.types import DraftPick, PositionRun
from src.database.player_utils import get_player_position

logger = logging.getLogger(__name__)


def detect_position_run(
    recent_picks: List[DraftPick],
    threshold: int = 3
) -> Optional[PositionRun]:
    """
    Detect if 3+ consecutive picks are same position
    
    Args:
        recent_picks: List of recent draft picks
        threshold: Minimum consecutive picks to trigger run (default 3)
    
    Returns:
        PositionRun object if detected, None otherwise
    """
    try:
        if len(recent_picks) < threshold:
            return None
        
        # Check last N picks for same position
        positions = [get_player_position(pick.player_id) for pick in recent_picks[-threshold:]]
        
        if len(set(positions)) == 1:
            # All same position - run detected
            position = positions[0]
            start_pick = recent_picks[-threshold].pick_number
            
            run = PositionRun(
                position=position,
                start_pick=start_pick,
                consecutive_picks=threshold,
                scarcity_multiplier=1.0 + (0.15 * threshold)  # +15% per pick
            )
            
            logger.info(f'Position run detected: {threshold} {position}s starting at pick {start_pick}')
            return run
        
        return None
        
    except Exception as error:
        logger.error('Failed to detect position run', exc_info=True)
        return None


def adjust_scarcity(
    position: str,
    base_value: float,
    run_detected: bool = False
) -> float:
    """
    Adjust player value based on position scarcity
    
    Args:
        position: Player position
        base_value: Base player value
        run_detected: Whether a position run is currently happening
    
    Returns:
        Adjusted value
    """
    try:
        if run_detected:
            # Increase value by 15% per consecutive pick in run
            adjusted = base_value * 1.15
            logger.debug(f'Scarcity adjustment for {position}: {base_value:.2f} -> {adjusted:.2f}')
            return adjusted
        
        return base_value
        
    except Exception as error:
        logger.error('Failed to adjust scarcity', exc_info=True)
        return base_value
