# Sleeper Mock Draft Agent (Temporal)

Mock draft agent for Sleeper fantasy football leagues using Python and Temporal workflows.

## Overview

This application analyzes historical league data from the Sleeper API to build a machine learning model that predicts draft outcomes. It uses Temporal for orchestrating data collection, analysis, and Monte Carlo draft simulations.

## Features

### Implemented ✅
- **Data Collection Workflows**: Automated orchestration of league data gathering
  - Full data collection workflow (chains team owner → league → draft data)
  - Team owner data collection (user info, leagues, rosters)
  - League data collection (metadata, settings, rosters)
  - Draft data collection (picks, traded picks)
- **Sleeper API Integration**: Async httpx client with comprehensive endpoints
- **Database Storage**: PostgreSQL with SQLAlchemy ORM (JSONB support)
- **Testing Suite**: Pytest integration with mock clients

### Planned 🚧
- **Historical Data Collection**: 5 years of league history analysis
- **Owner Profiling**: K-means clustering to identify drafter archetypes
- **Draft Analysis**: ADP calculation, positional runs, reach/value metrics
- **Mock Draft Simulation**: Monte Carlo simulation (1000+ iterations)
- **Recommendations**: Top 3 best available + top 3 best value picks

## Architecture

- **Workflows**: Durable orchestration of data collection, analysis, and simulation
  - Implemented: Full data collection, team owner, league, and draft workflows
  - Planned: Analysis workflows, mock draft simulation
- **Activities**: External interactions (Sleeper API, database, ML)
  - Implemented: Sleeper API clients, PostgreSQL operations
  - Planned: ML model training and prediction
- **Database**: PostgreSQL 16 with SQLAlchemy 2.0+ ORM (JSONB for flexible schema)
- **Orchestration**: Temporal for durable execution with automatic retries and error handling
- **Testing**: Pytest with mock clients for isolated workflow/activity testing

## Tech Stack

- **Language**: Python 3.12+
- **Orchestration**: Temporal v1.23.0 (durable workflows with automatic retries)
- **Database**: PostgreSQL 16 (with JSONB support for flexible schemas)
- **ORM**: SQLAlchemy 2.0+ (async support, type hints)
- **HTTP Client**: httpx (async Sleeper API integration)
- **ML/Analysis**: pandas, numpy, scikit-learn (planned)
- **API**: Sleeper API v1 (read-only, no authentication required)
- **Testing**: pytest with mock clients and fixtures
- **Containerization**: Docker & Docker Compose

## Services

The docker-compose setup includes:

| Service | Port | Description |
|---------|------|-------------|
| **postgres** | 5432 | PostgreSQL 16 database |
| **temporal_server** | 7233 | Temporal server (workflow engine) |
| **temporal_ui** | 8080 | Temporal Web UI (monitoring) |
| **temporal_worker_service** | - | Temporal worker (executes workflows/activities) |
| **fastapi_worker** | 8002 | FastAPI service (API endpoints) |

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)
- Poetry (for dependency management)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sleeper-mock-draft-agent-temporal
```

2. Copy environment file and configure:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Start all services (PostgreSQL, Temporal, Temporal UI, Workers):
```bash
docker-compose up -d
```

This will start:
- **PostgreSQL** on port 5432
- **Temporal Server** on port 7233
- **Temporal UI** on port 8080 (http://localhost:8080)
- **FastAPI Worker** on port 8002
- **Temporal Worker Service**

4. (Optional) Install dependencies for local development:
```bash
poetry install
```

5. (Optional) Run database migrations:
```bash
poetry run alembic upgrade head
```

### Running the Application

**Using Docker (Recommended)**:

All services start automatically with docker-compose:
```bash
docker-compose up -d
```

View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f temporal_worker_service
docker-compose logs -f fastapi_worker
```

Stop all services:
```bash
docker-compose down
```

**Local Development**:

Start Temporal worker:
```bash
poetry run python -m src.workers.workflow_worker
```

**Access Points**:
- **Temporal UI**: http://localhost:8080 (monitor workflows)
- **FastAPI**: http://localhost:8002 (API endpoints)
- **PostgreSQL**: localhost:5432 (database)

## Project Structure

```
.github/
├── instructions/      # Path-specific coding conventions
│   ├── workflows.instructions.md
│   ├── activities.instructions.md
│   ├── models.instructions.md
│   └── utils.instructions.md
├── skills/            # Reusable development task guides
│   ├── temporal-workflow/
│   ├── temporal-activity/
│   ├── database-model/
│   └── api-integration/
└── copilot-instructions.md  # Main AI assistant instructions

src/
├── activities/        # Temporal activities (API interactions, DB operations)
│   ├── clients/      # Sleeper API and PostgreSQL clients
│   ├── draft/        # Draft-related activities
│   ├── league/       # League data activities
│   └── team_owner/   # Team owner activities
├── workflows/         # Temporal workflows (orchestration logic)
│   ├── full_data_collection.py
│   ├── league_data_collection.py
│   ├── draft_data_collection.py
│   └── team_owner_data_collection.py
├── schema/            # SQLAlchemy database models and schema docs
├── testing/           # Test suite with mocks and fixtures
│   ├── data_collection/  # Workflow and activity tests
│   └── mocks/        # Mock clients for testing
├── workers/           # Worker entry points
│   └── workflow_worker.py
├── services/          # Service-specific requirements
├── ai-generated/      # AI-generated reference implementations
├── Dockerfile.fastapi_worker            # FastAPI worker container
└── Dockerfile.temporal_worker_service   # Temporal worker container

docker/                # Docker configuration
migrations/            # Database migrations
```

