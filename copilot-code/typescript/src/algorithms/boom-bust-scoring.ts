import { logger } from '../config';
import { BoomBustProfile } from '../types';

/**
 * Boom/bust scoring for player variance analysis
 * 
 * Tracks high-variance vs. consistent floor players
 * Recommends by draft stage (early = floor, late = boom)
 */

interface PlayerPerformance {
  playerId: string;
  weeklyScores: number[];
  gamesPlayed: number;
}

export function calculateBoomBustScore(
  performance: PlayerPerformance
): BoomBustProfile {
  try {
    const { playerId, weeklyScores } = performance;

    if (weeklyScores.length === 0) {
      logger.warn('No weekly scores for player', { playerId });
      return {
        player_id: playerId,
        variance_score: 0,
        floor_score: 0,
        ceiling_score: 0,
        consistency_rating: 'floor',
        recommended_draft_stage: 'mid',
      };
    }

    // Calculate statistical measures
    const mean = weeklyScores.reduce((sum, score) => sum + score, 0) / weeklyScores.length;
    const variance =
      weeklyScores.reduce((sum, score) => sum + Math.pow(score - mean, 2), 0) /
      weeklyScores.length;
    const stdDev = Math.sqrt(variance);

    // Normalize variance score (0-1 scale)
    const varianceScore = Math.min(stdDev / mean, 1.0);

    // Floor: 20th percentile of scores
    const sortedScores = [...weeklyScores].sort((a, b) => a - b);
    const floorIndex = Math.floor(sortedScores.length * 0.2);
    const floorScore = sortedScores[floorIndex];

    // Ceiling: 80th percentile of scores
    const ceilingIndex = Math.floor(sortedScores.length * 0.8);
    const ceilingScore = sortedScores[ceilingIndex];

    // Classify player
    let consistencyRating: 'boom' | 'bust' | 'floor' | 'ceiling';
    let recommendedStage: 'early' | 'mid' | 'late';

    if (varianceScore > 0.4) {
      // High variance
      if (mean > 15) {
        consistencyRating = 'boom'; // High-variance, high-scoring
        recommendedStage = 'mid';
      } else {
        consistencyRating = 'bust'; // High-variance, low-scoring
        recommendedStage = 'late';
      }
    } else {
      // Low variance (consistent)
      if (floorScore > 12) {
        consistencyRating = 'floor'; // High floor
        recommendedStage = 'early';
      } else {
        consistencyRating = 'ceiling'; // High ceiling but lower floor
        recommendedStage = 'mid';
      }
    }

    logger.debug('Boom/bust score calculated', {
      playerId,
      varianceScore,
      floorScore,
      ceilingScore,
      consistencyRating,
    });

    return {
      player_id: playerId,
      variance_score: varianceScore,
      floor_score: floorScore,
      ceiling_score: ceilingScore,
      consistency_rating: consistencyRating,
      recommended_draft_stage: recommendedStage,
    };
  } catch (error) {
    logger.error('Failed to calculate boom/bust score', {
      playerId: performance.playerId,
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

/**
 * Get player recommendation based on draft stage
 * Early rounds: Prefer high floor
 * Late rounds: Prefer high ceiling/boom potential
 */
export function getRecommendationByStage(
  profiles: BoomBustProfile[],
  currentRound: number,
  totalRounds: number = 15
): BoomBustProfile[] {
  try {
    const stage =
      currentRound <= 5
        ? 'early'
        : currentRound >= 12
        ? 'late'
        : 'mid';

    logger.debug('Filtering by draft stage', { stage, currentRound });

    if (stage === 'early') {
      // Early rounds: Prefer consistent floor players
      return profiles
        .filter((p) => p.consistency_rating === 'floor')
        .sort((a, b) => b.floor_score - a.floor_score);
    } else if (stage === 'late') {
      // Late rounds: Prefer boom/upside players
      return profiles
        .filter(
          (p) =>
            p.consistency_rating === 'boom' ||
            p.consistency_rating === 'ceiling'
        )
        .sort((a, b) => b.ceiling_score - a.ceiling_score);
    } else {
      // Mid rounds: Balanced approach
      return profiles.sort(
        (a, b) =>
          b.floor_score +
          b.ceiling_score -
          (a.floor_score + a.ceiling_score)
      );
    }
  } catch (error) {
    logger.error('Failed to get recommendation by stage', {
      currentRound,
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

/**
 * Calculate weekly performance from historical data
 * TODO: Query database for player's weekly scores
 */
export async function getPlayerPerformance(
  playerId: string,
  seasons: number[]
): Promise<PlayerPerformance> {
  try {
    // TODO: Implement database query
    // SELECT week, points FROM player_performances
    // WHERE player_id = $1 AND season IN ($2)
    // ORDER BY season, week

    logger.debug('Getting player performance', { playerId, seasons });

    // Placeholder
    return {
      playerId,
      weeklyScores: [],
      gamesPlayed: 0,
    };
  } catch (error) {
    logger.error('Failed to get player performance', {
      playerId,
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

/**
 * Batch calculate boom/bust profiles for multiple players
 */
export async function calculateBatchBoomBust(
  playerIds: string[],
  seasons: number[]
): Promise<BoomBustProfile[]> {
  try {
    logger.info('Calculating boom/bust profiles', {
      playerCount: playerIds.length,
      seasons,
    });

    const profiles: BoomBustProfile[] = [];

    for (const playerId of playerIds) {
      const performance = await getPlayerPerformance(playerId, seasons);
      const profile = calculateBoomBustScore(performance);
      profiles.push(profile);
    }

    logger.info('Boom/bust profiles calculated', { count: profiles.length });
    return profiles;
  } catch (error) {
    logger.error('Failed to calculate batch boom/bust', {
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}
