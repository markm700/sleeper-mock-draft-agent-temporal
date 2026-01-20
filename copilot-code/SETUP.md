# Sleeper Mock Draft Agent - Setup Guide

Complete installation and setup guide for both Python and TypeScript implementations.

---

## Prerequisites

- **Python 3.10+** (for Python implementation)
- **Node.js 18+** and npm (for TypeScript implementation)
- **PostgreSQL 14+** (required for both)
- **Git** (optional, for version control)

---

## Database Setup (Required for Both Implementations)

### 1. Install PostgreSQL

**macOS:**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download from [postgresql.org](https://www.postgresql.org/download/windows/)

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE sleeper_draft_agent;
CREATE USER draft_agent WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE sleeper_draft_agent TO draft_agent;
\q
```

### 3. Run Schema

```bash
# From project root
cd /Users/markmatas/Documents/sleeper-mock-draft-agent
psql -U postgres -d sleeper_draft_agent -f database/schema.sql
```

---

## Python Implementation Setup

### 1. Navigate to Python Directory

```bash
cd copilot-code/python
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected packages:**
- `requests>=2.31.0` - HTTP client for Sleeper API
- `psycopg2-binary>=2.9.9` - PostgreSQL adapter
- `python-dotenv>=1.0.0` - Environment variable management
- `pydantic>=2.5.0` - Data validation

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

**Required configuration:**
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sleeper_draft_agent
DB_USER=draft_agent
DB_PASSWORD=your_secure_password

# Sleeper API
SLEEPER_USERNAME=your_sleeper_username

# League Config
LEAGUE_SEASONS=2021,2022,2023,2024,2025
LEAGUE_TEAMS=10
LEAGUE_ROUNDS=15

# Logging
LOG_LEVEL=INFO
```

### 5. Verify Installation

```bash
# Test basic imports and database connection
python -m src.main
```

**Expected output:**
```
2026-01-20 10:00:00 - src.config - INFO - Logging configured
2026-01-20 10:00:00 - src.database.db - INFO - Database connection pool initialized
2026-01-20 10:00:00 - src.database.db - INFO - Database connection verified
2026-01-20 10:00:00 - src.main - INFO - Sleeper Mock Draft Agent v1.0.0
2026-01-20 10:00:00 - src.main - INFO - Ready for draft analysis!
```

### 6. Import Historical Data

```bash
# Replace with your Sleeper username
python -m src.scripts.import_historical your_username
```

### 7. Run Analysis

```bash
python -m src.scripts.run_analysis
```

---

## TypeScript Implementation Setup

### 1. Navigate to TypeScript Directory

```bash
cd copilot-code/typescript
```

### 2. Install Dependencies

```bash
npm install
```

**Expected packages:**
- `axios` - HTTP client for Sleeper API
- `pg` - PostgreSQL client
- `dotenv` - Environment variables
- `winston` - Logging framework
- `typescript` - TypeScript compiler
- `ts-node` - TypeScript execution

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

**Required configuration:**
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sleeper_draft_agent
DB_USER=draft_agent
DB_PASSWORD=your_secure_password

# Sleeper API
SLEEPER_USERNAME=your_sleeper_username

# League Config
LEAGUE_SEASONS=2021,2022,2023,2024,2025
LEAGUE_TEAMS=10
LEAGUE_ROUNDS=15

# Logging
LOG_LEVEL=info
```

### 4. Build Project

```bash
npm run build
```

### 5. Verify Installation

```bash
# Test basic setup
npm start
```

**Expected output:**
```
2026-01-20 10:00:00 [sleeper-mock-draft-agent] info: Database connection pool initialized
2026-01-20 10:00:00 [sleeper-mock-draft-agent] info: SleeperClient initialized
2026-01-20 10:00:00 [sleeper-mock-draft-agent] info: Sleeper Mock Draft Agent v1.0.0
2026-01-20 10:00:00 [sleeper-mock-draft-agent] info: Ready for draft analysis!
```

### 6. Import Historical Data

```bash
# Replace with your Sleeper username
npm run import your_username
```

### 7. Run Analysis

```bash
npm run analyze
```

---

## Common Issues and Troubleshooting

### Database Connection Errors

**Problem:** `could not connect to server: Connection refused`

**Solution:**
```bash
# Check if PostgreSQL is running
# macOS:
brew services list | grep postgresql

# Ubuntu/Linux:
sudo systemctl status postgresql

# Start if not running:
brew services start postgresql@14  # macOS
sudo systemctl start postgresql    # Linux
```

**Problem:** `FATAL: role "postgres" does not exist`

**Solution:**
```bash
# Create postgres user (macOS)
createuser -s postgres
```

### Python Import Errors

**Problem:** `ModuleNotFoundError: No module named 'requests'`

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

### TypeScript Compilation Errors

**Problem:** `Cannot find module 'winston'`

**Solution:**
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Sleeper API Rate Limiting

**Problem:** `Rate limit reached, waiting`

**Solution:** This is normal. The client automatically waits. If you see this frequently:
- Reduce concurrent requests
- The implementation already respects <1000/min limit

---

## Verifying Setup

### Python Health Check

```bash
cd copilot-code/python
python -c "
from src.config import config, logger
from src.database.db import db
from src.api.sleeper_client import sleeper_client

logger.info('Testing configuration...')
logger.info(f'Database: {config.database[\"name\"]}')
logger.info(f'Sleeper URL: {config.sleeper[\"base_url\"]}')

# Test database
db.initialize()
logger.info('Database connection: OK')

logger.info('All systems operational!')
"
```

### TypeScript Health Check

```bash
cd copilot-code/typescript
npx ts-node -e "
import { config, logger } from './src/config';
import { db } from './src/database/db';

(async () => {
  logger.info('Testing configuration...');
  logger.info('Database: ' + config.database.database);
  logger.info('Sleeper URL: ' + config.sleeper.baseUrl);
  
  await db.initialize();
  logger.info('Database connection: OK');
  
  await db.close();
  logger.info('All systems operational!');
})();
"
```

---

## Next Steps

1. **Import Historical Data**
   - Run import script with your Sleeper username
   - This fetches 2021-2025 draft picks, rosters, matchups, transactions

2. **Run Analysis**
   - Generates manager tendencies
   - Calculates keeper values
   - Creates boom/bust profiles

3. **Implement Phase 1** (Week 1-4)
   - Add database query implementations (marked with TODO)
   - Complete player lookup logic
   - Test with real historical data

4. **External ADP Integration** (Phase 2)
   - Add ESPN, FantasyPros, Yahoo rankings
   - Weight according to config (Sleeper 1.2x, others 1.0x)

---

## Development Workflow

### Python Development

```bash
# Activate virtual environment
source venv/bin/activate

# Make changes to code
# ...

# Run specific module
python -m src.services.data_import_service

# Run tests (when added)
pytest tests/
```

### TypeScript Development

```bash
# Start in development mode with auto-reload
npm run dev

# Build for production
npm run build

# Run built code
npm start

# Type checking
npx tsc --noEmit
```

---

## Project Structure

```
copilot-code/
├── python/
│   ├── src/
│   │   ├── algorithms/      # Draft analysis algorithms
│   │   ├── api/             # Sleeper API client
│   │   ├── database/        # PostgreSQL connection
│   │   ├── models/          # Pydantic data models
│   │   ├── services/        # Business logic
│   │   ├── scripts/         # CLI scripts
│   │   └── utils/           # Utilities
│   ├── requirements.txt
│   └── .env
│
└── typescript/
    ├── src/
    │   ├── algorithms/      # Draft analysis algorithms
    │   ├── api/             # Sleeper API client
    │   ├── database/        # PostgreSQL connection
    │   ├── services/        # Business logic
    │   ├── scripts/         # CLI scripts
    │   ├── types/           # TypeScript types
    │   └── utils/           # Utilities
    ├── package.json
    └── .env
```

---

## Support

For issues with:
- **Sleeper API**: Check [Sleeper API docs](https://docs.sleeper.com/)
- **PostgreSQL**: Check [PostgreSQL docs](https://www.postgresql.org/docs/)
- **Project-specific issues**: Review custom-specs/ folder for implementation details
