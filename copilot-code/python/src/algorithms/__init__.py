"""Algorithms package"""
from src.algorithms.keeper_value import (
    calculate_keeper_value,
    get_best_2_keeper_combo,
    get_projected_points,
    get_average_value_at_round,
)
from src.algorithms.position_run_detection import (
    detect_position_run,
    adjust_scarcity,
)
from src.algorithms.panic_pick_detection import is_panic_pick
from src.algorithms.boom_bust_scoring import calculate_boom_bust_score
from src.algorithms.stacking_recommendations import recommend_stacks
from src.algorithms.draft_philosophy import detect_draft_philosophy

__all__ = [
    'calculate_keeper_value',
    'get_best_2_keeper_combo',
    'get_projected_points',
    'get_average_value_at_round',
    'detect_position_run',
    'adjust_scarcity',
    'is_panic_pick',
    'calculate_boom_bust_score',
    'recommend_stacks',
    'detect_draft_philosophy',
]
