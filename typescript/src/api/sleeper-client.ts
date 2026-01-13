import axios, { AxiosInstance } from 'axios';
import { config } from '../config';

/**
 * Sleeper API Client
 * Handles all interactions with the Sleeper API
 * Rate limit: <1000 requests/minute
 */
export class SleeperClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: config.sleeper.baseUrl,
      timeout: 10000,
    });
  }

  /**
   * Get user ID from username
   */
  async getUser(username: string): Promise<any> {
    const response = await this.client.get(`/user/${username}`);
    return response.data;
  }

  /**
   * Get user's leagues for a specific season
   */
  async getUserLeagues(userId: string, season: number): Promise<any[]> {
    const response = await this.client.get(`/user/${userId}/leagues/nfl/${season}`);
    return response.data;
  }

  /**
   * Get draft details
   */
  async getDraft(draftId: string): Promise<any> {
    const response = await this.client.get(`/draft/${draftId}`);
    return response.data;
  }

  /**
   * Get all picks from a draft
   */
  async getDraftPicks(draftId: string): Promise<any[]> {
    const response = await this.client.get(`/draft/${draftId}/picks`);
    return response.data;
  }

  /**
   * Get traded picks from a draft
   */
  async getTradedPicks(draftId: string): Promise<any[]> {
    const response = await this.client.get(`/draft/${draftId}/traded_picks`);
    return response.data;
  }

  /**
   * Get league rosters
   */
  async getLeagueRosters(leagueId: string): Promise<any[]> {
    const response = await this.client.get(`/league/${leagueId}/rosters`);
    return response.data;
  }

  /**
   * Get matchups for a specific week
   */
  async getMatchups(leagueId: string, week: number): Promise<any[]> {
    const response = await this.client.get(`/league/${leagueId}/matchups/${week}`);
    return response.data;
  }

  /**
   * Get transactions for a specific week
   */
  async getTransactions(leagueId: string, week: number): Promise<any[]> {
    const response = await this.client.get(`/league/${leagueId}/transactions/${week}`);
    return response.data;
  }

  /**
   * Get all NFL players (should be cached daily)
   * Returns ~5MB of data
   */
  async getAllPlayers(): Promise<Record<string, any>> {
    const response = await this.client.get('/players/nfl');
    return response.data;
  }

  /**
   * Get current NFL state (season, week)
   */
  async getNFLState(): Promise<any> {
    const response = await this.client.get('/state/nfl');
    return response.data;
  }

  /**
   * Rate-limited sequential API call helper
   */
  async sequentialCalls<T>(
    calls: (() => Promise<T>)[],
    delayMs: number = 60
  ): Promise<T[]> {
    const results: T[] = [];
    for (const call of calls) {
      results.push(await call());
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
    return results;
  }
}

export const sleeperClient = new SleeperClient();
