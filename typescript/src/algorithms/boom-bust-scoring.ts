import { Player, BoomBustProfile } from '../types';

interface WeeklyPerformance {
  week: number;
  points: number;
}

/**
 * Calculate boom/bust score based on historical weekly variance
 * Uses coefficient of variation (standard deviation / mean)
 */
export function calculateBoomBustScore(
  player: Player,
  historicalWeeks: WeeklyPerformance[]
): BoomBustProfile {
  if (historicalWeeks.length === 0) {
    return {
      type: 'balanced',
      score: 0.3,
      recommendation: 'Insufficient data',
    };
  }

  const weeklyScores = historicalWeeks.map(w => w.points);
  const mean = average(weeklyScores);
  const stdDev = standardDeviation(weeklyScores);

  // Coefficient of variation
  const coefficient = mean > 0 ? stdDev / mean : 0;

  // Classify player type
  if (coefficient > 0.5) {
    return {
      type: 'boom-bust',
      score: coefficient,
      recommendation: 'Late round lottery',
    };
  }

  if (coefficient < 0.2) {
    return {
      type: 'floor',
      score: coefficient,
      recommendation: 'Safe early pick',
    };
  }

  return {
    type: 'balanced',
    score: coefficient,
    recommendation: 'Flexible',
  };
}

/**
 * Calculate average of an array
 */
function average(numbers: number[]): number {
  if (numbers.length === 0) return 0;
  return numbers.reduce((sum, n) => sum + n, 0) / numbers.length;
}

/**
 * Calculate standard deviation
 */
function standardDeviation(numbers: number[]): number {
  if (numbers.length === 0) return 0;

  const mean = average(numbers);
  const squaredDiffs = numbers.map(n => Math.pow(n - mean, 2));
  const variance = average(squaredDiffs);

  return Math.sqrt(variance);
}

/**
 * Recommend players based on boom/bust profile and draft stage
 */
export function recommendByBoomBust(
  players: Player[],
  round: number,
  profiles: Record<string, BoomBustProfile>
): Player[] {
  // Early rounds (1-5): Prefer floor players
  if (round <= 5) {
    return players
      .filter(p => profiles[p.player_id]?.type === 'floor')
      .sort((a, b) => {
        const scoreA = profiles[a.player_id]?.score || 1;
        const scoreB = profiles[b.player_id]?.score || 1;
        return scoreA - scoreB;
      });
  }

  // Late rounds (12-15): Prefer boom-bust (lottery tickets)
  if (round >= 12) {
    return players
      .filter(p => profiles[p.player_id]?.type === 'boom-bust')
      .sort((a, b) => {
        const scoreA = profiles[a.player_id]?.score || 0;
        const scoreB = profiles[b.player_id]?.score || 0;
        return scoreB - scoreA;
      });
  }

  // Middle rounds: Balanced approach
  return players;
}
