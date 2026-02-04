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

- Python 3.12+
- Temporal
- PostgreSQL
- SQLAlchemy
- pandas / numpy / scikit-learn
- Docker

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL
- Docker (for Temporal server)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sleeper-mock-draft-agent-temporal
```

2. Install dependencies:
```bash
poetry install
```

3. Copy environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start Temporal server (Docker):
```bash
docker-compose up -d
```

5. Run database migrations:
```bash
alembic upgrade head
```

### Running the Application

Start the Temporal worker:
```bash
poetry run python -m src.worker
```

Trigger a workflow:
```bash
poetry run python -m src.cli data-collection --username <your_sleeper_username>
```

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
├── workflows/         # Temporal workflows
├── activities/        # Temporal activities (API, database, ML)
├── models/            # Database and API models
└── utils/             # Configuration and logging

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

## Roadmap

See [sleeper-api-guide-v2.md](mock-draft-agent-guides/sleeper-api-guide-v2.md) for the complete 15-phase implementation roadmap.

### Current Status: Phase 1 (Foundation)

- [x] Project structure
- [x] Temporal workflow skeleton
- [x] Database models
- [ ] Database migrations
- [ ] Development environment (Docker)

## License

MIT

## Contributing

Contributions welcome! Please read the contributing guidelines first.
