from typing import List, Tuple
from src.models.types import Player, StackingRecommendation


def generate_stacking_recs(
    available_players: List[Player], roster_state: List[Player], round_num: int
) -> List[StackingRecommendation]:
    """
    Generate QB-WR stacking recommendations
    Only applicable in middle rounds (4-10)
    """
    # Only recommend stacks in middle rounds
    if round_num < 4 or round_num > 10:
        return []

    # Check if user has a QB
    qb_on_roster = [p for p in roster_state if p.position == "QB"]

    if not qb_on_roster:
        return []

    qb = qb_on_roster[0]
    qb_team = qb.team

    # Find available WRs from same team
    available_wrs = [
        p for p in available_players if p.position == "WR" and p.team == qb_team
    ]

    # Generate stacking recommendations
    return [
        StackingRecommendation(
            qb_id=qb.player_id,
            wr_id=wr.player_id,
            team=qb_team,
            expected_value=calculate_stack_value(qb, wr),
            correlation=0.7,  # QB-WR positive correlation
        )
        for wr in available_wrs
    ]


def calculate_stack_value(qb: Player, wr: Player) -> float:
    """Calculate expected value of a QB-WR stack"""
    # TODO: Implement based on historical data
    # Should consider:
    # - QB passing volume
    # - WR target share
    # - Team pass rate
    # - Red zone opportunities
    return 0.0


def identify_negative_correlations(
    player1: Player, player2: Player
) -> Tuple[bool, str]:
    """
    Identify negative correlations to avoid
    e.g., Two RBs from same team
    """
    # Same position, same team = negative correlation
    if player1.position == player2.position and player1.team == player2.team:
        if player1.position in ["RB", "WR"]:
            return (
                True,
                f"Multiple {player1.position}s from {player1.team}",
            )

    return False, ""
