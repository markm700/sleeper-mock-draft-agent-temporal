from typing import List
from src.models.types import DraftPick, PositionRun
from src.config import config


def detect_position_run(
    recent_picks: List[DraftPick], threshold: int = None
) -> PositionRun:
    """
    Detect if a position run is occurring
    A run is detected when 3+ consecutive picks are the same position
    """
    if threshold is None:
        threshold = config.POSITION_RUN_THRESHOLD

    if len(recent_picks) < threshold:
        return PositionRun(detected=False)

    last_n = recent_picks[-threshold:]
    positions = [get_player_position(p.player_id) for p in last_n]

    # Find most common position in recent picks
    position_counts = {}
    for pos in positions:
        position_counts[pos] = position_counts.get(pos, 0) + 1

    most_common = max(position_counts, key=position_counts.get)

    if position_counts[most_common] >= threshold:
        return PositionRun(
            detected=True, position=most_common, count=position_counts[most_common]
        )

    return PositionRun(detected=False)


def adjust_scarcity(position: str, run_count: int) -> float:
    """
    Adjust scarcity multiplier based on position run
    +15% per pick beyond threshold
    """
    base_multiplier = config.SCARCITY_MULTIPLIERS.get(position, 1.0)
    threshold = config.POSITION_RUN_THRESHOLD

    if run_count <= threshold:
        return base_multiplier

    additional_multiplier = 1 + (run_count - threshold) * 0.15
    return base_multiplier * additional_multiplier


def get_player_position(player_id: str) -> str:
    """
    Get position for a player
    TODO: Implement actual player lookup
    """
    # Placeholder - should query player database
    return "RB"
