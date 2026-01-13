from typing import List
from src.models.types import User, DraftPick, PanicPick, ManagerTendency


def is_panic_pick(
    owner: User, pick: DraftPick, round_num: int, tendencies: List[ManagerTendency]
) -> PanicPick:
    """
    Detect if a pick is a "panic pick" - significant deviation from owner's historical patterns
    """
    round_tendencies = [t for t in tendencies if t.round == round_num]

    if not round_tendencies:
        return PanicPick(is_panic=False)

    # Build historical pattern for this round
    historical_pattern = {}
    total_picks = 0

    for t in round_tendencies:
        historical_pattern[t.position] = t.frequency
        total_picks += t.frequency

    # Normalize to percentages
    if total_picks > 0:
        for pos in historical_pattern:
            historical_pattern[pos] = historical_pattern[pos] / total_picks

    pick_position = get_player_position(pick.player_id)

    # Check if position is expected for this owner in this round
    expected_positions = [pos for pos, freq in historical_pattern.items() if freq > 0.2]

    if pick_position not in expected_positions:
        deviation = 1.0 - historical_pattern.get(pick_position, 0)

        # 3-sigma equivalent (85% deviation)
        if deviation > 0.85:
            return PanicPick(
                is_panic=True,
                confidence=deviation,
                reason=f"{pick_position} rarely taken in Round {round_num}",
            )

    # Special case: Early QB reach
    if pick_position == "QB" and round_num < 8:
        avg_qb_round = get_average_qb_round(tendencies)
        if avg_qb_round > 10:
            return PanicPick(
                is_panic=True,
                confidence=0.9,
                reason="QB reach (historically waits)",
            )

    return PanicPick(is_panic=False)


def get_average_qb_round(tendencies: List[ManagerTendency]) -> float:
    """Get average round where owner typically drafts QBs"""
    qb_tendencies = [t for t in tendencies if t.position == "QB"]

    if not qb_tendencies:
        return 12.0  # Default late round

    total_rounds = sum(t.round * t.frequency for t in qb_tendencies)
    total_picks = sum(t.frequency for t in qb_tendencies)

    return total_rounds / total_picks if total_picks > 0 else 12.0


def get_player_position(player_id: str) -> str:
    """
    Get position for a player
    TODO: Implement actual player lookup
    """
    # Placeholder - should query player database
    return "RB"
