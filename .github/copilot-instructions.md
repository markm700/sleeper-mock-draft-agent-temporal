# Copilot Instructions for Sleeper Mock Draft Agent

## Overview

This repository implements a Fantasy Football Mock Draft Prediction Agent for Sleeper, using **Temporal workflows** for durable orchestration, **PostgreSQL** for data storage, and **scikit-learn** for ML analysis.

**Tech Stack**: Python 3.12+ | Temporal v1.5.0+ | PostgreSQL + SQLAlchemy | scikit-learn | Sleeper API

**Architecture**: 
- Temporal workflows orchestrate long-running draft simulations and data collection
- Activities handle external interactions (API calls, database ops, ML processing)
- PostgreSQL stores historical draft data with JSONB for semi-structured content

## Path-Specific Instructions

Detailed coding conventions for specific parts of the codebase are in `.github/instructions/`:

- **Workflows** (`src/workflows/**`): [workflows.instructions.md](.github/instructions/workflows.instructions.md)
- **Activities** (`src/activities/**`): [activities.instructions.md](.github/instructions/activities.instructions.md)
- **Models** (`src/models/**`): [models.instructions.md](.github/instructions/models.instructions.md)
- **Utils** (`src/utils/**`): [utils.instructions.md](.github/instructions/utils.instructions.md)

## Agent Skills

Common development tasks have detailed guides in `.github/skills/`:

- **temporal-workflow**: Create new Temporal workflows
- **temporal-activity**: Create new activities (API, database, ML)
- **database-model**: Add SQLAlchemy models and migrations
- **api-integration**: Integrate with external APIs




## Critical Cross-Cutting Rules

### Temporal Patterns
- ✅ Workflows use `@workflow.defn`, activities use `@activity.defn`
- ❌ Workflows MUST be deterministic (no API calls, DB queries, `datetime.now()`)
- ✅ All external interactions via `workflow.execute_activity()` with timeouts and retry policies
- ✅ Use `workflow.logger` in workflows, `activity.logger` in activities
- ✅ Wrap non-deterministic imports in `workflow.unsafe.imports_passed_through()`

### Type System & Code Quality
- ✅ All functions/parameters have explicit type hints (mypy compliant)
- ✅ Use `@dataclass` for workflow inputs/outputs and API models
- ✅ All code is `async def` with proper `await`
- ✅ Line length 100 chars, black formatting, ruff linting
- ✅ Use `Dict[str, Any]` for JSON from APIs, minimize `Any` elsewhere

### Database & Structure
- ✅ SQLAlchemy models inherit from `declarative_base()`, use JSONB for semi-structured data
- ✅ External IDs are VARCHAR(50), internal IDs are SERIAL
- ✅ All packages have `__init__.py` with `__all__` exports
- ✅ Use absolute imports (`from src.module import name`)
- ❌ No circular dependencies (workflows → activities, never reverse)

### Configuration & APIs
- ✅ Config from environment vars via `get_config()` singleton
- ✅ API calls use singleton `requests.Session()` with `timeout=30`
- ✅ Wrap sync requests with `await asyncio.to_thread()`
- ❌ No hardcoded URLs, credentials, or secrets in code