import { Player, KeeperValue, KeeperCombo, ManagerTendency } from '../types';

/**
 * Calculate keeper value with opportunity cost and owner/position weighting
 */
export function calculateKeeperValue(
  player: Player,
  keepCost: number,
  ownerHistory: Record<string, number>,
  positionScarcity: Record<string, number>,
  projectedRound: number,
  avgValueAtRound: number
): KeeperValue {
  const baseValue = projectedRound - keepCost;

  // Opportunity cost calculation
  const projectedPoints = getProjectedPoints(player); // TODO: Implement projection logic
  const opportunityCost = projectedPoints - avgValueAtRound;

  // Owner tendency multiplier (primary weight)
  const ownerMultiplier = ownerHistory[player.position] || 1.0;

  // Position scarcity (secondary weight)
  const scarcityMultiplier = positionScarcity[player.position] || 1.0;

  const totalValue =
    baseValue * ownerMultiplier * scarcityMultiplier + opportunityCost * 0.3;

  // Confidence score based on data quality
  const confidence = calculateConfidence(player, ownerHistory, keepCost);

  return {
    player,
    keep_cost: keepCost,
    projected_round: projectedRound,
    base_value: baseValue,
    opportunity_cost: opportunityCost,
    total_value: totalValue,
    confidence,
  };
}

/**
 * Find best 2-keeper combination
 */
export function getBest2KeeperCombo(
  players: Player[],
  keepCosts: Record<string, number>,
  ownerHistory: Record<string, number>,
  positionScarcity: Record<string, number>,
  projectedRounds: Record<string, number>,
  avgValuesAtRound: Record<number, number>
): KeeperCombo {
  const combos: KeeperCombo[] = [];

  // Generate all 2-player combinations
  for (let i = 0; i < players.length; i++) {
    for (let j = i + 1; j < players.length; j++) {
      const player1 = players[i];
      const player2 = players[j];

      const value1 = calculateKeeperValue(
        player1,
        keepCosts[player1.player_id],
        ownerHistory,
        positionScarcity,
        projectedRounds[player1.player_id],
        avgValuesAtRound[keepCosts[player1.player_id]]
      );

      const value2 = calculateKeeperValue(
        player2,
        keepCosts[player2.player_id],
        ownerHistory,
        positionScarcity,
        projectedRounds[player2.player_id],
        avgValuesAtRound[keepCosts[player2.player_id]]
      );

      const totalValue = value1.total_value + value2.total_value;
      const positionDiversity = player1.position !== player2.position ? 1.2 : 1.0;

      combos.push({
        players: [player1, player2],
        total_value: totalValue * positionDiversity,
        position_diversity: positionDiversity,
      });
    }
  }

  // Sort by total value and return best
  combos.sort((a, b) => b.total_value - a.total_value);
  return combos[0];
}

/**
 * Get average value of players available at a specific round
 */
export function getAverageValueAtRound(round: number): number {
  // TODO: Implement based on historical data
  // This should return the average projected points for players typically available at this round
  return 0;
}

/**
 * Get projected points for a player
 */
function getProjectedPoints(player: Player): number {
  // TODO: Implement projection logic based on historical performance
  return 0;
}

/**
 * Calculate confidence score for keeper prediction
 */
function calculateConfidence(
  player: Player,
  ownerHistory: Record<string, number>,
  keepCost: number
): number {
  let confidence = 0.5; // Base confidence

  // Increase confidence if owner has history with this position
  if (ownerHistory[player.position] && ownerHistory[player.position] > 0.3) {
    confidence += 0.2;
  }

  // Increase confidence for reasonable keep costs
  if (keepCost >= 1 && keepCost <= 12) {
    confidence += 0.15;
  }

  // Increase confidence for recent player data
  if (player.last_updated) {
    const daysSinceUpdate = Math.floor(
      (Date.now() - player.last_updated.getTime()) / (1000 * 60 * 60 * 24)
    );
    if (daysSinceUpdate < 30) {
      confidence += 0.15;
    }
  }

  return Math.min(confidence, 1.0);
}
