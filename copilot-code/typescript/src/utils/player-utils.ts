import { logger } from '../config';
import { Player } from '../types';

/**
 * Player cache for fast lookups
 */
class PlayerCache {
  private cache: Map<string, Player> = new Map();
  private lastUpdated: Date | null = null;

  /**
   * Load players into cache
   */
  async loadPlayers(players: { [playerId: string]: Player }): Promise<void> {
    try {
      this.cache.clear();

      for (const [playerId, player] of Object.entries(players)) {
        this.cache.set(playerId, player);
      }

      this.lastUpdated = new Date();

      logger.info('Player cache loaded', {
        count: this.cache.size,
        lastUpdated: this.lastUpdated,
      });
    } catch (error) {
      logger.error('Failed to load player cache', {
        error: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
  }

  /**
   * Get player by ID
   */
  getPlayer(playerId: string): Player | undefined {
    return this.cache.get(playerId);
  }

  /**
   * Search players by name
   */
  searchByName(searchTerm: string): Player[] {
    try {
      const term = searchTerm.toLowerCase();
      const results: Player[] = [];

      for (const player of this.cache.values()) {
        const fullName = player.full_name?.toLowerCase() || '';
        const firstName = player.first_name?.toLowerCase() || '';
        const lastName = player.last_name?.toLowerCase() || '';

        if (
          fullName.includes(term) ||
          firstName.includes(term) ||
          lastName.includes(term)
        ) {
          results.push(player);
        }
      }

      logger.debug('Player search completed', {
        searchTerm,
        resultsCount: results.length,
      });

      // Sort by search_rank
      return results.sort((a, b) => (a.search_rank || 999) - (b.search_rank || 999));
    } catch (error) {
      logger.error('Failed to search players', {
        searchTerm,
        error: error instanceof Error ? error.message : String(error),
      });
      return [];
    }
  }

  /**
   * Get players by position
   */
  getPlayersByPosition(position: string): Player[] {
    try {
      const results: Player[] = [];

      for (const player of this.cache.values()) {
        if (player.position === position) {
          results.push(player);
        }
      }

      logger.debug('Players filtered by position', {
        position,
        count: results.length,
      });

      return results.sort((a, b) => (a.search_rank || 999) - (b.search_rank || 999));
    } catch (error) {
      logger.error('Failed to get players by position', {
        position,
        error: error instanceof Error ? error.message : String(error),
      });
      return [];
    }
  }

  /**
   * Get players by team
   */
  getPlayersByTeam(team: string): Player[] {
    try {
      const results: Player[] = [];

      for (const player of this.cache.values()) {
        if (player.team === team) {
          results.push(player);
        }
      }

      logger.debug('Players filtered by team', {
        team,
        count: results.length,
      });

      return results.sort((a, b) => (a.search_rank || 999) - (b.search_rank || 999));
    } catch (error) {
      logger.error('Failed to get players by team', {
        team,
        error: error instanceof Error ? error.message : String(error),
      });
      return [];
    }
  }

  /**
   * Check if cache is stale (>30 days old)
   */
  isStale(): boolean {
    if (!this.lastUpdated) {
      return true;
    }

    const now = new Date();
    const daysSinceUpdate =
      (now.getTime() - this.lastUpdated.getTime()) / (1000 * 60 * 60 * 24);

    const stale = daysSinceUpdate > 30;

    if (stale) {
      logger.warn('Player cache is stale', {
        daysSinceUpdate: Math.floor(daysSinceUpdate),
      });
    }

    return stale;
  }

  /**
   * Get cache stats
   */
  getStats(): {
    size: number;
    lastUpdated: Date | null;
    isStale: boolean;
  } {
    return {
      size: this.cache.size,
      lastUpdated: this.lastUpdated,
      isStale: this.isStale(),
    };
  }

  /**
   * Clear cache
   */
  clear(): void {
    this.cache.clear();
    this.lastUpdated = null;
    logger.info('Player cache cleared');
  }
}

// Singleton instance
export const playerCache = new PlayerCache();

/**
 * Lookup player by ID with error handling
 */
export function lookupPlayer(playerId: string): Player | null {
  try {
    const player = playerCache.getPlayer(playerId);

    if (!player) {
      logger.warn('Player not found in cache', { playerId });
      return null;
    }

    return player;
  } catch (error) {
    logger.error('Failed to lookup player', {
      playerId,
      error: error instanceof Error ? error.message : String(error),
    });
    return null;
  }
}

/**
 * Lookup multiple players by IDs
 */
export function lookupPlayers(playerIds: string[]): Player[] {
  try {
    const players: Player[] = [];

    for (const playerId of playerIds) {
      const player = lookupPlayer(playerId);
      if (player) {
        players.push(player);
      }
    }

    logger.debug('Multiple players looked up', {
      requested: playerIds.length,
      found: players.length,
    });

    return players;
  } catch (error) {
    logger.error('Failed to lookup multiple players', {
      error: error instanceof Error ? error.message : String(error),
    });
    return [];
  }
}

/**
 * Format player name for display
 */
export function formatPlayerName(player: Player, includePosition: boolean = true): string {
  try {
    let name = player.full_name || `${player.first_name} ${player.last_name}`;

    if (includePosition && player.position) {
      name += ` (${player.position})`;
    }

    if (player.team) {
      name += ` - ${player.team}`;
    }

    return name;
  } catch (error) {
    logger.error('Failed to format player name', {
      playerId: player.player_id,
      error: error instanceof Error ? error.message : String(error),
    });
    return 'Unknown Player';
  }
}

/**
 * Check if player data is stale
 */
export function isPlayerDataStale(player: Player): boolean {
  try {
    if (!player.last_updated) {
      return true;
    }

    const now = new Date();
    const lastUpdated = new Date(player.last_updated);
    const daysSinceUpdate =
      (now.getTime() - lastUpdated.getTime()) / (1000 * 60 * 60 * 24);

    return daysSinceUpdate > 30;
  } catch (error) {
    logger.error('Failed to check if player data is stale', {
      playerId: player.player_id,
      error: error instanceof Error ? error.message : String(error),
    });
    return true;
  }
}

export default {
  playerCache,
  lookupPlayer,
  lookupPlayers,
  formatPlayerName,
  isPlayerDataStale,
};
