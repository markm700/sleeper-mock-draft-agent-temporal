import { Player, StackingRecommendation, DraftState } from '../types';

/**
 * Generate QB-WR stacking recommendations
 * Only applicable in middle rounds (4-10)
 */
export function generateStackingRecs(
  availablePlayers: Player[],
  rosterState: Player[],
  round: number
): StackingRecommendation[] {
  // Only recommend stacks in middle rounds
  if (round < 4 || round > 10) {
    return [];
  }

  // Check if user has a QB
  const qbOnRoster = rosterState.filter(p => p.position === 'QB');

  if (qbOnRoster.length === 0) {
    return [];
  }

  const qb = qbOnRoster[0];
  const qbTeam = qb.team;

  // Find available WRs from same team
  const availableWRs = availablePlayers.filter(
    p => p.position === 'WR' && p.team === qbTeam
  );

  // Generate stacking recommendations
  return availableWRs.map(wr => ({
    qb_id: qb.player_id,
    wr_id: wr.player_id,
    team: qbTeam,
    expected_value: calculateStackValue(qb, wr),
    correlation: 0.7, // QB-WR positive correlation
  }));
}

/**
 * Calculate expected value of a QB-WR stack
 */
function calculateStackValue(qb: Player, wr: Player): number {
  // TODO: Implement based on historical data
  // Should consider:
  // - QB passing volume
  // - WR target share
  // - Team pass rate
  // - Red zone opportunities

  // Placeholder
  return 0;
}

/**
 * Identify negative correlations to avoid
 * e.g., Two RBs from same team
 */
export function identifyNegativeCorrelations(
  player1: Player,
  player2: Player
): { hasConflict: boolean; reason?: string } {
  // Same position, same team = negative correlation
  if (player1.position === player2.position && player1.team === player2.team) {
    if (player1.position === 'RB' || player1.position === 'WR') {
      return {
        hasConflict: true,
        reason: `Multiple ${player1.position}s from ${player1.team}`,
      };
    }
  }

  return { hasConflict: false };
}
