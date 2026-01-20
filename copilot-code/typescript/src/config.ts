import winston from 'winston';
import dotenv from 'dotenv';

dotenv.config();

/**
 * Application configuration with Winston logger setup
 */
export const config = {
  // Database
  database: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'sleeper_mock_draft',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres',
    max: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
  },

  // Sleeper API
  sleeper: {
    baseUrl: 'https://api.sleeper.app/v1',
    rateLimit: 1000, // requests per minute
    retryAttempts: 3,
    retryDelay: 1000, // ms
  },

  // League settings
  league: {
    teams: 10,
    rounds: 15,
    scoringType: 'ppr',
    draftType: 'snake',
    seasons: [2021, 2022, 2023, 2024, 2025],
    playoffWeeks: 15, // Regular season ends week 14
    tradeDeadline: 11,
  },

  // Analysis thresholds
  analysis: {
    positionRunThreshold: 3, // consecutive picks to trigger run detection
    valueAlertThreshold: 1.3, // rounds late from ADP
    panicPickSigma: 3, // standard deviations for panic detection
    confidenceMinimum: 0.4,
    cacheTimeout: 10000, // 10 seconds for recommendation caching
  },

  // External ADP weights
  adp: {
    sleeper: 1.2,
    espn: 1.0,
    fantasyPros: 1.0,
    yahoo: 1.0,
  },

  // Application
  app: {
    port: parseInt(process.env.PORT || '3000'),
    env: process.env.NODE_ENV || 'development',
  },
};

/**
 * Winston logger instance with console and file transports
 */
export const logger = winston.createLogger({
  level: config.app.env === 'production' ? 'info' : 'debug',
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.errors({ stack: true }),
    winston.format.splat(),
    winston.format.json()
  ),
  defaultMeta: { service: 'sleeper-mock-draft-agent' },
  transports: [
    // Console transport with colorized output
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.printf(
          ({ level, message, timestamp, service, ...metadata }: any) => {
            let msg = `${timestamp} [${service}] ${level}: ${message}`;
            if (Object.keys(metadata).length > 0) {
              msg += ` ${JSON.stringify(metadata)}`;
            }
            return msg;
          }
        )
      ),
    }),
    // File transport for errors
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error',
    }),
    // File transport for all logs
    new winston.transports.File({
      filename: 'logs/combined.log',
    }),
  ],
});

/**
 * Log unhandled rejections and exceptions
 */
logger.exceptions.handle(
  new winston.transports.File({ filename: 'logs/exceptions.log' })
);

logger.rejections.handle(
  new winston.transports.File({ filename: 'logs/rejections.log' })
);

export default { config, logger };
