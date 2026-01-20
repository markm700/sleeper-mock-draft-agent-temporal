import { logger, config } from './config';
import { SleeperClient } from './api/sleeper-client';
import { DatabasePool } from './database/db';
import { DataImportService } from './services/data-import-service';
import { AnalysisService } from './services/analysis-service';
import { LiveDraftService } from './services/live-draft-service';

/**
 * Main entry point for Sleeper Mock Draft Agent
 */
async function main() {
  logger.info('Starting Sleeper Mock Draft Agent', {
    env: config.app.env,
    port: config.app.port,
  });

  let db: DatabasePool | null = null;

  try {
    // Initialize database connection
    db = new DatabasePool();
    await db.initialize();
    logger.info('Database connection established');

    // Initialize Sleeper API client
    const sleeperClient = new SleeperClient();
    logger.info('Sleeper API client initialized');

    // Initialize services
    const dataImportService = new DataImportService(sleeperClient, db);
    const analysisService = new AnalysisService(db);
    const liveDraftService = new LiveDraftService(sleeperClient, db);

    logger.info('All services initialized successfully');

    // TODO: Add Express server or CLI interface here
    // Example: Start HTTP server for live draft recommendations
    // Example: Expose endpoints for data import, analysis, live draft

    // Keep process running
    process.on('SIGINT', async () => {
      logger.info('Received SIGINT, shutting down gracefully...');
      await shutdown(db);
    });

    process.on('SIGTERM', async () => {
      logger.info('Received SIGTERM, shutting down gracefully...');
      await shutdown(db);
    });

    logger.info('Application started successfully');
  } catch (error) {
    logger.error('Failed to start application', {
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
    await shutdown(db);
    process.exit(1);
  }
}

/**
 * Graceful shutdown handler
 */
async function shutdown(db: DatabasePool | null) {
  try {
    if (db) {
      await db.close();
      logger.info('Database connection closed');
    }
    logger.info('Application shutdown complete');
    process.exit(0);
  } catch (error) {
    logger.error('Error during shutdown', {
      error: error instanceof Error ? error.message : String(error),
    });
    process.exit(1);
  }
}

// Start application
if (require.main === module) {
  main().catch((error) => {
    logger.error('Unhandled error in main', {
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
    process.exit(1);
  });
}

export { main };
