import { logger, config } from '../config';
import { DraftPick, PanicPick, ManagerTendency } from '../types';

/**
 * Detect panic picks - when owners deviate significantly from historical patterns
 * 
 * A panic pick is flagged when:
 * 1. Owner picks a position much earlier than their historical pattern
 * 2. Deviation is 3+ standard deviations (sigma)
 * 3. Example: Owner who never takes QB early suddenly takes 3rd QB in round 5
 */

export async function detectPanicPick(
  pick: DraftPick,
  userId: string,
  round: number,
  managerTendencies: ManagerTendency[]
): Promise<PanicPick> {
  try {
    const position = pick.metadata?.position || 'UNKNOWN';

    // Get owner's historical tendencies for this position
    const tendencies = managerTendencies.filter(
      (t) => t.user_id === userId && t.position === position
    );

    if (tendencies.length === 0) {
      logger.debug('No historical tendencies found for owner', {
        userId,
        position,
      });
      return {
        detected: false,
        roster_id: pick.roster_id,
        player_id: pick.player_id,
        position,
        expected_position: '',
        sigma_deviation: 0,
        reason: 'No historical data available',
      };
    }

    // Calculate average round for this position
    const avgRound =
      tendencies.reduce((sum, t) => sum + t.round * t.frequency, 0) /
      tendencies.reduce((sum, t) => sum + t.frequency, 0);

    // Calculate standard deviation
    const variance =
      tendencies.reduce(
        (sum, t) => sum + Math.pow(t.round - avgRound, 2) * t.frequency,
        0
      ) / tendencies.reduce((sum, t) => sum + t.frequency, 0);
    const stdDev = Math.sqrt(variance);

    // Calculate sigma deviation
    const sigmaDeviation = (avgRound - round) / (stdDev || 1);

    // Check if this is a panic pick (3+ sigma deviation, picking earlier than usual)
    const isPanic =
      Math.abs(sigmaDeviation) >= config.analysis.panicPickSigma &&
      round < avgRound;

    if (isPanic) {
      logger.warn('Panic pick detected', {
        userId,
        playerId: pick.player_id,
        position,
        round,
        avgRound,
        sigmaDeviation,
      });

      return {
        detected: true,
        roster_id: pick.roster_id,
        player_id: pick.player_id,
        position,
        expected_position: getMostLikelyPosition(managerTendencies, round),
        sigma_deviation: sigmaDeviation,
        reason: `Picked ${position} in round ${round}, typically picks in round ${avgRound.toFixed(1)} (${sigmaDeviation.toFixed(1)}σ early)`,
      };
    }

    return {
      detected: false,
      roster_id: pick.roster_id,
      player_id: pick.player_id,
      position,
      expected_position: '',
      sigma_deviation: sigmaDeviation,
      reason: 'Within normal historical range',
    };
  } catch (error) {
    logger.error('Failed to detect panic pick', {
      playerId: pick.player_id,
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

/**
 * Get the most likely position for an owner to pick in a given round
 */
function getMostLikelyPosition(
  tendencies: ManagerTendency[],
  round: number
): string {
  try {
    const roundTendencies = tendencies.filter(
      (t) => Math.abs(t.round - round) <= 1
    );

    if (roundTendencies.length === 0) {
      return 'UNKNOWN';
    }

    // Find position with highest frequency
    let maxFrequency = 0;
    let mostLikelyPosition = '';

    roundTendencies.forEach((t) => {
      if (t.frequency > maxFrequency) {
        maxFrequency = t.frequency;
        mostLikelyPosition = t.position;
      }
    });

    return mostLikelyPosition;
  } catch (error) {
    logger.error('Failed to get most likely position', {
      round,
      error: error instanceof Error ? error.message : String(error),
    });
    return 'UNKNOWN';
  }
}

/**
 * Calculate reach for a pick (how many rounds early/late compared to ADP)
 */
export function calculateReach(
  pickNumber: number,
  adpRank: number,
  teamsCount: number = config.league.teams
): number {
  try {
    // Convert pick number to round
    const pickRound = Math.ceil(pickNumber / teamsCount);

    // Convert ADP rank to expected round
    const adpRound = Math.ceil(adpRank / teamsCount);

    // Positive reach = picked early, negative reach = picked late
    const reach = adpRound - pickRound;

    logger.debug('Reach calculated', {
      pickNumber,
      adpRank,
      pickRound,
      adpRound,
      reach,
    });

    return reach;
  } catch (error) {
    logger.error('Failed to calculate reach', {
      pickNumber,
      adpRank,
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

/**
 * Analyze all picks for panic picks (post-draft analysis)
 */
export async function analyzePanicPicks(
  picks: DraftPick[],
  managerTendencies: ManagerTendency[]
): Promise<PanicPick[]> {
  try {
    const panicPicks: PanicPick[] = [];

    for (const pick of picks) {
      // Skip keeper picks
      if (pick.is_keeper) {
        continue;
      }

      // TODO: Get user_id from roster_id
      const userId = pick.roster_id; // Placeholder

      const result = await detectPanicPick(
        pick,
        userId,
        pick.round,
        managerTendencies
      );

      if (result.detected) {
        panicPicks.push(result);
      }
    }

    logger.info('Panic picks analyzed', { count: panicPicks.length });
    return panicPicks;
  } catch (error) {
    logger.error('Failed to analyze panic picks', {
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}
