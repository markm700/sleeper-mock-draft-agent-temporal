import { DraftPick, DraftPhilosophy } from '../types';

/**
 * Detect draft philosophy based on early round picks
 */
export function detectDraftPhilosophy(ownerPicks: DraftPick[]): DraftPhilosophy {
  const earlyRounds = ownerPicks.filter(p => p.round <= 5);

  if (earlyRounds.length === 0) {
    return 'Balanced';
  }

  // Count positions in early rounds
  const positionCounts: Record<string, number> = {};
  earlyRounds.forEach(pick => {
    const position = getPlayerPosition(pick.player_id); // TODO: Implement player lookup
    positionCounts[position] = (positionCounts[position] || 0) + 1;
  });

  const rbCount = positionCounts['RB'] || 0;
  const wrCount = positionCounts['WR'] || 0;
  const firstPickPosition = getPlayerPosition(earlyRounds[0].player_id);

  // Zero-RB: No RBs, multiple WRs early
  if (rbCount === 0 && wrCount >= 3) {
    return 'Zero-RB';
  }

  // Hero-RB: One RB early, then WR focus
  if (rbCount >= 1 && firstPickPosition === 'RB' && wrCount >= 2) {
    return 'Hero-RB';
  }

  // Robust-RB: Multiple RBs early
  if (rbCount >= 3) {
    return 'Robust-RB';
  }

  // WR-Heavy: WR focus
  if (wrCount >= 3) {
    return 'WR-Heavy';
  }

  return 'Balanced';
}

/**
 * Predict next pick based on philosophy
 */
export function predictByPhilosophy(
  philosophy: DraftPhilosophy,
  currentRoster: string[],
  round: number,
  availablePlayers: any[]
): { position: string; confidence: number } {
  const positions = currentRoster.map(pid => getPlayerPosition(pid));
  const rbCount = positions.filter(p => p === 'RB').length;
  const wrCount = positions.filter(p => p === 'WR').length;

  switch (philosophy) {
    case 'Zero-RB':
      if (round <= 5) {
        return { position: 'WR', confidence: 0.9 };
      }
      if (round >= 6 && rbCount < 2) {
        return { position: 'RB', confidence: 0.8 };
      }
      break;

    case 'Hero-RB':
      if (round === 1) {
        return { position: 'RB', confidence: 0.95 };
      }
      if (round <= 4 && wrCount < 2) {
        return { position: 'WR', confidence: 0.85 };
      }
      break;

    case 'Robust-RB':
      if (round <= 4 && rbCount < 3) {
        return { position: 'RB', confidence: 0.9 };
      }
      break;

    case 'WR-Heavy':
      if (round <= 5 && wrCount < 3) {
        return { position: 'WR', confidence: 0.85 };
      }
      break;
  }

  return { position: 'BPA', confidence: 0.5 };
}

/**
 * Get position for a player
 * TODO: Implement actual player lookup
 */
function getPlayerPosition(playerId: string): string {
  // Placeholder - should query player database
  return 'RB';
}
