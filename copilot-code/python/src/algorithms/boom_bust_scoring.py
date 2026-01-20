"""Boom/bust scoring algorithm"""
import logging
from typing import List, Dict
from src.models.types import BoomBustProfile

logger = logging.getLogger(__name__)


def calculate_boom_bust_score(
    player_id: str,
    weekly_scores: List[float],
    boom_threshold: float = 20.0,
    bust_threshold: float = 5.0
) -> BoomBustProfile:
    """
    Calculate boom/bust profile based on weekly score variance
    
    Args:
        player_id: Player ID
        weekly_scores: List of weekly fantasy scores
        boom_threshold: Points threshold for boom week
        bust_threshold: Points threshold for bust week
    
    Returns:
        BoomBustProfile with variance metrics
    """
    try:
        if not weekly_scores:
            return BoomBustProfile(
                player_id=player_id,
                boom_rate=0.0,
                bust_rate=0.0,
                consistency_score=0.0,
                variance=0.0
            )
        
        # Calculate boom/bust rates
        boom_weeks = sum(1 for score in weekly_scores if score >= boom_threshold)
        bust_weeks = sum(1 for score in weekly_scores if score <= bust_threshold)
        total_weeks = len(weekly_scores)
        
        boom_rate = boom_weeks / total_weeks
        bust_rate = bust_weeks / total_weeks
        
        # Calculate variance (coefficient of variation)
        mean = sum(weekly_scores) / total_weeks
        variance = sum((x - mean) ** 2 for x in weekly_scores) / total_weeks
        std_dev = variance ** 0.5
        
        # Consistency score (inverse of coefficient of variation)
        coefficient_of_variation = std_dev / mean if mean > 0 else 0
        consistency_score = 1 / (1 + coefficient_of_variation)  # Normalize 0-1
        
        profile = BoomBustProfile(
            player_id=player_id,
            boom_rate=boom_rate,
            bust_rate=bust_rate,
            consistency_score=consistency_score,
            variance=variance
        )
        
        logger.debug(f'Boom/bust profile for {player_id}: boom={boom_rate:.2%}, bust={bust_rate:.2%}')
        return profile
        
    except Exception as error:
        logger.error(f'Failed to calculate boom/bust for {player_id}', exc_info=True)
        return BoomBustProfile(
            player_id=player_id,
            boom_rate=0.0,
            bust_rate=0.0,
            consistency_score=0.0,
            variance=0.0
        )
