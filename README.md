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
  - Draft data collection (picks, traded picks) — independent activities can run concurrently
  - Player data collection (full NFL player database)
- **Sleeper API Integration**: Async httpx client with comprehensive endpoints
- **Database Storage**: PostgreSQL with SQLAlchemy ORM (JSONB support)
- **ADP & Draft Analysis**: Average draft position computed from historical picks
- **ML Model Training**: Per-owner LightGBM learning-to-rank models
  - Model management lifecycle (build, rebuild, status, list, delete)
  - Single-owner and league-wide (all owners) training workflows
  - Structural `DraftModel` Protocol interface decoupling management from the concrete model
- **Draft Pick Prediction**: Score candidate players from a specific owner's perspective (single and batch)
- **Mock Draft Simulation**: Full-draft simulation using the trained per-owner models
- **Testing Suite**: Pytest integration with mock clients

### Planned 🚧
- **Historical Data Collection**: Deeper multi-season backfill and profiling
- **Owner Profiling**: Clustering to improve drafter predictions and personality analysis
- **Recommendations**: Top 3 best available + top 3 best value picks
- **Database Migrations**: Alembic-managed schema (currently created at worker startup)
- **Centralized Config & Structured Logging**: Shared settings object and JSON logging

## Architecture

- **Workflows**: Durable orchestration of data collection, training, prediction, and simulation
  - Data collection: full, team owner, league, draft, and player workflows
  - ML: model management, model training, league-wide model training, model prediction, mock draft simulation
- **Activities**: External interactions (Sleeper API, database, ML)
  - Client Based: Sleeper API, PostgreSQL operations
  - ML: ADP calculation, training-data prep, model build/train, feature loading, and prediction
- **Task queues**: Data-collection activities and ML activities run on separate Temporal task queues, served by separate workers
- **Database**: PostgreSQL 16 with SQLAlchemy 2.0+ ORM (JSONB for flexible schema)
- **Orchestration**: Temporal for durable execution with automatic retries and error handling
- **Testing**: Pytest with mock clients for isolated workflow/activity testing

## Tech Stack

- **Language**: Python 3.12
- **Orchestration**: Temporal (`temporalio==1.21.1`) — durable workflows with automatic retries
- **Database**: PostgreSQL 16 (with JSONB support for flexible schemas)
- **ORM**: SQLAlchemy 2.0+ (utilizes type hints)
- **HTTP Client**: httpx (async Sleeper API integration)
- **ML**: LightGBM (learning-to-rank), scikit-learn, pandas, numpy; models persisted with joblib
- **API**: FastAPI (workflow trigger endpoints) + Sleeper API v1 (read-only, no auth required)
- **Testing**: pytest with mock clients and fixtures
- **Containerization**: Docker & Docker Compose

## Services

The docker-compose setup includes:

