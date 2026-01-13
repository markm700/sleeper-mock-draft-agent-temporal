import { DraftPick, PositionRun } from '../types';
import { config } from '../config';

/**
 * Detect if a position run is occurring
 * A run is detected when 3+ consecutive picks are the same position
 */
export function detectPositionRun(
  recentPicks: DraftPick[],
  threshold: number = config.algorithms.positionRunThreshold
): PositionRun {
  if (recentPicks.length < threshold) {
    return { detected: false };
  }

  const lastN = recentPicks.slice(-threshold);
  const positions = lastN.map(p => getPlayerPosition(p.player_id)); // TODO: Implement player lookup

  // Find most common position in recent picks
  const positionCounts: Record<string, number> = {};
  positions.forEach(pos => {
    positionCounts[pos] = (positionCounts[pos] || 0) + 1;
  });

  const mostCommon = Object.keys(positionCounts).reduce((a, b) =>
    positionCounts[a] > positionCounts[b] ? a : b
  );

  if (positionCounts[mostCommon] >= threshold) {
    return {
      detected: true,
      position: mostCommon,
      count: positionCounts[mostCommon],
    };
  }

  return { detected: false };
}

/**
 * Adjust scarcity multiplier based on position run
 * +15% per pick beyond threshold
 */
export function adjustScarcity(position: string, runCount: number): number {
  const baseMultiplier = config.algorithms.scarcityMultipliers[position as keyof typeof config.algorithms.scarcityMultipliers] || 1.0;
  const threshold = config.algorithms.positionRunThreshold;

  if (runCount <= threshold) {
    return baseMultiplier;
  }

  const additionalMultiplier = 1 + (runCount - threshold) * 0.15;
  return baseMultiplier * additionalMultiplier;
}

/**
 * Get position for a player
 * TODO: Implement actual player lookup
 */
function getPlayerPosition(playerId: string): string {
  // Placeholder - should query player database
  return 'RB';
}
