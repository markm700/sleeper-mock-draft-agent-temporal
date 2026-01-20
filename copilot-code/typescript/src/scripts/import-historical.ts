import { logger } from '../config';
import { SleeperClient } from '../api/sleeper-client';
import { DatabasePool } from '../database/db';
import { DataImportService } from '../services/data-import-service';
import { playerCache } from '../utils/player-utils';

/**
 * Script to import historical draft data
 * Usage: npm run import-historical <username>
 */

async function main() {
  const username = process.argv[2];

  if (!username) {
    logger.error('Username required');
    console.error('Usage: npm run import-historical <username>');
    process.exit(1);
  }

  logger.info('Starting historical data import', { username });

  let db: DatabasePool | null = null;

  try {
    // Initialize database
    db = new DatabasePool();
    await db.initialize();
    logger.info('Database initialized');

    // Initialize Sleeper client
    const sleeperClient = new SleeperClient();

    // Initialize import service
    const importService = new DataImportService(sleeperClient, db);

    // Import player data first
    logger.info('Importing player data...');
    await importService.importPlayerData();

    // Load players into cache
    const players = await sleeperClient.getAllPlayers();
    await playerCache.loadPlayers(players);
    logger.info('Player cache loaded');

    // Import user's historical data
    logger.info('Importing user data...');
    await importService.importUserData(username);

    logger.info('Historical data import completed successfully');
    process.exit(0);
  } catch (error) {
    logger.error('Historical data import failed', {
      username,
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
    process.exit(1);
  } finally {
    if (db) {
      await db.close();
    }
  }
}

// Run script
if (require.main === module) {
  main().catch((error) => {
    logger.error('Unhandled error in import script', {
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
    process.exit(1);
  });
}

export { main };
