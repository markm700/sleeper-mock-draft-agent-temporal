import { logger, config } from '../config';
import { DraftPick, PositionRun } from '../types';

/**
 * Detect position runs during live draft
 * 
 * A run is detected when 3+ consecutive picks are the same position.
 * This triggers immediate scarcity adjustments for recommendations.
 */

export function detectPositionRun(
  recentPicks: DraftPick[],
  threshold: number = config.analysis.positionRunThreshold
): PositionRun {
  try {
    if (recentPicks.length < threshold) {
      return {
        detected: false,
        position: '',
        consecutive_count: 0,
        picks: [],
        scarcity_adjustment: 1.0,
      };
    }

    // Get last N picks
    const lastPicks = recentPicks.slice(-threshold);
    
    // Extract positions from metadata or lookup
    const positions = lastPicks.map(
      (pick) => pick.metadata?.position || 'UNKNOWN'
    );

    // Count occurrences of each position
    const positionCounts: { [pos: string]: number } = {};
    positions.forEach((pos) => {
      positionCounts[pos] = (positionCounts[pos] || 0) + 1;
    });

    // Find the most common position
    let maxPosition = '';
    let maxCount = 0;
    for (const [pos, count] of Object.entries(positionCounts)) {
      if (count > maxCount) {
        maxPosition = pos;
        maxCount = count;
      }
    }

    // Check if we have a run (threshold or more of same position)
    if (maxCount >= threshold) {
      const pickNumbers = lastPicks
        .filter((pick) => pick.metadata?.position === maxPosition)
        .map((pick) => pick.pick_no);

      // Calculate scarcity adjustment (higher multiplier = more urgent to draft)
      const scarcityAdjustment = 1.0 + maxCount * 0.15; // +15% per consecutive pick

      logger.info('Position run detected', {
        position: maxPosition,
        consecutiveCount: maxCount,
        picks: pickNumbers,
        scarcityAdjustment,
      });

      return {
        detected: true,
        position: maxPosition,
        consecutive_count: maxCount,
        picks: pickNumbers,
        scarcity_adjustment: scarcityAdjustment,
      };
    }

    return {
      detected: false,
      position: '',
      consecutive_count: 0,
      picks: [],
      scarcity_adjustment: 1.0,
    };
  } catch (error) {
    logger.error('Failed to detect position run', {
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

/**
 * Get position counts from recent picks
 */
export function getPositionCounts(picks: DraftPick[]): {
  [position: string]: number;
} {
  try {
    const counts: { [position: string]: number } = {};

    picks.forEach((pick) => {
      const position = pick.metadata?.position || 'UNKNOWN';
      counts[position] = (counts[position] || 0) + 1;
    });

    logger.debug('Position counts calculated', { counts });
    return counts;
  } catch (error) {
    logger.error('Failed to get position counts', {
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

/**
 * Calculate scarcity multiplier based on position run
 * Used to adjust player rankings during live draft
 */
export function calculateScarcityMultiplier(
  position: string,
  positionRun: PositionRun
): number {
  try {
    if (!positionRun.detected) {
      return 1.0;
    }

    // If the position matches the run position, increase urgency
    if (position === positionRun.position) {
      return positionRun.scarcity_adjustment;
    }

    // Other positions are slightly less urgent during a run
    return 0.95;
  } catch (error) {
    logger.error('Failed to calculate scarcity multiplier', {
      position,
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

/**
 * Analyze draft for all position runs in history
 * Used for post-draft analysis
 */
export function analyzePositionRuns(allPicks: DraftPick[]): PositionRun[] {
  try {
    const runs: PositionRun[] = [];
    const threshold = config.analysis.positionRunThreshold;

    // Slide through all picks looking for runs
    for (let i = threshold - 1; i < allPicks.length; i++) {
      const windowPicks = allPicks.slice(i - threshold + 1, i + 1);
      const run = detectPositionRun(windowPicks, threshold);

      if (run.detected) {
        // Avoid duplicate runs
        const lastRun = runs[runs.length - 1];
        if (
          !lastRun ||
          lastRun.position !== run.position ||
          !lastRun.picks.some((pick) => run.picks.includes(pick))
        ) {
          runs.push(run);
        }
      }
    }

    logger.info('Position runs analyzed', { totalRuns: runs.length });
    return runs;
  } catch (error) {
    logger.error('Failed to analyze position runs', {
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}
