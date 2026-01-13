from typing import Dict, List
from src.models.types import Player, KeeperValue, KeeperCombo


def calculate_keeper_value(
    player: Player,
    keep_cost: int,
    owner_history: Dict[str, float],
    position_scarcity: Dict[str, float],
    projected_round: int,
    avg_value_at_round: float,
) -> KeeperValue:
    """
    Calculate keeper value with opportunity cost and owner/position weighting
    """
    base_value = projected_round - keep_cost

    # Opportunity cost calculation
    projected_points = get_projected_points(player)  # TODO: Implement projection logic
    opportunity_cost = projected_points - avg_value_at_round

    # Owner tendency multiplier (primary weight)
    owner_multiplier = owner_history.get(player.position, 1.0)

    # Position scarcity (secondary weight)
    scarcity_multiplier = position_scarcity.get(player.position, 1.0)

    total_value = (
        base_value * owner_multiplier * scarcity_multiplier + opportunity_cost * 0.3
    )

    # Confidence score based on data quality
    confidence = calculate_confidence(player, owner_history, keep_cost)

    return KeeperValue(
        player=player,
        keep_cost=keep_cost,
        projected_round=projected_round,
        base_value=base_value,
        opportunity_cost=opportunity_cost,
        total_value=total_value,
        confidence=confidence,
    )


def get_best_2_keeper_combo(
    players: List[Player],
    keep_costs: Dict[str, int],
    owner_history: Dict[str, float],
    position_scarcity: Dict[str, float],
    projected_rounds: Dict[str, int],
    avg_values_at_round: Dict[int, float],
) -> KeeperCombo:
    """Find best 2-keeper combination"""
    combos: List[KeeperCombo] = []

    # Generate all 2-player combinations
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            player1 = players[i]
            player2 = players[j]

            value1 = calculate_keeper_value(
                player1,
                keep_costs[player1.player_id],
                owner_history,
                position_scarcity,
                projected_rounds[player1.player_id],
                avg_values_at_round[keep_costs[player1.player_id]],
            )

            value2 = calculate_keeper_value(
                player2,
                keep_costs[player2.player_id],
                owner_history,
                position_scarcity,
                projected_rounds[player2.player_id],
                avg_values_at_round[keep_costs[player2.player_id]],
            )

            total_value = value1.total_value + value2.total_value
            position_diversity = 1.2 if player1.position != player2.position else 1.0

            combos.append(
                KeeperCombo(
                    players=[player1, player2],
                    total_value=total_value * position_diversity,
                    position_diversity=position_diversity,
                )
            )

    # Sort by total value and return best
    combos.sort(key=lambda x: x.total_value, reverse=True)
    return combos[0]


def get_average_value_at_round(round_num: int) -> float:
    """Get average value of players available at a specific round"""
    # TODO: Implement based on historical data
    return 0.0


def get_projected_points(player: Player) -> float:
    """Get projected points for a player"""
    # TODO: Implement projection logic based on historical performance
    return 0.0


def calculate_confidence(
    player: Player, owner_history: Dict[str, float], keep_cost: int
) -> float:
    """Calculate confidence score for keeper prediction"""
    confidence = 0.5  # Base confidence

    # Increase confidence if owner has history with this position
    if player.position in owner_history and owner_history[player.position] > 0.3:
        confidence += 0.2

    # Increase confidence for reasonable keep costs
    if 1 <= keep_cost <= 12:
        confidence += 0.15

    # Increase confidence for recent player data
    if player.last_updated:
        from datetime import datetime

        days_since_update = (datetime.now() - player.last_updated).days
        if days_since_update < 30:
            confidence += 0.15

    return min(confidence, 1.0)
