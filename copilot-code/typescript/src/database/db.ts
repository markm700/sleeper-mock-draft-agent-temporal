import { Pool, PoolClient, QueryResult } from 'pg';
import { logger, config } from '../config';

/**
 * PostgreSQL database connection pool with context manager
 */
export class DatabasePool {
  private pool: Pool | null = null;

  constructor() {
    logger.debug('DatabasePool constructor called');
  }

  /**
   * Initialize the connection pool
   */
  async initialize(): Promise<void> {
    try {
      this.pool = new Pool({
        host: config.database.host,
        port: config.database.port,
        database: config.database.database,
        user: config.database.user,
        password: config.database.password,
        max: config.database.max,
        idleTimeoutMillis: config.database.idleTimeoutMillis,
        connectionTimeoutMillis: config.database.connectionTimeoutMillis,
      });

      // Test connection
      const client = await this.pool.connect();
      await client.query('SELECT NOW()');
      client.release();

      logger.info('Database pool initialized successfully', {
        host: config.database.host,
        database: config.database.database,
        maxConnections: config.database.max,
      });
    } catch (error) {
      logger.error('Failed to initialize database pool', {
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      });
      throw new Error(`Database initialization failed: ${error}`);
    }
  }

  /**
   * Get a client from the pool
   */
  async getClient(): Promise<PoolClient> {
    if (!this.pool) {
      throw new Error('Database pool not initialized');
    }

    try {
      const client = await this.pool.connect();
      logger.debug('Database client acquired from pool');
      return client;
    } catch (error) {
      logger.error('Failed to get database client', {
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error(`Failed to get database client: ${error}`);
    }
  }

  /**
   * Execute a query with automatic client management
   */
  async query<T extends Record<string, any> = any>(
    text: string,
    params?: any[]
  ): Promise<QueryResult<T>> {
    if (!this.pool) {
      throw new Error('Database pool not initialized');
    }

    const client = await this.getClient();
    try {
      logger.debug('Executing query', { text, paramCount: params?.length || 0 });
      const result = await client.query<T>(text, params);
      logger.debug('Query executed successfully', { rowCount: result.rowCount });
      return result;
    } catch (error) {
      logger.error('Query execution failed', {
        query: text,
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      });
      throw error;
    } finally {
      client.release();
      logger.debug('Database client released');
    }
  }

  /**
   * Execute a query within a transaction
   */
  async transaction<T extends Record<string, any> = any>(
    callback: (client: PoolClient) => Promise<T>
  ): Promise<T> {
    if (!this.pool) {
      throw new Error('Database pool not initialized');
    }

    const client = await this.getClient();
    try {
      await client.query('BEGIN');
      logger.debug('Transaction started');

      const result = await callback(client);

      await client.query('COMMIT');
      logger.debug('Transaction committed');

      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      logger.error('Transaction rolled back', {
        error: error instanceof Error ? error.message : String(error),
      });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Close the connection pool
   */
  async close(): Promise<void> {
    if (this.pool) {
      try {
        await this.pool.end();
        this.pool = null;
        logger.info('Database pool closed successfully');
      } catch (error) {
        logger.error('Failed to close database pool', {
          error: error instanceof Error ? error.message : String(error),
        });
        throw error;
      }
    }
  }

  /**
   * Check if pool is initialized
   */
  isInitialized(): boolean {
    return this.pool !== null;
  }
}

/**
 * Context manager for database transactions
 */
export async function withTransaction<T extends Record<string, any> = any>(
  db: DatabasePool,
  callback: (client: PoolClient) => Promise<T>
): Promise<T> {
  return db.transaction(callback);
}

export default DatabasePool;
