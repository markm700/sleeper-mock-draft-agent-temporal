"""Draft philosophy detection algorithm"""
import logging
from typing import List, Dict
from src.models.types import DraftPick
from src.database.player_utils import get_player_position

logger = logging.getLogger(__name__)


def detect_draft_philosophy(
    user_id: str,
    draft_picks: List[DraftPick]
) -> str:
    """
    Detect owner's draft philosophy based on early round picks
    
    Philosophies:
    - Zero-RB: No RBs in first 3 rounds
    - Hero-RB: 1 RB in first 2 rounds, then WRs
    - Robust-RB: 2+ RBs in first 3 rounds
    - WR-Heavy: 3+ WRs in first 5 rounds
    - Balanced: Mix of positions
    
    Args:
        user_id: Owner's user ID
        draft_picks: List of draft picks by this owner
    
    Returns:
        Philosophy name
    """
    try:
        # Get first 5 rounds
        early_picks = [p for p in draft_picks if p.round <= 5]
        first_3_rounds = [p for p in draft_picks if p.round <= 3]
        first_2_rounds = [p for p in draft_picks if p.round <= 2]
        
        # Count positions
        rb_count_3 = sum(1 for p in first_3_rounds if get_player_position(p.player_id) == 'RB')
        rb_count_2 = sum(1 for p in first_2_rounds if get_player_position(p.player_id) == 'RB')
        wr_count_5 = sum(1 for p in early_picks if get_player_position(p.player_id) == 'WR')
        
        # Detect philosophy
        if rb_count_3 == 0:
            philosophy = 'Zero-RB'
        elif rb_count_2 == 1 and wr_count_5 >= 3:
            philosophy = 'Hero-RB'
        elif rb_count_3 >= 2:
            philosophy = 'Robust-RB'
        elif wr_count_5 >= 3:
            philosophy = 'WR-Heavy'
        else:
            philosophy = 'Balanced'
        
        logger.info(f'Draft philosophy for {user_id}: {philosophy}')
        return philosophy
        
    except Exception as error:
        logger.error(f'Failed to detect philosophy for {user_id}', exc_info=True)
        return 'Unknown'