| Service | Port | Description |
|---------|------|-------------|
| **postgres** | 5432 | PostgreSQL 16 database |
| **temporal_server** | 7233 | Temporal server (workflow engine) |
| **temporal_ui** | 8080 | Temporal Web UI (monitoring) |
| **data_collection_worker_service** | - | Data collection worker (executes data workflows/activities) |
| **ml_worker_service** | - | ML worker (scikit-learn / LightGBM training & inference) |
| **fastapi_worker** | 8002 | FastAPI service (API endpoints) |

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.12 (for local development / running the helper scripts)
- `make` (optional — convenience wrapper around docker compose)

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
docker compose up -d     # or: make up   (make up-build to rebuild images)
```

This will start:
- **PostgreSQL** on port 5432
- **Temporal Server** on port 7233
- **Temporal UI** on port 8080 (http://localhost:8080)
- **FastAPI Worker** on port 8002
- **Data Collection Worker Service**
- **ML Worker Service**

**Note**: Database tables are created automatically by the worker at startup
> (`create_all_tables`). Alembic migrations are planned but not yet in place.

4. Make the `run_api.sh` script executable for running commands, workflows, and simulations:
```bash
chmod +x ./scripts/run_api.sh
```

4. (Optional) Alias the folder location for the executable script for easier access:
```bash
alias mockdraftagent="./scripts/run_api.sh"
# Note: The script `run_api.sh` is the main entry point for running commands, workflows, and simulations. 
# 'mockdraftagent' is the default but can be customized to your preference.
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
docker-compose logs -f data_collection_worker_service
docker-compose logs -f fastapi_worker
```

Stop all services:
```bash
docker-compose down
```

**Local Development**:

Workers resolve imports with `PYTHONPATH=src` (imports are `from activities...` / `from workflows...`, not `src.`-prefixed). To run a worker outside Docker:
```bash
pip install -r src/services/requirements.data_collection_worker_service.txt
PYTHONPATH=src python -m workers.workflow_worker   # data-collection worker
PYTHONPATH=src python -m workers.ml_worker         # ML worker
```

**Driving the pipeline** — `scripts/run_api.sh` is a CLI wrapper over the FastAPI endpoints:
```bash
scripts/run_api.sh health                       # health check
scripts/run_api.sh collect-all <user> <league>  # full data collection
scripts/run_api.sh train-league <league_id>     # train models for all owners
scripts/run_api.sh simulate-draft <league_id>   # run a mock draft (alias: sim)
scripts/run_api.sh pipeline <user> <league>     # collect → train → simulate
scripts/run_api.sh help                          # full command list
```

**Access Points**:
- **Temporal UI**: http://localhost:8080 (monitor workflows)
- **FastAPI**: http://localhost:8002 (API endpoints; interactive docs at `/docs`)
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
│   ├── api-integration/
│   ├── docstring-formatter/
│   └── _template/
├── agents/            # Agent definitions (activity_tester, notion_mcp)
├── prompts/           # Reusable prompt templates (spec/test-writing)
└── copilot-instructions.md  # Main AI assistant instructions

src/
├── api.py             # FastAPI app: endpoints that start Temporal workflows
├── activities/        # Temporal activities (API interactions, DB, ML)
│   ├── clients/      # Sleeper API, PostgreSQL, and ML model manager clients
│   ├── draft/        # Draft-related activities
│   ├── league/       # League data activities
│   ├── players/      # NFL player data activities
│   ├── team_owner/   # Team owner activities
│   └── ml/           # ML activities
│       ├── training/     # ADP, training-data prep, model training
│       ├── models/       # Model build/manage, TeamOwnerDraftModel, DraftModel Protocol
│       └── predictions/  # Feature loading, pick prediction, draft-sim context
├── workflows/         # Temporal workflows (orchestration logic)
│   ├── full_data_collection.py, team_owner_data_collection.py
│   ├── league_data_collection.py, draft_data_collection.py, player_data_collection.py
│   ├── model_management.py, model_training.py, league_model_training.py
│   └── model_prediction.py, mock_draft_simulation.py
├── schema/            # SQLAlchemy database models and schema docs (SCHEMA.md, ERD.md)
├── testing/           # Test suite with mocks and fixtures
│   ├── data_collection/  # Workflow and activity tests
│   └── mocks/        # Mock clients for testing
├── workers/           # Worker entry points
│   ├── workflow_worker.py    # data-collection task queue
│   └── ml_worker.py          # ML task queue
├── services/          # Service-specific requirements (data collection, ml, fastapi)
├── Dockerfile.fastapi_worker            # FastAPI worker container
├── Dockerfile.data_collection_worker_service   # Data collection worker container
└── Dockerfile.ml_worker_service                 # ML worker container (scikit-learn / LightGBM)

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
black src/

# Lint code
ruff check src/

# Type check
mypy src/
```

> Conventions: black formatting, ruff linting, mypy-compliant type hints, 100-char lines.

### Testing

Run tests using the testing suite in `src/testing/`:

```bash
# Run all tests (PYTHONPATH=src so imports resolve as in the workers)
PYTHONPATH=src pytest src/testing/

# Run specific test category
PYTHONPATH=src pytest src/testing/data_collection/activities/
PYTHONPATH=src pytest src/testing/data_collection/workflows/

# Run with verbose output
PYTHONPATH=src pytest src/testing/ -v
```

The test suite includes:
- Activity tests with mock Sleeper API and PostgreSQL clients
- Workflow tests with mock activities
- Integration tests for full workflows

## Implementation Guide

This project follows the implementation roadmap in `mock-draft-agent-guides/`:

- **[sleeper-api-guide-v2.md](mock-draft-agent-guides/sleeper-api-guide-v2.md)**: Complete 15-phase implementation guide with Sleeper API endpoints, data structures, and workflow orchestration patterns
- **[sleeper-api-guide-v1.md](mock-draft-agent-guides/sleeper-api-guide-v1.md)**: Original implementation reference

### Current Status: Data Collection + ML Pipeline ✅

**Phase 1 (Foundation) - Complete:**
- [x] Project structure with AI assistant instructions
- [x] Development environment (Docker Compose)
- [x] PostgreSQL, Temporal Server, Temporal UI services
- [x] Database models (SQLAlchemy ORM with JSONB support)
- [x] PostgreSQL client with upsert operations

**Phase 2 (Data Collection) - Complete:**
- [x] Sleeper API client with httpx
- [x] Data collection workflows (full, team owner, league, draft, player)
- [x] Data collection activities (owners, league, drafts/picks, traded picks, NFL players)
- [x] Concurrent execution of independent activities (e.g. draft picks + traded picks)
- [x] Comprehensive test suite with mocks
- [x] Worker registration and deployment (separate data-collection and ML task queues)

