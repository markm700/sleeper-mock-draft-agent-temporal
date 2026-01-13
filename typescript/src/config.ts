import dotenv from 'dotenv';

dotenv.config();

export const config = {
  // Database
  database: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432'),
    name: process.env.DB_NAME || 'sleeper_draft_agent',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || '',
  },

  // Sleeper API
  sleeper: {
    baseUrl: 'https://api.sleeper.app/v1',
    username: process.env.SLEEPER_USERNAME || '',
    rateLimit: 1000, // requests per minute
  },

  // League Configuration
  league: {
    teams: 10,
    rounds: 15,
    scoring: 'PPR',
    draftType: 'snake',
    seasons: [2021, 2022, 2023, 2024, 2025],
    targetDraftDate: new Date('2026-09-05'),
  },

  // ADP Weights
  adpWeights: {
    sleeper: 1.2,
    espn: 1.0,
    fantasypros: 1.0,
    yahoo: 1.0,
  },

  // Algorithm Parameters
  algorithms: {
    positionRunThreshold: 3,
    valueAlertThreshold: { rounds: 1, picks: 3 },
    panicPickSigma: 3,
    stalenessThreshold: 30, // days
    cacheDuration: 10, // seconds
    scarcityMultipliers: {
      RB: 1.3,
      WR: 1.1,
      TE: 1.2,
      QB: 1.0,
    },
  },

  // Success Metrics
  metrics: {
    keeperAccuracyTarget: 0.8,
    keeperComboAccuracyTarget: 0.7,
    pickPredictionExactTarget: 0.6,
    pickPredictionPositionTarget: 0.85,
    valueAlertPrecisionTarget: 0.75,
    panicPickDetectionTarget: 0.8,
    responseTimeTarget: 10, // seconds
  },
};
