"""Stacking recommendations algorithm"""
import logging
from typing import List, Dict
from src.models.types import StackingRecommendation

logger = logging.getLogger(__name__)


def recommend_stacks(
    available_qbs: List[str],
    available_wrs: List[str],
    team_correlations: Dict[str, List[str]],
    min_correlation: float = 0.6
) -> List[StackingRecommendation]:
    """
    Recommend QB-WR stacks from same team
    
    Args:
        available_qbs: List of available QB player IDs
        available_wrs: List of available WR player IDs
        team_correlations: Map of QB IDs to their team's WR IDs
        min_correlation: Minimum correlation score to recommend
    
    Returns:
        List of stacking recommendations
    """
    try:
        recommendations = []
        
        for qb_id in available_qbs:
            team_wrs = team_correlations.get(qb_id, [])
            available_team_wrs = [wr for wr in team_wrs if wr in available_wrs]
            
            if available_team_wrs:
                # TODO: Calculate actual correlation from historical data
                correlation_score = 0.75  # Placeholder
                
                if correlation_score >= min_correlation:
                    rec = StackingRecommendation(
                        qb_id=qb_id,
                        wr_ids=available_team_wrs,
                        correlation_score=correlation_score,
                        team='TEAM'  # TODO: Get actual team
                    )
                    recommendations.append(rec)
        
        logger.info(f'Found {len(recommendations)} stacking opportunities')
        return recommendations
        
    except Exception as error:
        logger.error('Failed to generate stacking recommendations', exc_info=True)
        return []
