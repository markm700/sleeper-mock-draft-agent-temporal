# Sleeper Mock Draft Agent (Temporal)

Mock draft agent for Sleeper fantasy football leagues using Python and Temporal workflows.

## Overview

This application analyzes historical league data from the Sleeper API to build a machine learning model that predicts draft outcomes. It uses Temporal for orchestrating data collection, analysis, and Monte Carlo draft simulations.

## Features

- **Data Collection**: Automated gathering of 5 years of league history
- **Owner Profiling**: K-means clustering to identify drafter archetypes
- **Draft Analysis**: ADP calculation, positional runs, reach/value metrics
- **Mock Draft Simulation**: Monte Carlo simulation (1000+ iterations)
- **Recommendations**: Top 3 best available + top 3 best value picks

## Architecture

- **Workflows**: Data collection, analysis, mock draft simulation
- **Activities**: API calls, database operations, ML models
- **Database**: PostgreSQL with SQLAlchemy
- **Orchestration**: Temporal for durable execution

## Tech Stack

- **Language**: Python 3.12+
- **Orchestration**: Temporal v1.23.0 (durable workflows)
- **Database**: PostgreSQL 16 (with JSONB support)
- **ORM**: SQLAlchemy 2.0+
- **ML/Analysis**: pandas, numpy, scikit-learn
- **API**: Sleeper API (read-only, no auth)
- **Containerization**: Docker & Docker Compose

## Services

The docker-compose setup includes:

| Service | Port | Description |
|---------|------|-------------|
| **postgres** | 5432 | PostgreSQL 16 database |
| **temporal** | 7233 | Temporal server (workflow engine) |
| **temporal-ui** | 8080 | Temporal Web UI (monitoring) |
| **temporal_worker** | - | Temporal worker (executes workflows/activities) |
| **fastapi_worker_pipeline** | 8001 | FastAPI service (API endpoints) |

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
- **FastAPI Worker** on port 8001
- **Temporal Worker**

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
docker-compose logs -f temporal_worker
```

Stop all services:
```bash
docker-compose down
```

**Local Development**:

Start Temporal worker:
```bash
poetry run python -m src.workers.temporal_worker
```

**Access Points**:
- **Temporal UI**: http://localhost:8080 (monitor workflows)
- **FastAPI**: http://localhost:8001 (API endpoints)
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
├── ai-generated/      # Generated implementation code
├── activities/        # Custom activity implementations
├── workflows/         # Custom workflow implementations
├── workers/           # Worker entry points
├── services/          # Service-specific requirements
├── Dockerfile.fastapi # FastAPI worker container
└── Dockerfile.temporal_worker # Temporal worker container

tests/
├── unit/              # Unit tests
├── integration/       # Integration tests
└── fixtures/          # Test fixtures

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

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src
```

## Implementation Guide

This project follows the implementation roadmap in `mock-draft-agent-guides/`:

- **[sleeper-api-guide-v2.md](mock-draft-agent-guides/sleeper-api-guide-v2.md)**: Complete 15-phase implementation guide with Sleeper API endpoints, data structures, and workflow orchestration patterns
- **[sleeper-api-guide-v1.md](mock-draft-agent-guides/sleeper-api-guide-v1.md)**: Original implementation reference

### Current Status: Phase 1 (Foundation) ✅

- [x] Project structure with AI assistant instructions
- [x] Temporal workflow skeleton
- [x] Database models (SQLAlchemy ORM)
- [x] Development environment (Docker Compose)
- [x] PostgreSQL, Temporal Server, Temporal UI services
- [ ] Database migrations (Alembic)
- [ ] Implement data collection workflow
- [ ] Implement API client activities

## License

MIT

## Contributing

Contributions welcome! Please read the contributing guidelines first.
