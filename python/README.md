# Sleeper Mock Draft Agent (Python)

Keeper league mock draft agent with real-time adaptation and advanced analytics.

## Features

- **Advanced Keeper Strategy**: Position weighting, opportunity cost calculation, multi-keeper optimization
- **Real-Time Draft Adaptation**: Position run detection, panic pick flagging, value alerts
- **Strategic Intelligence**: Boom/bust tracking, stacking strategies, draft philosophy detection
- **Advanced Analytics**: Draft position analysis, late-round targets, confidence scoring

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Set up database:
```bash
# Create PostgreSQL database
createdb sleeper_draft_agent

# Run schema
psql sleeper_draft_agent < ../database/schema.sql
```

## Usage

### Import Historical Data
```bash
python -m src.scripts.import_historical
```

### Run Analysis
```bash
python -m src.scripts.run_analysis
```

### Run Main Application
```bash
python -m src.main
```

## Project Structure

```
src/
├── api/              # Sleeper API client
├── algorithms/       # Core algorithms (keeper value, position runs, etc)
├── services/         # Business logic services
├── database/         # Database utilities
├── models/           # Pydantic data models
├── scripts/          # CLI scripts
└── main.py           # Main entry point
```

## Target

- **League**: 10 teams, 15 rounds, PPR, snake draft
- **Data**: 2021-2025 seasons
- **Draft Date**: September 5, 2026
