# Copilot Instructions for Sleeper Mock Draft Agent

## Overview

This repository implements a Fantasy Football Mock Draft Prediction Agent for Sleeper, using **Temporal workflows** for durable orchestration and **httpx** for async API interactions.

**Tech Stack**: Python 3.12+ | Temporal v1.5.0+ | httpx | Sleeper API | FastAPI

**Architecture**: 
- Temporal workflows orchestrate long-running draft simulations and data collection
- Activities handle external interactions (Sleeper API calls)
- FastAPI service triggers workflows via Temporal client
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




## Critical Cross-Cutting Rules

### Temporal Patterns
- ✅ Workflows use `@workflow.defn`, activities use `@activity.defn`
- ❌ Workflows MUST be deterministic (no API calls, DB queries, `datetime.now()`)
- ✅ All external interactions via `workflow.execute_activity()` with timeouts and retry policies
- ✅ Use `print()` for logging in workflows (workflow.logger deprecated in newer Temporal versions)
- ✅ Use `print()` for logging in activities (simpler than activity.logger)
- ✅ Wrap non-deterministic imports in `workflow.unsafe.imports_passed_through()`
- ✅ In workflows, import activities/other workflows with relative imports (e.g., `from activities.draft.get_drafts import...`)
- ✅ In worker registration, use absolute `src.` imports (e.g., `from src.workflows.draft_data_collection import...`)

### Type System & Code Quality
- ✅ All functions/parameters have explicit type hints (mypy compliant)
- ✅ Use `@dataclass` for workflow inputs/outputs and API models
- ✅ All code is `async def` with proper `await`
- ✅ Line length 100 chars, black formatting, ruff linting
- ✅ Use `Dict[str, Any]` for JSON from APIs, minimize `Any` elsewhere

### Package Structure
- ✅ All packages have `__init__.py` with **docstrings only** (no imports, no `__all__`)
- ✅ Relative imports in workflows/activities (e.g., `from ..activities.draft import...`)
- ✅ Absolute `src.` imports only in worker registration and tests
- ✅ Docker: `PYTHONPATH=/app` and src copied to `/app/src` for package resolution
- ❌ No circular dependencies (workflows → activities, never reverse)

### Configuration & APIs
- ✅ Config from environment vars (DATABASE_URL, TEMPORAL_HOST, SLEEPER_USERNAME, SLEEPER_LEAGUE_NAME)
- ✅ Use httpx `AsyncClient` singleton for Sleeper API calls with `timeout=30`
- ✅ All API calls are async (no need for asyncio.to_thread)
- ✅ Sleeper API base: `https://api.sleeper.app/v1/`
- ❌ No hardcoded URLs, credentials, or secrets in code