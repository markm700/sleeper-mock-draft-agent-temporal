# Sleeper Mock Draft Agent - Python

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
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and Sleeper username

# Import historical data
python -m src.scripts.import_historical

# Run analysis
python -m src.scripts.run_analysis

# Start application
python -m src.main
```

## Project Structure

```
src/
├── api/              # Sleeper API client
├── algorithms/       # Draft analysis algorithms
├── database/         # PostgreSQL connection and utilities
├── models/           # Pydantic data models
├── services/         # Business logic layer
├── scripts/          # CLI scripts for data import and analysis
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

- **No async/await**: Uses synchronous requests and psycopg2 for simplicity
- **Logging**: Python logging module with configurable levels
- **Error handling**: Comprehensive try-except blocks with proper logging
- **Type safety**: Pydantic models with full type hints
