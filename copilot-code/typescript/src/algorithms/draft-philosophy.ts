import { logger } from '../config';
import { DraftPick, ManagerTendency } from '../types';

/**
 * Draft philosophy detection and analysis
 * 
 * Detects patterns:
 * - Zero-RB: Avoids early RBs, focuses on WR/TE
 * - Hero-RB: Takes 1 elite RB early, then WR-heavy
 * - Robust-RB: Takes 2+ RBs in first 3 rounds
 * - Balanced: Even distribution across positions
 */

export type DraftPhilosophy = 'zero-rb' | 'hero-rb' | 'robust-rb' | 'balanced';

interface PhilosophyAnalysis {
  philosophy: DraftPhilosophy;
  confidence: number;
  evidence: string[];
  earlyRoundPattern: string;
}

export function detectDraftPhilosophy(
  picks: DraftPick[],
  userId: string
): PhilosophyAnalysis {
  try {
    // Filter picks for this user
    const userPicks = picks.filter((p) => p.picked_by === userId);

    if (userPicks.length === 0) {
      logger.warn('No picks found for user', { userId });
      return {
        philosophy: 'balanced',
        confidence: 0,
        evidence: ['No draft data available'],
        earlyRoundPattern: 'UNKNOWN',
      };
    }

    // Sort by round
    const sortedPicks = [...userPicks].sort((a, b) => a.round - b.round);

    // Analyze early rounds (1-5)
    const earlyPicks = sortedPicks.filter((p) => p.round <= 5);
    const earlyPositions = earlyPicks.map((p) => p.metadata?.position || 'UNKNOWN');

    // Count positions in early rounds
    const rbCountEarly = earlyPositions.filter((p) => p === 'RB').length;
    const wrCountEarly = earlyPositions.filter((p) => p === 'WR').length;
    const teCountEarly = earlyPositions.filter((p) => p === 'TE').length;

    const evidence: string[] = [];
    let philosophy: DraftPhilosophy;
    let confidence: number;

    // Zero-RB detection: 0-1 RB in first 5 rounds, 3+ WR
    if (rbCountEarly <= 1 && wrCountEarly >= 3) {
      philosophy = 'zero-rb';
      confidence = 0.9;
      evidence.push(
        `Only ${rbCountEarly} RB in first 5 rounds`,
        `${wrCountEarly} WRs drafted early`,
        'Classic Zero-RB strategy'
      );
    }
    // Hero-RB detection: Exactly 1 RB in first 2 rounds, then WR-heavy
    else if (rbCountEarly === 1 && sortedPicks[0]?.metadata?.position === 'RB') {
      const rb1Round = sortedPicks.find((p) => p.metadata?.position === 'RB')?.round || 0;
      if (rb1Round <= 2 && wrCountEarly >= 3) {
        philosophy = 'hero-rb';
        confidence = 0.85;
        evidence.push(
          `1 elite RB in round ${rb1Round}`,
          `Followed by ${wrCountEarly} WRs`,
          'Hero-RB approach'
        );
      } else {
        philosophy = 'balanced';
        confidence = 0.6;
        evidence.push('Mixed strategy with some RB emphasis');
      }
    }
    // Robust-RB detection: 2+ RBs in first 3 rounds
    else if (rbCountEarly >= 2) {
      const rb1Round = sortedPicks.find((p) => p.metadata?.position === 'RB')?.round || 0;
      const rb2Round =
        sortedPicks.filter((p) => p.metadata?.position === 'RB')[1]?.round || 0;

      if (rb1Round <= 3 && rb2Round <= 3) {
        philosophy = 'robust-rb';
        confidence = 0.9;
        evidence.push(
          `2+ RBs by round 3 (rounds ${rb1Round}, ${rb2Round})`,
          'Emphasizes RB depth',
          'Robust-RB strategy'
        );
      } else {
        philosophy = 'balanced';
        confidence = 0.7;
        evidence.push('Multiple RBs but spread across rounds');
      }
    }
    // Balanced: No clear pattern
    else {
      philosophy = 'balanced';
      confidence = 0.5;
      evidence.push(
        `${rbCountEarly} RBs, ${wrCountEarly} WRs, ${teCountEarly} TEs in first 5`,
        'No dominant strategy detected',
        'Balanced approach'
      );
    }

    const earlyRoundPattern = earlyPositions.slice(0, 5).join('-');

    logger.info('Draft philosophy detected', {
      userId,
      philosophy,
      confidence,
      earlyRoundPattern,
    });

    return {
      philosophy,
      confidence,
      evidence,
      earlyRoundPattern,
    };
  } catch (error) {
    logger.error('Failed to detect draft philosophy', {
      userId,
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

/**
 * Analyze draft philosophies for all users across multiple drafts
 */
export function analyzeAllPhilosophies(
  allPicks: DraftPick[],
  userIds: string[]
): Map<string, PhilosophyAnalysis> {
  try {
    const philosophies = new Map<string, PhilosophyAnalysis>();

    for (const userId of userIds) {
      const analysis = detectDraftPhilosophy(allPicks, userId);
      philosophies.set(userId, analysis);
    }

    logger.info('All philosophies analyzed', {
      userCount: userIds.length,
    });

    return philosophies;
  } catch (error) {
    logger.error('Failed to analyze all philosophies', {
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

/**
 * Get philosophy match score between player and owner
 * Used to recommend players that fit owner's historical philosophy
 */
export function getPhilosophyMatchScore(
  playerPosition: string,
  currentRound: number,
  ownerPhilosophy: DraftPhilosophy
): number {
  try {
    let matchScore = 0.5; // Default neutral score

    switch (ownerPhilosophy) {
      case 'zero-rb':
        if (playerPosition === 'WR' && currentRound <= 5) {
          matchScore = 0.9;
        } else if (playerPosition === 'TE' && currentRound <= 5) {
          matchScore = 0.8;
        } else if (playerPosition === 'RB' && currentRound <= 5) {
          matchScore = 0.2;
        }
        break;

      case 'hero-rb':
        if (playerPosition === 'RB' && currentRound <= 2) {
          matchScore = 0.95;
        } else if (playerPosition === 'WR' && currentRound >= 2 && currentRound <= 6) {
          matchScore = 0.85;
        }
        break;

      case 'robust-rb':
        if (playerPosition === 'RB' && currentRound <= 5) {
          matchScore = 0.9;
        } else if (playerPosition === 'WR' && currentRound >= 4) {
          matchScore = 0.75;
        }
        break;

      case 'balanced':
        matchScore = 0.6; // Neutral for all positions
        break;
    }

    logger.debug('Philosophy match score calculated', {
      playerPosition,
      currentRound,
      ownerPhilosophy,
      matchScore,
    });

    return matchScore;
  } catch (error) {
    logger.error('Failed to calculate philosophy match score', {
      error: error instanceof Error ? error.message : String(error),
    });
    return 0.5;
  }
}

/**
 * Predict next pick based on philosophy
 */
export function predictPositionByPhilosophy(
  ownerPhilosophy: DraftPhilosophy,
  currentRound: number,
  rosterComposition: { [position: string]: number }
): string[] {
  try {
    const predictions: string[] = [];

    // Check roster needs
    const needsQB = (rosterComposition['QB'] || 0) === 0 && currentRound >= 6;
    const needsTE = (rosterComposition['TE'] || 0) === 0 && currentRound >= 4;

    if (needsQB) {
      predictions.push('QB');
    }

    switch (ownerPhilosophy) {
      case 'zero-rb':
        predictions.push('WR', 'TE', 'WR');
        if (currentRound >= 6) predictions.push('RB');
        break;

      case 'hero-rb':
        if (currentRound <= 2 && (rosterComposition['RB'] || 0) === 0) {
          predictions.push('RB', 'WR', 'WR');
        } else {
          predictions.push('WR', 'WR', 'RB');
        }
        break;

      case 'robust-rb':
        if (currentRound <= 4) {
          predictions.push('RB', 'RB', 'WR');
        } else {
          predictions.push('WR', 'RB', 'TE');
        }
        break;

      case 'balanced':
        predictions.push('RB', 'WR', 'TE');
        break;
    }

    if (needsTE && !predictions.includes('TE')) {
      predictions.unshift('TE');
    }

    logger.debug('Position predicted by philosophy', {
      ownerPhilosophy,
      currentRound,
      predictions: predictions.slice(0, 3),
    });

    return predictions.slice(0, 3);
  } catch (error) {
    logger.error('Failed to predict position by philosophy', {
      error: error instanceof Error ? error.message : String(error),
    });
    return ['RB', 'WR', 'TE'];
  }
}
