import axios, { AxiosInstance, AxiosError } from 'axios';
import { logger, config } from '../config';
import {
  User,
  Draft,
  DraftPick,
  Player,
  LeagueRoster,
  WeeklyMatchup,
  Transaction,
} from '../types';

/**
 * Sleeper API client with rate limiting, retries, and error handling
 * Base URL: https://api.sleeper.app/v1
 * Rate Limit: <1000 requests/minute
 * Auth: None required
 */
export class SleeperClient {
  private client: AxiosInstance;
  private requestCount: number = 0;
  private requestWindowStart: number = Date.now();

  constructor() {
    this.client = axios.create({
      baseURL: config.sleeper.baseUrl,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'SleeperMockDraftAgent/1.0',
      },
    });

    logger.info('SleeperClient initialized', {
      baseUrl: config.sleeper.baseUrl,
      rateLimit: config.sleeper.rateLimit,
    });
  }

  /**
   * Rate limiting check before making requests
   */
  private async checkRateLimit(): Promise<void> {
    const now = Date.now();
    const elapsed = now - this.requestWindowStart;

    if (elapsed >= 60000) {
      // Reset window every minute
      this.requestCount = 0;
      this.requestWindowStart = now;
    }

    if (this.requestCount >= config.sleeper.rateLimit) {
      const waitTime = 60000 - elapsed;
      logger.warn('Rate limit reached, waiting', { waitTime });
      await new Promise((resolve) => setTimeout(resolve, waitTime));
      this.requestCount = 0;
      this.requestWindowStart = Date.now();
    }

    this.requestCount++;
  }

  /**
   * Retry logic for failed requests
   */
  private async retryRequest<T>(
    fn: () => Promise<T>,
    attempt: number = 1
  ): Promise<T> {
    try {
      return await fn();
    } catch (error) {
      if (attempt >= config.sleeper.retryAttempts) {
        throw error;
      }

      const delay = config.sleeper.retryDelay * attempt;
      logger.warn('Request failed, retrying', { attempt, delay });
      await new Promise((resolve) => setTimeout(resolve, delay));
      return this.retryRequest(fn, attempt + 1);
    }
  }

  /**
   * Get user by username
   * GET /user/<username>
   */
  async getUser(username: string): Promise<User> {
    await this.checkRateLimit();

    try {
      logger.debug('Fetching user', { username });
      const response = await this.retryRequest(() =>
        this.client.get<User>(`/user/${username}`)
      );
      logger.info('User fetched successfully', { user_id: response.data.user_id });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch user', {
        username,
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error(`Failed to fetch user ${username}: ${error}`);
    }
  }

  /**
   * Get user's leagues for a season
   * GET /user/<user_id>/leagues/nfl/<season>
   */
  async getUserLeagues(userId: string, season: number): Promise<any[]> {
    await this.checkRateLimit();

    try {
      logger.debug('Fetching user leagues', { userId, season });
      const response = await this.retryRequest(() =>
        this.client.get<any[]>(`/user/${userId}/leagues/nfl/${season}`)
      );
      logger.info('User leagues fetched', {
        userId,
        season,
        count: response.data.length,
      });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch user leagues', {
        userId,
        season,
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error(`Failed to fetch leagues for user ${userId}: ${error}`);
    }
  }

  /**
   * Get draft details
   * GET /draft/<draft_id>
   */
  async getDraft(draftId: string): Promise<Draft> {
    await this.checkRateLimit();

    try {
      logger.debug('Fetching draft', { draftId });
      const response = await this.retryRequest(() =>
        this.client.get<Draft>(`/draft/${draftId}`)
      );
      logger.info('Draft fetched successfully', { draftId, status: response.data.status });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch draft', {
        draftId,
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error(`Failed to fetch draft ${draftId}: ${error}`);
    }
  }

  /**
   * Get draft picks
   * GET /draft/<draft_id>/picks
   */
  async getDraftPicks(draftId: string): Promise<DraftPick[]> {
    await this.checkRateLimit();

    try {
      logger.debug('Fetching draft picks', { draftId });
      const response = await this.retryRequest(() =>
        this.client.get<DraftPick[]>(`/draft/${draftId}/picks`)
      );
      logger.info('Draft picks fetched', {
        draftId,
        count: response.data.length,
      });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch draft picks', {
        draftId,
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error(`Failed to fetch draft picks for ${draftId}: ${error}`);
    }
  }

  /**
   * Get traded draft picks
   * GET /draft/<draft_id>/traded_picks
   */
  async getTradedPicks(draftId: string): Promise<any[]> {
    await this.checkRateLimit();

    try {
      logger.debug('Fetching traded picks', { draftId });
      const response = await this.retryRequest(() =>
        this.client.get<any[]>(`/draft/${draftId}/traded_picks`)
      );
      logger.info('Traded picks fetched', {
        draftId,
        count: response.data.length,
      });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch traded picks', {
        draftId,
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error(`Failed to fetch traded picks for ${draftId}: ${error}`);
    }
  }

  /**
   * Get league rosters
   * GET /league/<league_id>/rosters
   */
  async getLeagueRosters(leagueId: string): Promise<LeagueRoster[]> {
    await this.checkRateLimit();

    try {
      logger.debug('Fetching league rosters', { leagueId });
      const response = await this.retryRequest(() =>
        this.client.get<LeagueRoster[]>(`/league/${leagueId}/rosters`)
      );
      logger.info('League rosters fetched', {
        leagueId,
        count: response.data.length,
      });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch league rosters', {
        leagueId,
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error(`Failed to fetch rosters for ${leagueId}: ${error}`);
    }
  }

  /**
   * Get weekly matchups
   * GET /league/<league_id>/matchups/<week>
   */
  async getWeeklyMatchups(leagueId: string, week: number): Promise<WeeklyMatchup[]> {
    await this.checkRateLimit();

    try {
      logger.debug('Fetching weekly matchups', { leagueId, week });
      const response = await this.retryRequest(() =>
        this.client.get<WeeklyMatchup[]>(`/league/${leagueId}/matchups/${week}`)
      );
      logger.info('Weekly matchups fetched', {
        leagueId,
        week,
        count: response.data.length,
      });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch weekly matchups', {
        leagueId,
        week,
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error(`Failed to fetch matchups for ${leagueId} week ${week}: ${error}`);
    }
  }

  /**
   * Get weekly transactions
   * GET /league/<league_id>/transactions/<week>
   */
  async getWeeklyTransactions(
    leagueId: string,
    week: number
  ): Promise<Transaction[]> {
    await this.checkRateLimit();

    try {
      logger.debug('Fetching weekly transactions', { leagueId, week });
      const response = await this.retryRequest(() =>
        this.client.get<Transaction[]>(`/league/${leagueId}/transactions/${week}`)
      );
      logger.info('Weekly transactions fetched', {
        leagueId,
        week,
        count: response.data.length,
      });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch weekly transactions', {
        leagueId,
        week,
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error(
        `Failed to fetch transactions for ${leagueId} week ${week}: ${error}`
      );
    }
  }

  /**
   * Get all NFL players
   * GET /players/nfl
   * Returns ~5MB JSON, should be cached daily
   */
  async getAllPlayers(): Promise<{ [playerId: string]: Player }> {
    await this.checkRateLimit();

    try {
      logger.debug('Fetching all NFL players');
      const response = await this.retryRequest(() =>
        this.client.get<{ [playerId: string]: Player }>('/players/nfl')
      );
      const playerCount = Object.keys(response.data).length;
      logger.info('All NFL players fetched', { count: playerCount });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch all players', {
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error(`Failed to fetch all players: ${error}`);
    }
  }

  /**
   * Get current NFL state (season, week)
   * GET /state/nfl
   */
  async getNFLState(): Promise<any> {
    await this.checkRateLimit();

    try {
      logger.debug('Fetching NFL state');
      const response = await this.retryRequest(() =>
        this.client.get<any>('/state/nfl')
      );
      logger.info('NFL state fetched', {
        season: response.data.season,
        week: response.data.week,
      });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch NFL state', {
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error(`Failed to fetch NFL state: ${error}`);
    }
  }
}
