import { User, DraftPick, PanicPick, ManagerTendency } from '../types';

/**
 * Detect if a pick is a "panic pick" - significant deviation from owner's historical patterns
 */
export function isPanicPick(
  owner: User,
  pick: DraftPick,
  round: number,
  tendencies: ManagerTendency[]
): PanicPick {
  const roundTendencies = tendencies.filter(t => t.round === round);

  if (roundTendencies.length === 0) {
    return { isPanic: false };
  }

  // Build historical pattern for this round
  const historicalPattern: Record<string, number> = {};
  let totalPicks = 0;

  roundTendencies.forEach(t => {
    historicalPattern[t.position] = t.frequency;
    totalPicks += t.frequency;
  });

  // Normalize to percentages
  Object.keys(historicalPattern).forEach(pos => {
    historicalPattern[pos] = historicalPattern[pos] / totalPicks;
  });

  const pickPosition = getPlayerPosition(pick.player_id); // TODO: Implement player lookup

  // Check if position is expected for this owner in this round
  const expectedPositions = Object.keys(historicalPattern).filter(
    pos => historicalPattern[pos] > 0.2
  );

  if (!expectedPositions.includes(pickPosition)) {
    const deviation = 1.0 - (historicalPattern[pickPosition] || 0);

    // 3-sigma equivalent (85% deviation)
    if (deviation > 0.85) {
      return {
        isPanic: true,
        confidence: deviation,
        reason: `${pickPosition} rarely taken in Round ${round}`,
      };
    }
  }

  // Special case: Early QB reach
  if (pickPosition === 'QB' && round < 8) {
    const avgQBRound = getAverageQBRound(tendencies);
    if (avgQBRound > 10) {
      return {
        isPanic: true,
        confidence: 0.9,
        reason: 'QB reach (historically waits)',
      };
    }
  }

  return { isPanic: false };
}

/**
 * Get average round where owner typically drafts QBs
 */
function getAverageQBRound(tendencies: ManagerTendency[]): number {
  const qbTendencies = tendencies.filter(t => t.position === 'QB');

  if (qbTendencies.length === 0) {
    return 12; // Default late round
  }

  const totalRounds = qbTendencies.reduce((sum, t) => sum + t.round * t.frequency, 0);
  const totalPicks = qbTendencies.reduce((sum, t) => sum + t.frequency, 0);

  return totalRounds / totalPicks;
}

/**
 * Get position for a player
 * TODO: Implement actual player lookup
 */
function getPlayerPosition(playerId: string): string {
  // Placeholder - should query player database
  return 'RB';
}
