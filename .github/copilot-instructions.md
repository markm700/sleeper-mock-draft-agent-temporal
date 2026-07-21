# Copilot Instructions for Sleeper Mock Draft Agent

## Overview

This repository implements a Fantasy Football Mock Draft Prediction Agent for Sleeper, using **Temporal workflows** for durable orchestration, **httpx/FastAPI** for async API interactions, and **LightGBM** for per-owner mock-draft prediction models.

**Tech Stack**: Python 3.12 | Temporal (`temporalio==1.21.1`) | httpx | Sleeper API | FastAPI | PostgreSQL / SQLAlchemy 2.0 | LightGBM

**Architecture**: 
- Temporal workflows orchestrate data collection, model training, prediction, and mock draft simulation
- Activities handle external interactions (Sleeper API, PostgreSQL, ML training/inference)
- Data-collection activities and ML activities run on **separate task queues**, served by two workers (`workflow_worker`, `ml_worker`)
- FastAPI service (`src/api.py`) triggers workflows via the Temporal client
- Docker Compose orchestrates services (Temporal server, workers, FastAPI, PostgreSQL)

## Path-Specific Instructions

Detailed coding conventions for specific parts of the codebase are in `.github/instructions/`:

- **Workflows** (`src/workflows/**`): [workflows.instructions.md](.github/instructions/workflows.instructions.md)
- **Activities** (`src/activities/**`): [activities.instructions.md](.github/instructions/activities.instructions.md)
- **Tests** (`src/testing/**`): Use relative imports from activities/workflows under test

## Agent Skills

Common development tasks have detailed guides in `.github/skills/`:

- **temporal-workflow**: Create new Temporal workflows
- **temporal-activity**: Create new Temporal activities for Sleeper API
- **api-integration**: Integrate with external APIs
- **database-model**: Add/modify mutable SQLAlchemy models in `src/schema/`
- **docstring-formatter**: Apply the project's docstring conventions




## Critical Cross-Cutting Rules

### Temporal Patterns
- ✅ Workflows use `@workflow.defn`, activities use `@activity.defn`
- ❌ Workflows MUST be deterministic (no API calls, DB queries, `datetime.now()`, no ThreadPoolExecutor, etc.)
- ✅ All external interactions via `workflow.execute_activity()` with timeouts and retry policies
- ✅ Run independent activities concurrently with `asyncio.gather` (e.g. draft picks + traded picks); await sequentially only on true data dependencies
- ✅ Prefer `workflow.logger` in workflows (replay-aware, injects workflow context) and `activity.logger` in activities. `workflow.logger` is **not** deprecated. The codebase is migrating off `print()`; don't add new `print()` calls.
- ✅ Wrap non-deterministic imports in `workflow.unsafe.imports_passed_through()`
- ✅ In workflows, import activities/other workflows with relative imports (e.g., `from activities.draft.get_drafts import...`)
- ✅ In worker registration, use the same top-level imports (e.g., `from workflows.draft_data_collection import...`) — workers run with `PYTHONPATH=src`, so imports are **not** `src.`-prefixed

### Type System & Code Quality
- ✅ All functions/parameters have explicit type hints (mypy compliant)
- ✅ Use `@dataclass` from pydantic.dataclasses for workflow inputs/outputs and API models
- ✅ All code is `async def` with proper `await`
- ✅ Line length 100 chars, black formatting, ruff linting
- ✅ Use `Dict[str, Any]` for JSON from APIs, minimize `Any` elsewhere

### Package Structure
- ✅ All packages have `__init__.py` with **docstrings only** (no imports, no `__all__`)
- ✅ Top-level imports resolved via `PYTHONPATH=src`: `from activities...`, `from workflows...`, `from schema...`, `from testing...` (no `src.` prefix anywhere — workers, tests, and modules all use this form)
- ✅ Docker: build `context: ./src` copies the `src` contents into `/app`, and containers run `python -m workers.<name>` from `/app`, so `activities`, `workflows`, `observability`, etc. resolve as top-level packages (locally, use `PYTHONPATH=src`)
- ❌ No circular dependencies (workflows → activities, never reverse)

### ML Pipeline
- ✅ ML activities live under `src/activities/ml/` (`training/`, `models/`, `predictions/`) and run on the ML task queue
- ✅ Models conform to the structural `DraftModel` Protocol (`activities/ml/models/model_interface.py`); management activities depend on the Protocol, not the concrete `TeamOwnerDraftModel`
- ✅ Models are persisted with joblib via `MLModelManager` (`activities/clients/ml_client.py`)

### Configuration & APIs
- ✅ Config from environment vars (DATABASE_URL, TEMPORAL_HOST, SLEEPER_USERNAME, SLEEPER_LEAGUE_NAME)
- ✅ Use httpx `AsyncClient` singleton for Sleeper API calls with `timeout=30`
- ✅ All API calls are async (no need for asyncio.to_thread)
- ✅ Sleeper API base: `https://api.sleeper.app/v1/`
- ❌ No hardcoded URLs, credentials, or secrets in code