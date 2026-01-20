import { logger } from '../config';
import { DatabasePool } from '../database/db';
import { AnalysisService } from '../services/analysis-service';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Script to run analysis on imported data
 * Usage: npm run run-analysis
 */

async function main() {
  logger.info('Starting analysis pipeline');

  let db: DatabasePool | null = null;

  try {
    // Initialize database
    db = new DatabasePool();
    await db.initialize();
    logger.info('Database initialized');

    // Initialize analysis service
    const analysisService = new AnalysisService(db);

    // Run full analysis
    logger.info('Running full analysis...');
    await analysisService.runFullAnalysis();

    // Generate report
    logger.info('Generating analysis report...');
    const report = await analysisService.generateReport();

    // Save report to file
    const reportsDir = path.join(process.cwd(), 'reports');
    if (!fs.existsSync(reportsDir)) {
      fs.mkdirSync(reportsDir, { recursive: true });
    }

    const timestamp = new Date().toISOString().replace(/:/g, '-').split('.')[0];
    const reportPath = path.join(reportsDir, `analysis-report-${timestamp}.md`);

    fs.writeFileSync(reportPath, report, 'utf-8');
    logger.info('Analysis report saved', { reportPath });

    console.log('\n' + report);
    console.log(`\nReport saved to: ${reportPath}`);

    logger.info('Analysis completed successfully');
    process.exit(0);
  } catch (error) {
    logger.error('Analysis failed', {
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
    logger.error('Unhandled error in analysis script', {
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
    process.exit(1);
  });
}

export { main };
