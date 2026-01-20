# Sleeper Mock Draft Agent

> **Advanced keeper league draft assistant with real-time adaptation, strategic intelligence, and n8n workflow automation**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue.svg)](https://www.typescriptlang.org/)
[![n8n](https://img.shields.io/badge/n8n-automation-orange.svg)](https://n8n.io/)

## 📋 Overview

A sophisticated fantasy football draft assistant that analyzes historical Sleeper league data (2021-2025) to predict keeper values, detect draft patterns, and provide real-time strategic recommendations during live drafts. Designed for 10-12 team keeper leagues with 15-round snake drafts.

### Key Features

- 🎯 **Keeper Value Analysis** - Multi-keeper optimization with opportunity cost calculations
- 📊 **Manager Tendencies** - Historical pattern detection and draft philosophy identification
- 🚨 **Real-Time Alerts** - Position run detection, panic pick flagging, value alerts
- 🎲 **Boom/Bust Scoring** - High-variance vs. consistent floor player recommendations
- 🔗 **Stacking Strategies** - QB-WR correlation analysis and anti-stacking detection
- 🔄 **n8n Workflows** - Complete automation for data import, analysis, and live draft assistance

---

## 🚀 Quick Start

### Prerequisites

- **Docker** 23.0+ and Docker Compose 2.0+ (for n8n workflows)
- **PostgreSQL** 14+ (database)
- **Python** 3.10+ OR **Node.js** 18+ (choose implementation)
- **Sleeper Account** (for API access)

### Installation (5-Minute Quick Start)

```bash
# Clone the repository
git clone https://github.com/yourusername/sleeper-mock-draft-agent.git
cd sleeper-mock-draft-agent

# Option 1: Python Implementation
cd copilot-code/python
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database credentials
python src/scripts/import_historical.py

# Option 2: TypeScript Implementation
cd copilot-code/typescript
npm install
cp .env.example .env
# Edit .env with your database credentials
npm run import:historical

# Option 3: n8n Workflows (Recommended)
cd src
./up Postgres  # Starts n8n + PostgreSQL
# Visit http://localhost:5678 to configure workflows
```

📚 **See [SETUP.md](copilot-code/SETUP.md) for complete installation guide**  
⚡ **See [QUICKSTART.md](copilot-code/QUICKSTART.md) for 5-minute setup**

---

## 📁 Repository Structure

```
sleeper-mock-draft-agent/
├── copilot-code/                    # Core implementations
│   ├── python/                      # Python 3.10+ implementation
│   │   ├── src/
│   │   │   ├── algorithms/          # Keeper value, position runs, panic picks, etc.
│   │   │   ├── api/                 # Sleeper API client
│   │   │   ├── database/            # PostgreSQL connection pool
│   │   │   ├── models/              # Pydantic data models
│   │   │   ├── services/            # Business logic (import, analysis, live draft)
│   │   │   ├── scripts/             # CLI scripts for data import & analysis
│   │   │   └── utils/               # Player lookup utilities
│   │   ├── requirements.txt         # Python dependencies
│   │   └── README.md
│   │
│   ├── typescript/                  # TypeScript/Node.js implementation
│   │   ├── src/
│   │   │   ├── algorithms/          # Same algorithms as Python (TS version)
│   │   │   ├── api/                 # Sleeper API client with rate limiting
│   │   │   ├── database/            # PostgreSQL connection pool (pg)
│   │   │   ├── services/            # Business logic services
│   │   │   ├── scripts/             # CLI scripts
│   │   │   ├── types/               # TypeScript interfaces
│   │   │   └── utils/               # Player cache utilities
│   │   ├── package.json
│   │   └── README.md
│   │
│   ├── SETUP.md                     # Complete installation guide
│   └── QUICKSTART.md                # 5-minute quick start
│
├── src/                             # n8n workflow environment
│   ├── n8n-custom/                  # Custom n8n nodes
│   │   ├── credentials/
│   │   │   └── SleeperAgent.credentials.ts  # Sleeper username credential
│   │   └── nodes/
│   │       └── SleeperAgent_Typescript/
│   │           └── SleeperAgentNode.node.ts  # Main n8n node
│   ├── docker-compose.yml           # n8n service configuration
│   ├── Postgres/                    # PostgreSQL docker setup
│   ├── Langfuse/                    # LLM observability (optional)
│   ├── Qdrant/                      # Vector DB (optional)
│   ├── up                           # Convenience script to start services
│   └── README.md
│
├── database/
│   └── schema.sql                   # Complete PostgreSQL schema (11 tables)
│
├── mock-draft-agent-guides/        # Project documentation
│   ├── sleeper-api-guide-v4.md      # Complete API & architecture guide
│   ├── sleeper-api-guide-v3.md      # Previous iterations
│   ├── sleeper-api-guide-v2.md
│   └── sleeper-api-guide-v1.md
│
├── custom-specs/                    # Development specifications
│   ├── 0-create-api-guide.md
│   ├── 1-code-improvement.md
│   └── 2-src-code-improvement.md
│
├── .github/
│   ├── copilot-instructions.md      # GitHub Copilot configuration
│   └── prompts/examples/            # Prompt engineering examples
│
├── LICENSE.md                       # MIT License
└── README.md                        # This file
```

---

## 🏗️ Architecture

### Tech Stack

| Component | Python | TypeScript | Purpose |
|-----------|--------|------------|---------|
| **API Client** | `requests` | `axios` | Sleeper API integration |
| **Database** | `psycopg2-binary` | `pg` | PostgreSQL connection pool |
| **Data Models** | `pydantic` | TypeScript interfaces | Type-safe data validation |
| **Logging** | `logging` | `winston` | Structured logging |
| **Environment** | `python-dotenv` | `dotenv` | Configuration management |
| **Automation** | n/a | n8n custom nodes | Workflow orchestration |

### Database Schema

11 tables with complete relational integrity:

- **Core:** `users`, `drafts`, `draft_picks`, `players`
- **Analysis:** `manager_tendencies`, `keeper_predictions`, `draft_sessions`
- **Real-Time:** `value_alerts`, `position_runs`, `draft_philosophy_scores`
- **Configuration:** `league_settings`

📄 **See [database/schema.sql](database/schema.sql) for complete DDL**

### Algorithms

| Algorithm | File | Purpose |
|-----------|------|---------|
| **Keeper Value** | `algorithms/keeper-value.ts` | Calculate expected value vs. ADP with opportunity cost |
| **Position Run Detection** | `algorithms/position-run-detection.ts` | Identify 3+ consecutive same-position picks |
| **Panic Pick Detection** | `algorithms/panic-pick-detection.ts` | Flag deviations from historical patterns |
| **Boom/Bust Scoring** | `algorithms/boom-bust-scoring.ts` | Variance analysis for player consistency |
| **Stacking Recommendations** | `algorithms/stacking-recommendations.ts` | QB-WR correlation analysis |
| **Draft Philosophy** | `algorithms/draft-philosophy.ts` | Zero-RB, Hero-RB, Robust-RB detection |

---

## 🔌 n8n Custom Node

### Sleeper Agent Node

**Location:** `src/n8n-custom/nodes/SleeperAgent_Typescript/`

A production-ready n8n node for seamless Sleeper API integration with:

#### Features
- ✅ **Dynamic Dropdowns** - Auto-populate leagues and drafts from your account
- ✅ **User Operations** - Get profile, leagues
- ✅ **League Operations** - Rosters, matchups, transactions
- ✅ **Draft Operations** - Draft details, picks, traded picks
- ✅ **Player Operations** - All NFL players, current season state
- ✅ **No Authentication Required** - Sleeper API is public (username only)

#### Setup

```bash
cd src/n8n-custom
npm install
npm run build

# Add to n8n custom nodes directory
# Copy dist/ contents to ~/.n8n/custom/
```

#### Usage in n8n

1. **Add Credential:** Sleeper API (username only)
2. **Add Node:** "Sleeper Agent" in workflow
3. **Select Resource:** User, League, Draft, or Players
4. **Choose Operation:** Dropdowns auto-populate with your data

📖 **See [sleeper-api-guide-v4.md](mock-draft-agent-guides/sleeper-api-guide-v4.md) for n8n workflow examples**

---

## 📊 API Reference

### Sleeper API Endpoints

All endpoints are accessed via `https://api.sleeper.app/v1`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/user/<username>` | GET | User profile |
| `/user/<user_id>/leagues/nfl/<season>` | GET | User's leagues |
| `/draft/<draft_id>` | GET | Draft metadata |
| `/draft/<draft_id>/picks` | GET | All draft picks |
| `/draft/<draft_id>/traded_picks` | GET | Traded picks |
| `/league/<league_id>/rosters` | GET | League rosters |
| `/league/<league_id>/matchups/<week>` | GET | Weekly matchups |
| `/league/<league_id>/transactions/<week>` | GET | Transactions |
| `/players/nfl` | GET | All NFL players (~5MB) |
| `/state/nfl` | GET | Current season/week |

**Rate Limit:** <1000 requests/minute (enforced in both clients)

---

## 🎯 Usage Examples

### Python: Import Historical Data

```python
from src.services.data_import_service import DataImportService
from src.database.db import Database

# Initialize
db = Database()
service = DataImportService(db)

# Import 5 years of draft data
service.import_historical_data(
    user_id="your_sleeper_user_id",
    seasons=[2021, 2022, 2023, 2024, 2025]
)
```

### TypeScript: Run Analysis

```typescript
import { AnalysisService } from './services/analysis-service';
import { DatabasePool } from './database/db';

const db = new DatabasePool();
const analysis = new AnalysisService(db);

// Calculate keeper values
const keepers = await analysis.calculateKeeperValues(
  'league_id',
  2026
);

console.log(keepers);
```

### n8n: Live Draft Workflow

```
1. HTTP Request → GET /state/nfl (get current week)
2. Sleeper Agent → Get Draft Picks
3. Function → Calculate available players
4. Sleeper Agent → Get All Players
5. Function → Run position run detection
6. Function → Calculate keeper values
7. Email/Slack → Send recommendations
```

---

## 🧪 Development

### Running Tests

```bash
# Python
cd copilot-code/python
pytest tests/

# TypeScript
cd copilot-code/typescript
npm test
```

### Code Quality

```bash
# Python: Type checking & linting
mypy src/
black src/
flake8 src/

# TypeScript: Type checking & linting
npm run type-check
npm run lint
npm run format
```

### Environment Variables

Both implementations use `.env` files:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sleeper_draft
DB_USER=postgres
DB_PASSWORD=your_password

# Sleeper API (optional - API is public)
SLEEPER_BASE_URL=https://api.sleeper.app/v1

# Logging
LOG_LEVEL=INFO
```

---

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| [SETUP.md](copilot-code/SETUP.md) | Complete installation & configuration guide |
| [QUICKSTART.md](copilot-code/QUICKSTART.md) | 5-minute quick start |
| [sleeper-api-guide-v4.md](mock-draft-agent-guides/sleeper-api-guide-v4.md) | Complete API reference & architecture |
| [schema.sql](database/schema.sql) | Database schema with indexes |
| [Python README](copilot-code/python/README.md) | Python implementation details |
| [TypeScript README](copilot-code/typescript/README.md) | TypeScript implementation details |

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Coding Standards

- **Python:** Follow PEP 8, use type hints, docstrings required
- **TypeScript:** Follow ESLint config, use strict mode, JSDoc for public APIs
- **Git:** Use conventional commits (`feat:`, `fix:`, `docs:`, etc.)

---

## 🔮 Roadmap

### Phase 1: Historical Data Collection ✅
- [x] Sleeper API client (Python & TypeScript)
- [x] Database schema design
- [x] Historical data import scripts
- [x] Manager tendency analysis

### Phase 2: Keeper Analysis ✅
- [x] Keeper value calculation
- [x] Multi-keeper optimization
- [x] Opportunity cost algorithm
- [x] Boom/bust scoring

### Phase 3: Real-Time Draft Intelligence ✅
- [x] Position run detection
- [x] Panic pick flagging
- [x] Value alerts
- [x] Draft philosophy detection

### Phase 4: n8n Integration ✅
- [x] Custom Sleeper Agent node
- [x] Dynamic league/draft dropdowns
- [x] Workflow automation
- [ ] Pre-built workflow templates

### Phase 5: Advanced Features (Planned)
- [ ] External ADP integration (ESPN, FantasyPros, Yahoo)
- [ ] Machine learning models for keeper predictions
- [ ] Draft recap reports with lessons learned
- [ ] Confidence scoring for all predictions
- [ ] Redis caching for high-frequency queries

---

## 📜 License

This project is licensed under the MIT License - see [LICENSE.md](LICENSE.md) for details.

Original n8n components © 2022 n8n  
Sleeper Mock Draft Agent extensions © 2024-2026

---

## 🙏 Acknowledgments

- **Sleeper API** - Public fantasy football API
- **n8n** - Workflow automation platform
- **PostgreSQL** - Robust relational database
- **GitHub Copilot** - AI-powered development assistant

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/sleeper-mock-draft-agent/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/sleeper-mock-draft-agent/discussions)
- **Sleeper API Docs:** [https://docs.sleeper.com/](https://docs.sleeper.com/)
- **n8n Community:** [https://community.n8n.io/](https://community.n8n.io/)

---

**Built with ❤️ for keeper league domination** 🏆
