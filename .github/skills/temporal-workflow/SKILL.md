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

3. **Import activities** inside `workflow.unsafe.imports_passed_through()` context

4. **Create workflow class** with `@workflow.defn` decorator

5. **Implement `@workflow.run` method** that:
   - Accepts input dataclass
   - Returns result dataclass
   - Calls activities via `workflow.execute_activity()`
   - Specifies `start_to_close_timeout` and `retry_policy` for each activity
   - Uses `workflow.logger` for logging
   - Handles errors gracefully

6. **Export workflow** in `src/workflows/__init__.py` by adding to `__all__` list

## Example Template

```python
from temporalio import workflow
from dataclasses import dataclass
from datetime import timedelta

with workflow.unsafe.imports_passed_through():
    from src.activities.database import fetch_data, store_results
    from src.activities.api_client import fetch_external_data

@dataclass
class {WorkflowName}Input:
    """Input parameters for {WorkflowName}"""
    # Add required fields
    league_id: str
    season: str
    # Add optional fields with defaults
    include_history: bool = False

@dataclass
class {WorkflowName}Result:
    """Result from {WorkflowName}"""
    success: bool
    errors: list[str]
    # Add additional result fields
    records_processed: int = 0

@workflow.defn
class {WorkflowName}:
    """
    Brief description of what this workflow does.
    
    Typical use case and behavior details.
    """
    
    @workflow.run
    async def run(self, input_data: {WorkflowName}Input) -> {WorkflowName}Result:
        workflow.logger.info(f"Starting {WorkflowName} for league {input_data.league_id}")
        errors = []
        
        try:
            # Step 1: Fetch data
            data = await workflow.execute_activity(
                fetch_data,
                input_data.league_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0,
                ),
            )
            
            # Step 2: Process data
            results = await workflow.execute_activity(
                process_data,
                {"data": data, "options": input_data.include_history},
                start_to_close_timeout=timedelta(seconds=60),
            )
            
            # Step 3: Store results
            await workflow.execute_activity(
                store_results,
                results,
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            workflow.logger.info(f"Completed {WorkflowName} successfully")
            return {WorkflowName}Result(
                success=True,
                errors=errors,
                records_processed=len(results)
            )
            
        except Exception as e:
            workflow.logger.error(f"{WorkflowName} failed: {str(e)}")
            errors.append(str(e))
            return {WorkflowName}Result(
                success=False,
                errors=errors,
                records_processed=0
            )
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

1. Add workflow to `src/workflows/__init__.py`:
   ```python
   __all__ = [
       "ExistingWorkflow",
       "{WorkflowName}",  # Add new workflow
   ]
   ```

2. Create corresponding activities if needed (see `temporal-activity` skill)

3. Test workflow using Temporal test environment
