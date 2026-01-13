import { Pool, PoolClient } from 'pg';
import { config } from '../config';

/**
 * Database connection pool
 */
export class Database {
  private pool: Pool;

  constructor() {
    this.pool = new Pool({
      host: config.database.host,
      port: config.database.port,
      database: config.database.name,
      user: config.database.user,
      password: config.database.password,
    });
  }

  /**
   * Get a client from the pool
   */
  async getClient(): Promise<PoolClient> {
    return this.pool.connect();
  }

  /**
   * Execute a query
   */
  async query(text: string, params?: any[]): Promise<any> {
    return this.pool.query(text, params);
  }

  /**
   * Close the pool
   */
  async close(): Promise<void> {
    await this.pool.end();
  }

  /**
   * Initialize database tables
   */
  async initialize(): Promise<void> {
    // TODO: Run schema.sql or create tables programmatically
    console.log('Database initialized');
  }
}

export const db = new Database();
