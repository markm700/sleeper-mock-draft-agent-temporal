---
name: temporal-workflow
description: Create a new Temporal workflow following project patterns. Use when asked to create workflows, orchestration logic, or long-running business processes.
---

# Creating a Temporal Workflow

Use this skill to create a new Temporal workflow that follows project conventions.

## Steps

1. **Create workflow file** at `src/workflows/{feature_name}.py`

2. **Define input/output dataclasses** with naming pattern:
   - `{WorkflowName}Input` - workflow parameters
   - `{WorkflowName}Result` - workflow return value

3. **Import activities** inside `workflow.unsafe.imports_passed_through()` using relative imports

4. **Create workflow class** with `@workflow.defn(name="...")` decorator with explicit name

5. **Implement `@workflow.run` method** that:
   - Accepts input dataclass
   - Returns `Dict[str, Any]`
   - Calls activities via `workflow.execute_activity(name, params, ...)`
   - Specifies `start_to_close_timeout` and `retry_policy` for each activity
   - Uses `workflow.logger` for logging (replay-aware; NOT deprecated)
   - Runs independent activities concurrently with `asyncio.gather`; awaits sequentially only on data dependencies
   - Handles errors gracefully

## Example: Simple Workflow

```python
from temporalio import workflow
from pydantic.dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Any

with workflow.unsafe.imports_passed_through():
    from activities.draft.get_drafts import GetLeagueDraftsParams

@dataclass(frozen=True, kw_only=True)
class DraftDataCollectionParams:
    """Input parameters for DraftDataCollectionWorkflow"""
    league_id: str
    season: str = "2025"

@workflow.defn(name="draft_data_collection_workflow")
class DraftDataCollectionWorkflow:
    """
    Collect all draft-related data for a league.
    
    Fetches draft metadata and pick details.
    """
    
    @workflow.run
    async def run(self, input: DraftDataCollectionParams) -> Dict[str, Any]:
        workflow.logger.info(f"Starting draft data collection for league {input.league_id}")
        
        # Fetch league drafts
        drafts_result = await workflow.execute_activity(
            "get_league_drafts",
            GetLeagueDraftsParams(league_id=input.league_id),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=workflow.RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                backoff_coefficient=2.0,
            ),
        )
        
        league_drafts = drafts_result["league_drafts"]
        workflow.logger.info(f"Fetched {len(league_drafts)} drafts")
        
        return {
            "drafts": league_drafts,
            "success": True
        }
```

## Example: Workflow with Child Workflows

```python
from temporalio import workflow
from pydantic.dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Any

with workflow.unsafe.imports_passed_through():
    from workflows.league_data_collection import (
        LeagueDataCollectionParams,
        LeagueDataCollectionWorkflow
    )
    from workflows.draft_data_collection import (
        DraftDataCollectionParams,
        DraftDataCollectionWorkflow
    )

@dataclass(frozen=True, kw_only=True)
class FullDataCollectionParams:
    """Input parameters for full data collection"""
    username: str
    league_name: str
    season: str = "2025"

@workflow.defn(name="full_data_collection_workflow")
class FullDataCollectionWorkflow:
    """
    Comprehensive data collection for user and league.
    
    Orchestrates league and draft data collection as child workflows.
    """
    
    @workflow.run
    async def run(self, input: FullDataCollectionParams) -> Dict[str, Any]:
        workflow.logger.info(f"Starting full data collection for {input.username}")
        
        # Execute league data collection child workflow
        @workflow.defn(name="...")` with explicit workflow name
- ✅ Use `workflow.execute_activity(name, params, ...)` for ALL external interactions
- ✅ Pass activity parameters as dataclass instances
- ✅ Use `workflow.logger` for logging (replay-aware; NOT deprecated — don't add new `print()` calls)
- ✅ Import activities/other workflows with relative imports (e.g., `from activities.draft.get_drafts import...`)
- ✅ Import non-deterministic modules inside `workflow.unsafe.imports_passed_through()`
- ❌ NEVER make direct API calls or database queries in workflows
- ❌ NEVER use `datetime.now()` or random numbers in workflows
- ❌ NEVER use blocking I/O in workflows

## After Creation

### 1. Register in Worker

Add workflow to `src/workers/workflow_worker.py`:

```python
with workflow.unsafe.imports_passed_through():
    from workflows.draft_data_collection import DraftDataCollectionWorkflow
    # Add new workflow import

worker = Worker(
    client,
    task_queue=temporal_task_queue,
    workflows=[
        DraftDataCollectionWorkflow,
        # Add new workflow here
    ],
    activities=[...],
)
```

### 2. Package Markers

Ensure `src/workflows/__init__.py` contains only a docstring (no imports or `__all__`):

```python
"""Temporal workflows for orchestrating data collection and analysis."""
```

### 3. Import Patterns

- **In workflows**: use relative imports (e.g., `from activities.draft.get_drafts import...`)
- **In worker registration**: use the same top-level form (e.g., `from workflows.draft_data_collection import...`) — `PYTHONPATH=src`, no `src.` prefix
            task_queue="temporal-task-queue",
        )
        
        workflow.logger.info("Completed full data collection")
        
        return {
            "league_data": league_data,
            "draft_data": draft_result,
            "success": True
        }
```

## Critical Rules

- ✅ Workflows MUST be deterministic
- ✅ Use `workflow.execute_activity()` for ALL external interactions
- ✅ Use `workflow.logger` for logging (NEVER standard logging)
- ✅ Import non-deterministic modules inside `workflow.unsafe.imports_passed_through()`
- ❌ NEVER make direct API calls or database queries in workflows
- ❌ NEVER use `datetime.now()` or random numbers in workflows
- ❌ NEVER use blocking I/O in workflows

## After Creation

1. Keep `src/workflows/__init__.py` as a docstring only (no imports, no `__all__`) — register the workflow in the worker instead (see "Register in Worker" above)

2. Create corresponding activities if needed (see `temporal-activity` skill)

3. Test workflow using Temporal test environment
