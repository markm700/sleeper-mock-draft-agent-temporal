# Sleeper Mock Draft Agent (TypeScript)

Keeper league mock draft agent with real-time adaptation and advanced analytics.

## Features

- **Advanced Keeper Strategy**: Position weighting, opportunity cost calculation, multi-keeper optimization
- **Real-Time Draft Adaptation**: Position run detection, panic pick flagging, value alerts
- **Strategic Intelligence**: Boom/bust tracking, stacking strategies, draft philosophy detection
- **Advanced Analytics**: Draft position analysis, late-round targets, confidence scoring

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Set up database:
```bash
# Create PostgreSQL database
createdb sleeper_draft_agent

# Run schema
psql sleeper_draft_agent < database/schema.sql
```

## Usage

### Import Historical Data
```bash
npm run import
```

### Run Analysis
```bash
npm run analyze
```

### Development
```bash
npm run dev
```

### Build
```bash
npm run build
npm start
```

## Project Structure

```
src/
├── api/              # Sleeper API client
├── algorithms/       # Core algorithms (keeper value, position runs, etc)
├── services/         # Business logic services
├── database/         # Database utilities
├── types/            # TypeScript type definitions
├── scripts/          # CLI scripts
└── index.ts          # Main entry point
```

## Target

- **League**: 10 teams, 15 rounds, PPR, snake draft
- **Data**: 2021-2025 seasons
- **Draft Date**: September 5, 2026
