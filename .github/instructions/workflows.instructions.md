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
- Use `print()` for logging (simpler and clearer than workflow.logger)

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
        print(f"Starting MyWorkflow for league {params.league_id}")
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
        print(f"Retrieved league data: {league_data}")
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
2. In worker (`src/workers/workflow_worker.py`), use absolute imports:
   ```python
   from src.workflows.my_workflow import MyWorkflow
   ```
3. In other workflows, use relative imports:
   ```python
   from workflows.my_workflow import MyWorkflow
   ```
