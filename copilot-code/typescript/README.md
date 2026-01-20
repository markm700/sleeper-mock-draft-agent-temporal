# Sleeper Mock Draft Agent - TypeScript

Fantasy football draft agent using historical league data from Sleeper API.

## Features

- **Historical Data Import**: Collects 2021-2025 draft picks, rosters, matchups, and transactions
- **Manager Tendency Analysis**: Learns each owner's draft patterns and preferences
- **Keeper Value Calculator**: Determines optimal keeper selections with opportunity cost
- **Live Draft Recommendations**: Real-time BPA, positional need, and value picks
- **Advanced Analytics**: Position run detection, panic pick alerts, boom/bust profiles

## Quick Start

```bash
# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and Sleeper username

# Build project
npm run build

# Import historical data
npm run import <username>

# Run analysis
npm run analyze

# Start application
npm start
```

## Project Structure

```
src/
├── api/              # Sleeper API client
├── algorithms/       # Draft analysis algorithms
├── database/         # PostgreSQL connection
├── services/         # Business logic layer
├── scripts/          # CLI scripts for data import and analysis
├── types/            # TypeScript type definitions
└── utils/            # Shared utility functions
```

## Database Setup

Run the schema from `/database/schema.sql`:

```bash
psql -U postgres -d sleeper_draft_agent -f ../database/schema.sql
```

## Configuration

See `.env.example` for all available configuration options.

## Architecture

- **Winston logging**: Structured logging with colors and levels
- **Error handling**: Comprehensive try-catch blocks with proper error types
- **Type safety**: Full TypeScript typing throughout
- **Connection pooling**: PostgreSQL connection pool management
