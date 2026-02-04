---
applyTo: "src/workflows/**/*.py"
---

# Temporal Workflow Instructions

When working with Temporal workflows in this project:

## Core Patterns

- Use `@workflow.defn` decorator on workflow classes
- Define `@workflow.run` async method as entry point  
- Use dataclasses for inputs/outputs with naming pattern: `{WorkflowName}Input`, `{WorkflowName}Result`
- All external calls (API, database) MUST be via `workflow.execute_activity()`

## Determinism Requirements

- Workflows MUST be deterministic
- Import non-deterministic modules inside `workflow.unsafe.imports_passed_through()`
- NEVER make direct API calls, database queries, or use `datetime.now()` in workflows
- Use `workflow.logger` for logging (NEVER standard Python logging)

## Activity Execution

- Always specify `start_to_close_timeout` using `timedelta`
- Always specify `retry_policy` with:
  - `maximum_attempts`
  - `initial_interval`
  - `maximum_interval`
  - `backoff_coefficient`

## Example Structure

```python
from temporalio import workflow
from dataclasses import dataclass
from datetime import timedelta

with workflow.unsafe.imports_passed_through():
    from src.activities.database import fetch_league_settings

@dataclass
class MyWorkflowInput:
    league_id: str
    season: str

@dataclass  
class MyWorkflowResult:
    success: bool
    errors: list[str]

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, input_data: MyWorkflowInput) -> MyWorkflowResult:
        settings = await workflow.execute_activity(
            fetch_league_settings,
            input_data.league_id,
            start_to_close_timeout=timedelta(seconds=30),
        )
        return MyWorkflowResult(success=True, errors=[])
```

## Package Exports

After creating a new workflow:
1. Add to `src/workflows/__init__.py` in the `__all__` list
2. Use absolute imports: `from src.workflows.my_workflow import MyWorkflow`
