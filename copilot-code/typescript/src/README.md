# Sleeper Mock Draft Agent - TypeScript Implementation

Complete TypeScript skeleton for the Sleeper Mock Draft Agent with Winston logging, error handling, and best practices.

## Project Structure

```
src/
├── config.ts                    # Configuration and Winston logger setup
├── index.ts                     # Main entry point with error handling
├── types/
│   └── index.ts                 # All TypeScript interfaces
├── api/
│   └── sleeper-client.ts        # Sleeper API client with rate limiting
├── database/
│   └── db.ts                    # PostgreSQL connection pool
├── algorithms/
│   ├── keeper-value.ts          # Keeper value calculations
│   ├── position-run-detection.ts # Position run detection
│   ├── panic-pick-detection.ts  # Panic pick detection
│   ├── boom-bust-scoring.ts     # Boom/bust scoring
│   ├── stacking-recommendations.ts # Stacking recommendations
│   └── draft-philosophy.ts      # Draft philosophy detection
├── services/
│   ├── data-import-service.ts   # Historical data import
│   ├── analysis-service.ts      # Analysis pipeline
│   └── live-draft-service.ts    # Live draft recommendations
├── scripts/
│   ├── import-historical.ts     # Import script
│   └── run-analysis.ts          # Analysis script
└── utils/
    └── player-utils.ts          # Player cache and utilities
```

## Features

### Logging
- Winston logger configured for console and file output
- Separate error log and combined log files
- Automatic exception and rejection handling
- Contextual logging throughout all modules

### Error Handling
- Try-catch blocks in all async functions
- Error logging with stack traces
- Graceful shutdown handlers
- Database transaction rollback on errors

### API Client
- Rate limiting (1000 requests/minute)
- Automatic retries with exponential backoff
- Request logging and error handling
- Sequential API calls to respect rate limits

### Database
- Connection pooling with pg
- Transaction support with context manager
- Automatic client release
- Query logging

### Algorithms
All algorithms include:
- Input validation
- Error handling
- Debug/info logging
- TODO comments for database integration

### Services
- Data import service for historical data (2021-2025)
- Analysis service for manager tendencies and predictions
- Live draft service for real-time recommendations

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Build TypeScript:
```bash
npm run build
```

## Usage

### Import Historical Data
```bash
npm run import <username>
```

### Run Analysis
```bash
npm run analyze
```

### Start Application
```bash
npm start
```

### Development Mode
```bash
npm run dev
```

## Configuration

Edit [src/config.ts](src/config.ts) to configure:
- Database connection settings
- Sleeper API parameters
- League settings (teams, rounds, scoring)
- Analysis thresholds
- ADP source weights

## Logging

Logs are written to:
- `logs/combined.log` - All logs
- `logs/error.log` - Error logs only
- `logs/exceptions.log` - Unhandled exceptions
- `logs/rejections.log` - Unhandled promise rejections

## Database Schema

See [/database/schema.sql](../../database/schema.sql) for the complete database schema.

Key tables:
- `users` - User profiles with draft philosophy
- `drafts` - Draft settings and order
- `draft_picks` - Individual picks with keeper flags
- `players` - Player database with boom/bust scores
- `manager_tendencies` - Historical patterns by user
- `keeper_predictions` - Predicted keepers for upcoming season
- `draft_position_value` - Historical success by draft slot

## API Endpoints (Future)

TODO: Add Express server with endpoints:
- `POST /api/import` - Trigger data import
- `POST /api/analyze` - Run analysis
- `POST /api/live-draft` - Get live recommendations
- `GET /api/keeper-predictions/:rosterId` - Get keeper predictions

## Next Steps

1. Implement database queries (marked with TODO comments)
2. Add Express HTTP server
3. Implement external ADP integration
4. Add caching layer (Redis)
5. Create post-draft recap functionality
6. Add webhook support for n8n integration

## Testing

TODO: Add test suite with:
- Unit tests for algorithms
- Integration tests for services
- API client mocking
- Database fixtures

## Contributing

Follow these conventions:
- Use Winston logger (not console.log)
- Add try-catch to all async functions
- Include TODO comments for incomplete features
- Use TypeScript strict mode
- Follow dash-case for file names

## License

MIT