## Development

### AI-Assisted Development

This project includes comprehensive instructions for AI assistants (GitHub Copilot, Claude, etc.):

- **[Main Instructions](.github/copilot-instructions.md)**: Project overview and architectural constraints
- **[Path-Specific Instructions](.github/instructions/)**: Auto-apply when editing files in specific paths
- **[Agent Skills](.github/skills/)**: Reusable guides for common tasks (creating workflows, activities, models, API integrations)

These files help AI assistants generate code that follows project patterns and conventions.

### Code Quality

```bash
# Format code
poetry run black src/

# Lint code
poetry run ruff check src/

# Type check
poetry run mypy src/
```

### Testing

Run tests using the testing suite in `src/testing/`:

```bash
# Run all tests
poetry run pytest src/testing/

# Run specific test category
poetry run pytest src/testing/data_collection/activities/
poetry run pytest src/testing/data_collection/workflows/

# Run with coverage
poetry run pytest src/testing/ --cov=src

# Run with verbose output
poetry run pytest src/testing/ -v
```

The test suite includes:
- Activity tests with mock Sleeper API and PostgreSQL clients
- Workflow tests with mock activities
- Integration tests for full workflows

## Implementation Guide

This project follows the implementation roadmap in `mock-draft-agent-guides/`:

- **[sleeper-api-guide-v2.md](mock-draft-agent-guides/sleeper-api-guide-v2.md)**: Complete 15-phase implementation guide with Sleeper API endpoints, data structures, and workflow orchestration patterns
- **[sleeper-api-guide-v1.md](mock-draft-agent-guides/sleeper-api-guide-v1.md)**: Original implementation reference

### Current Status: Phase 2 (Data Collection) ✅

**Phase 1 (Foundation) - Complete:**
- [x] Project structure with AI assistant instructions
- [x] Development environment (Docker Compose)
- [x] PostgreSQL, Temporal Server, Temporal UI services
- [x] Database models (SQLAlchemy ORM with JSONB support)
- [x] PostgreSQL client with upsert operations

**Phase 2 (Data Collection) - Complete:**
- [x] Sleeper API client with httpx
- [x] Data collection workflows:
  - [x] Full data collection (orchestrates all workflows)
  - [x] Team owner data collection
  - [x] League data collection
  - [x] Draft data collection
  - [x] Player data collection
- [x] Data collection activities:
  - [x] Team owner data (users, leagues, rosters)
  - [x] League metadata and rosters
  - [x] Draft picks and traded picks
  - [x] NFL player data (all players)
- [x] Comprehensive test suite with mocks
- [x] Worker registration and deployment

**Next Steps:**
- [ ] Database migrations (Alembic)
- [ ] Historical data collection (5 years)
- [ ] Data analysis workflows
- [ ] ML model training activities

## Implemented Components

### Workflows

| Workflow | File | Description |
|----------|------|-------------|
| **Full Data Collection** | [full_data_collection.py](src/workflows/full_data_collection.py) | Orchestrates all data collection workflows |
| **Team Owner Data Collection** | [team_owner_data_collection.py](src/workflows/team_owner_data_collection.py) | Collects user data, leagues, and rosters |
| **League Data Collection** | [league_data_collection.py](src/workflows/league_data_collection.py) | Fetches league metadata and roster information |
| **Draft Data Collection** | [draft_data_collection.py](src/workflows/draft_data_collection.py) | Gathers draft picks and traded picks |
| **Player Data Collection** | [player_data_collection.py](src/workflows/player_data_collection.py) | Collects NFL player data from Sleeper API |

### Activities

| Activity | File | Description |
|----------|------|-------------|
| **get_team_owner_data** | [team_owner/get_data.py](src/activities/team_owner/get_data.py) | Fetch user info and leagues from Sleeper |
| **get_team_owner_rosters** | [team_owner/get_roster.py](src/activities/team_owner/get_roster.py) | Get team rosters for a user |
| **get_league_data** | [league/get_data.py](src/activities/league/get_data.py) | Fetch league metadata, users, and rosters |
| **get_league_drafts** | [draft/get_drafts.py](src/activities/draft/get_drafts.py) | Get all drafts for a league |
| **get_specific_draft_picks** | [draft/get_draft_picks.py](src/activities/draft/get_draft_picks.py) | Fetch picks for a specific draft |
| **get_traded_draft_picks** | [draft/get_traded_draft_picks.py](src/activities/draft/get_traded_draft_picks.py) | Get traded draft picks for a league |
| **get_all_player_data** | [players/get_all_players.py](src/activities/players/get_all_players.py) | Fetch all NFL player data from Sleeper API |

### Database Models

Located in [src/schema/database_models.py](src/schema/database_models.py):
- **User**: Sleeper user accounts
- **TeamOwner**: Draft participant profiles
- **League**: League configuration and settings
- **Roster**: Team rosters with players
- **Draft**: Draft metadata
- **DraftPick**: Individual draft picks
- **TradedDraftPick**: Traded future picks
- **Player**: NFL player metadata and details

See [src/schema/SCHEMA.md](src/schema/SCHEMA.md) for full schema documentation.

## License

MIT

## Contributing

Contributions welcome! Please read the contributing guidelines first.
