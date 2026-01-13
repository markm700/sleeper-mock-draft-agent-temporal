#!/usr/bin/env ts-node

import { dataImportService } from '../services/data-import-service';
import { config } from '../config';

async function main() {
  const username = config.sleeper.username || process.argv[2];

  if (!username) {
    console.error('Usage: npm run import <username>');
    console.error('Or set SLEEPER_USERNAME in .env');
    process.exit(1);
  }

  try {
    await dataImportService.importHistoricalData(username);
  } catch (error) {
    console.error('Import failed:', error);
    process.exit(1);
  }
}

main();
