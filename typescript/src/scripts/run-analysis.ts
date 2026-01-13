#!/usr/bin/env ts-node

import { analysisService } from '../services/analysis-service';

async function main() {
  try {
    await analysisService.runAnalysis();
  } catch (error) {
    console.error('Analysis failed:', error);
    process.exit(1);
  }
}

main();
