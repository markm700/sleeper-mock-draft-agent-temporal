---
name: temporal-activity
description: Create new Temporal activities (API, database, or ML). Use when asked to add external API calls, database operations, or ML processing functions.
---

# Creating Temporal Activities

Use this skill to create new Temporal activities that follow project conventions.

## Activity Types

Choose the appropriate pattern based on the activity's purpose:

### 1. API Activities (`src/activities/api_client.py` or new file)

For external API calls (Sleeper API or other APIs).

```python
from temporalio import activity
import asyncio
from typing import Dict, List, Any

@activity.defn
async def fetch_{resource}(resource_id: str) -> Dict[str, Any]:
    """Fetch {resource} from external API."""
    activity.logger.info(f"Fetching {resource}: {resource_id}")
    
    try:
        # Use asyncio.to_thread for synchronous requests
        data = await asyncio.to_thread(
            _client._make_request,
            f"{resource}/{resource_id}"
        )
        activity.logger.info(f"Successfully fetched {resource}: {resource_id}")
        return data
    except Exception as e:
        activity.logger.error(f"Failed to fetch {resource} {resource_id}: {str(e)}")
        raise
```

**Key points for API activities**:
- Wrap sync requests with `await asyncio.to_thread()`
- Use singleton client with `requests.Session()`
- Specify `timeout=30` on HTTP requests
- Return `Dict[str, Any]` for single resources, `List[Dict[str, Any]]` for collections

### 2. Database Activities (`src/activities/database.py`)

For database CRUD operations using SQLAlchemy ORM.

```python
from temporalio import activity
from typing import Dict, List, Any

@activity.defn
async def store_{entity}(data: Dict[str, Any]) -> bool:
    """Store {entity} in database."""
    activity.logger.info(f"Storing {entity}: {data.get('id')}")
    
    try:
        # TODO: Implement SQLAlchemy insert/update
        # session = get_db_session()
        # entity = {Entity}(**data)
        # session.merge(entity)
        # session.commit()
        
        activity.logger.info("{Entity} stored successfully")
        return True
    except Exception as e:
        activity.logger.error(f"Failed to store {entity}: {str(e)}")
        raise

@activity.defn
async def fetch_{entity}(entity_id: str) -> Dict[str, Any]:
    """Fetch {entity} from database."""
    activity.logger.info(f"Fetching {entity}: {entity_id}")
    
    try:
        # TODO: Query database
        # session = get_db_session()
        # entity = session.query({Entity}).filter_by(id=entity_id).first()
        # return entity.to_dict()
        
        data = {}
        activity.logger.info("{Entity} fetched successfully")
        return data
    except Exception as e:
        activity.logger.error(f"Failed to fetch {entity}: {str(e)}")
        raise
```

**Key points for database activities**:
- Store functions return `bool`
- Fetch functions return `Dict[str, Any]` or `List[Dict[str, Any]]`
- Include TODO comments for SQLAlchemy implementation
- NEVER perform database operations in workflows

### 3. ML Activities (`src/activities/ml_models.py`)

For machine learning operations, analysis, and computations.

```python
from temporalio import activity
from typing import Dict, Any

@activity.defn
async def calculate_{metric}(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate {metric} for analysis.
    
    Args:
        params: Dict containing input data and configuration
            - data: Input data to analyze
            - options: Configuration options
        
    Returns:
        Results dictionary with calculated metrics
    """
    input_data = params["data"]
    options = params.get("options", {})
    
    activity.logger.info(f"Calculating {metric} for {len(input_data)} records")
    
    try:
        # TODO: Implement calculation
        # - Step 1: Prepare data
        # - Step 2: Apply algorithm
        # - Step 3: Format results
        
        results = {}
        activity.logger.info(f"Calculated {metric} successfully")
        return results
    except Exception as e:
        activity.logger.error(f"Failed to calculate {metric}: {str(e)}")
        raise
```

**Key points for ML activities**:
- Accept dict parameters: `params: Dict[str, Any]`
- Include detailed docstrings explaining algorithms
- Use TODO comments for multi-step algorithm documentation
- Include business context (e.g., "recency weighting factor 0.7")

## General Activity Rules

All activities must:

- ✅ Use `@activity.defn` decorator
- ✅ Be `async def` functions
- ✅ Use `activity.logger` for logging (NEVER standard logging)
- ✅ Include try/except with error logging before raising
- ✅ Have type hints for parameters and return values
- ✅ Have descriptive docstrings

## After Creation

If creating activities in a new file:

1. Add to `src/activities/__init__.py`:
   ```python
   __all__ = [
       "existing_activity",
       "new_activity",  # Add new activity
   ]
   ```

2. Import in workflows using `workflow.unsafe.imports_passed_through()`:
   ```python
   with workflow.unsafe.imports_passed_through():
       from src.activities.my_activities import new_activity
   ```

3. Call from workflows with timeouts and retry policies:
   ```python
   result = await workflow.execute_activity(
       new_activity,
       params,
       start_to_close_timeout=timedelta(seconds=30),
       retry_policy=workflow.RetryPolicy(
           maximum_attempts=3,
           initial_interval=timedelta(seconds=1),
           maximum_interval=timedelta(seconds=10),
           backoff_coefficient=2.0,
       ),
   )
   ```
