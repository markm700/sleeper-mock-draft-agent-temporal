# Quick Start Guide

Get up and running with the Sleeper Mock Draft Agent in 5 minutes.

## Choose Your Implementation

- **Python**: Best for data science workflows, statistical analysis
- **TypeScript**: Best for Node.js ecosystem, web integration

## Fast Setup (Python)

```bash
# 1. Setup database (one-time)
psql -U postgres -c "CREATE DATABASE sleeper_draft_agent;"
psql -U postgres -d sleeper_draft_agent -f database/schema.sql

# 2. Setup Python environment
cd copilot-code/python
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your database password and Sleeper username

# 4. Run
python -m src.scripts.import_historical <your_sleeper_username>
python -m src.scripts.run_analysis
```

## Fast Setup (TypeScript)

```bash
# 1. Setup database (one-time)
psql -U postgres -c "CREATE DATABASE sleeper_draft_agent;"
psql -U postgres -d sleeper_draft_agent -f database/schema.sql

# 2. Setup TypeScript environment
cd copilot-code/typescript
npm install

# 3. Configure
cp .env.example .env
# Edit .env with your database password and Sleeper username

# 4. Run
npm run import <your_sleeper_username>
npm run analyze
```

## What This Does

1. **Import**: Fetches your league's 2021-2025 drafts, rosters, matchups
2. **Analyze**: Calculates manager tendencies, keeper values, boom/bust profiles

## Next Steps

- See [SETUP.md](./SETUP.md) for detailed installation guide
- Review `/mock-draft-agent-guides/sleeper-api-guide-v4.md` for features
- Start implementing Phase 1: Historical Data Collection

## Troubleshooting

**Can't connect to database?**
```bash
# macOS: Start PostgreSQL
brew services start postgresql@14

# Linux: Start PostgreSQL
sudo systemctl start postgresql
```

**Import errors?**
```bash
# Python: Activate virtual environment
source venv/bin/activate

# TypeScript: Reinstall dependencies
npm install
```

**Need your Sleeper username?**
- Log into [sleeper.com](https://sleeper.com)
- Your username is in your profile URL: sleeper.com/USERNAME
