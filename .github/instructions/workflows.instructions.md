---
applyTo: "src/workflows/**/*.py"
---

# Temporal Workflow Instructions

When working with Temporal workflows in this project:

## Core Patterns

- Use `@workflow.defn` decorator on workflow classes with `name` parameter for workflow ID
- Define `@workflow.run` async method as entry point  
- Use dataclasses from pydantic.dataclasses  for inputs with naming pattern: `{WorkflowName}Params` or `{WorkflowName}Input`
- All external calls (API, child workflows) MUST be via `workflow.execute_activity()` or `workflow.execute_child_workflow()`
- Use relative imports for activities (e.g., `from activities.draft.get_drafts import...`)

## Determinism Requirements

- Workflows MUST be deterministic
- Import non-deterministic modules inside `workflow.unsafe.imports_passed_through()`
- NEVER make direct API calls, database queries, or use `datetime.now()` in workflows
- Use `workflow.logger` for logging — it is replay-aware and injects workflow context (`workflow.logger` is NOT deprecated). The codebase is migrating off `print()`; don't add new `print()` calls.

## Concurrency

- Independent activities/child workflows should run concurrently, not in a sequential `await` loop
- Build a list of un-awaited handles from `workflow.execute_activity(...)` / `execute_child_workflow(...)` and join with `asyncio.gather(*handles)` — utilizing `asyncio` this way is deterministic and supported by Temporal
- Await sequentially only when there is a true data dependency (e.g. one activity's output feeds the next)
- Give each fanned-out activity a **unique** `activity_id` (include the per-item key) — duplicate IDs within a workflow collide

```python
from asyncio import gather

pick_handles = [
    workflow.execute_activity(
        get_specific_draft_picks,
        GetSpecificDraftPicksParams(draft_id=d["draft_id"]),
        start_to_close_timeout=timedelta(seconds=30),
        activity_id=f"activity-get_specific_draft_picks-{params.league_id}-{d['draft_id']}",
        retry_policy=activity_retry_policy,
    )
    for d in draft_data["league_drafts"]
]
results = await gather(*pick_handles)
```

## Activity Execution

- Always specify `start_to_close_timeout` using `timedelta`
- Always specify `retry_policy` with:
  - `maximum_attempts`
  - `initial_interval`
  - `maximum_interval`
  - `backoff_coefficient`

## Example Structure

```python
from datetime import timedelta
from dataclasses import dataclass
from typing import Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.league.get_data import get_league_data, GetLeagueDataParams
    from workflows.draft_data_collection import DraftDataCollectionWorkflow, DraftDataCollectionWorkflowParams

@dataclass(frozen=True, kw_only=True)
class MyWorkflowParams:
    """Input parameters for MyWorkflow."""
    league_id: str
    season: str = "2025"

@workflow.defn(name="my-workflow")
class MyWorkflow:
    """Workflow that demonstrates project patterns."""

    @workflow.run
    async def run(self, params: MyWorkflowParams) -> Dict[str, Any]:
        workflow.logger.info(f"Starting MyWorkflow for league {params.league_id}")
        workflow_activities = []
        
        activity_retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            backoff_coefficient=2.0,
        )

        # Execute activity
        league_data = await workflow.execute_activity(
            get_league_data,
            GetLeagueDataParams(league_id=params.league_id),
            start_to_close_timeout=timedelta(seconds=30),
            activity_id=f"activity-get_league_data-{params.league_id}",
            retry_policy=activity_retry_policy,
        )
        workflow.logger.info(f"Retrieved league data: {league_data}")
        workflow_activities.append({
            "activity": "get_league_data",
            "result": league_data
        })
        
        # Execute child workflow
        draft_result = await workflow.execute_child_workflow(
            DraftDataCollectionWorkflow.run,
            DraftDataCollectionWorkflowParams(
                league_id=params.league_id,
                season=params.season
            ),
            id=f"child-draft-{params.league_id}-{workflow.info().run_id}",
            retry_policy=activity_retry_policy,
        )
        workflow_activities.append({
            "workflow": "draft-data-collection",
            "result": draft_result
        })
        
        return {
            "activity_data": workflow_activities
        }
```

## Package Exports

After creating a new workflow:
1. `__init__.py` files contain **docstrings only** (no imports needed)
2. Register it in the appropriate worker — `src/workers/workflow_worker.py` (data collection) or `src/workers/ml_worker.py` (ML). Imports use the `PYTHONPATH=src` top-level form (no `src.` prefix):
   ```python
   from workflows.my_workflow import MyWorkflow
   ```
3. In other workflows, use the same import form:
   ```python
   from workflows.my_workflow import MyWorkflow
   ```
