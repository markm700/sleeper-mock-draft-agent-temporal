from typing import List, Dict, Tuple
from src.models.types import DraftPick, DraftPhilosophy


def detect_draft_philosophy(owner_picks: List[DraftPick]) -> DraftPhilosophy:
    """Detect draft philosophy based on early round picks"""
    early_rounds = [p for p in owner_picks if p.round <= 5]

    if not early_rounds:
        return DraftPhilosophy.BALANCED

    # Count positions in early rounds
    position_counts = {}
    for pick in early_rounds:
        position = get_player_position(pick.player_id)
        position_counts[position] = position_counts.get(position, 0) + 1

    rb_count = position_counts.get("RB", 0)
    wr_count = position_counts.get("WR", 0)
    first_pick_position = get_player_position(early_rounds[0].player_id)

    # Zero-RB: No RBs, multiple WRs early
    if rb_count == 0 and wr_count >= 3:
        return DraftPhilosophy.ZERO_RB

    # Hero-RB: One RB early, then WR focus
    if rb_count >= 1 and first_pick_position == "RB" and wr_count >= 2:
        return DraftPhilosophy.HERO_RB

    # Robust-RB: Multiple RBs early
    if rb_count >= 3:
        return DraftPhilosophy.ROBUST_RB

    # WR-Heavy: WR focus
    if wr_count >= 3:
        return DraftPhilosophy.WR_HEAVY

    return DraftPhilosophy.BALANCED


def predict_by_philosophy(
    philosophy: DraftPhilosophy,
    current_roster: List[str],
    round_num: int,
    available_players: List,
) -> Tuple[str, float]:
    """Predict next pick based on philosophy"""
    positions = [get_player_position(pid) for pid in current_roster]
    rb_count = positions.count("RB")
    wr_count = positions.count("WR")

    if philosophy == DraftPhilosophy.ZERO_RB:
        if round_num <= 5:
            return "WR", 0.9
        if round_num >= 6 and rb_count < 2:
            return "RB", 0.8

    elif philosophy == DraftPhilosophy.HERO_RB:
        if round_num == 1:
            return "RB", 0.95
        if round_num <= 4 and wr_count < 2:
            return "WR", 0.85

    elif philosophy == DraftPhilosophy.ROBUST_RB:
        if round_num <= 4 and rb_count < 3:
            return "RB", 0.9

    elif philosophy == DraftPhilosophy.WR_HEAVY:
        if round_num <= 5 and wr_count < 3:
            return "WR", 0.85

    return "BPA", 0.5


def get_player_position(player_id: str) -> str:
    """
    Get position for a player
    TODO: Implement actual player lookup
    """
    # Placeholder - should query player database
    return "RB"
