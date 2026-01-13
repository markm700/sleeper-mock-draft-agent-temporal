import { db } from './database/db';
import { liveDraftService } from './services/live-draft-service';

/**
 * Main entry point for the application
 * Can be extended to include API server, CLI interface, etc.
 */
async function main() {
  console.log('Sleeper Mock Draft Agent v1.0.0\n');

  // Initialize database
  await db.initialize();

  // Example: Get recommendations for a draft state
  // This would typically be called via API or CLI
  const draftState = {
    // ... draft state data
  };

  // Uncomment to test live draft service:
  // const recommendations = await liveDraftService.getRecommendations(
  //   'username',
  //   draftState,
  //   1
  // );
  // console.log(recommendations);

  console.log('\nReady for draft analysis!');
  console.log('Run "npm run import" to import historical data');
  console.log('Run "npm run analyze" to generate predictions');
}

// Run if called directly
if (require.main === module) {
  main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

export { main };