**Phase 3 (ML Pipeline) - Complete:**
- [x] ADP calculation from historical picks
- [x] Training-data preparation and per-owner LightGBM training
- [x] Model management lifecycle (build, rebuild, status, list, delete)
- [x] League-wide model training
- [x] Draft pick prediction (single and batch) and mock draft simulation
- [x] `DraftModel` Protocol interface for model backends
- [x] Parallelization of independent data-collection workflow/activity fan-outs

**Next Steps:**
- [ ] Centralized config object and structured (JSON) logging
- [ ] Owner archetype profiling and value/recommendation surfaces
- [ ] Database migrations (Alembic) — tables currently created at worker startup

## Implemented Components

### Workflows

| Workflow | File | Description |
|----------|------|-------------|
| **Full Data Collection** | [full_data_collection.py](src/workflows/full_data_collection.py) | Orchestrates all data collection workflows |
| **Team Owner Data Collection** | [team_owner_data_collection.py](src/workflows/team_owner_data_collection.py) | Collects user data, leagues, and rosters |
| **League Data Collection** | [league_data_collection.py](src/workflows/league_data_collection.py) | Fetches league metadata and roster information |
| **Draft Data Collection** | [draft_data_collection.py](src/workflows/draft_data_collection.py) | Gathers draft picks (concurrently) and traded picks |
| **Player Data Collection** | [player_data_collection.py](src/workflows/player_data_collection.py) | Collects NFL player data from Sleeper API |
| **Model Management** | [model_management.py](src/workflows/model_management.py) | Build, rebuild, status, list, or delete a model |
| **Model Training** | [model_training.py](src/workflows/model_training.py) | Train a single team owner's draft model |
| **League Model Training** | [league_model_training.py](src/workflows/league_model_training.py) | Train models for all owners in a league |
| **Model Prediction** | [model_prediction.py](src/workflows/model_prediction.py) | Score candidate players for an owner |
| **Mock Draft Simulation** | [mock_draft_simulation.py](src/workflows/mock_draft_simulation.py) | Simulate a full draft using trained models |

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

#### ML Activities

| Activity | File | Description |
|----------|------|-------------|
| **calculate_adp_from_picks** | [ml/calculate_adp.py](src/activities/ml/calculate_adp.py) | Compute average draft position from historical picks |
| **get_league_team_owners** | [ml/get_league_team_owners.py](src/activities/ml/get_league_team_owners.py) | List owner user_ids for a league |
| **prepare_owner_training_data** | [ml/training/prepare_training_data.py](src/activities/ml/training/prepare_training_data.py) | Encode historical picks into ranking training samples |
| **train_team_owner_model** | [ml/training/train_model.py](src/activities/ml/training/train_model.py) | Train a LightGBM learning-to-rank model for an owner |
| **build_owner_model / get_model_status / list_models / delete_model** | [ml/models/manage_model.py](src/activities/ml/models/manage_model.py) | Model lifecycle management |
| **get_player_features_from_db** | [ml/predictions/predict_player_pick.py](src/activities/ml/predictions/predict_player_pick.py) | Load player feature vectors from PostgreSQL |
| **predict_owner_draft_pick / batch_predict_owner** | [ml/predictions/predict_player_pick.py](src/activities/ml/predictions/predict_player_pick.py) | Score candidate players for an owner |
| **get_draft_simulation_context** | [ml/predictions/get_draft_simulation_context.py](src/activities/ml/predictions/get_draft_simulation_context.py) | Assemble draft state for simulation |

The team owner model ([ml/models/team_owner_model.py](src/activities/ml/models/team_owner_model.py)) and any future backend conform to the structural `DraftModel` Protocol in [ml/models/model_interface.py](src/activities/ml/models/model_interface.py), which decouples the model-management activities from a concrete implementation.

### API Endpoints

The FastAPI service ([src/api.py](src/api.py)) exposes endpoints that start Temporal workflows:

| Method | Path | Workflow |
|--------|------|----------|
| POST | `/full-data-collection/run` | full-data-collection |
| POST | `/team-owner-data-collection/run` | team-owner-data-collection |
| POST | `/player-data-collection/run` | player-data-collection |
| POST | `/model-management/run` | model-management |
| POST | `/model-training/run` | model-training |
| POST | `/league-model-training/run` | league-model-training |
| POST | `/model-prediction/run` | model-prediction |
| POST | `/mock-draft-simulation/run` | mock-draft-simulation |
| GET/POST/DELETE | `/models`, `/models/{name}/status`, `/models/{name}/build`, `/models/{name}/rebuild`, `/models/{name}` | model-management (convenience routes) |
| GET | `/`, `/healthz`, `/healthz/data-collection-worker-service/status` | health checks |

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
