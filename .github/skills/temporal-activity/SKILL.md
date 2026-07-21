---
name: temporal-activity
description: Create new Temporal activities (API, database, or ML). Use when asked to add external API calls, database operations, or ML processing functions.
---

# Creating Temporal Activities

Use this skill to create new Temporal activities that follow project conventions.

## Activity Types

Choose the appropriate pattern based on the activity's purpose:

### 1. Sleeper API Activities (e.g., `src/activities/draft/get_drafts.py`)

For Sleeper API calls using httpx AsyncClient.

```python
from pydantic.dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager

@dataclass(frozen=True, kw_only=True)
class GetLeagueDraftsParams:
    """Parameters for fetching all drafts for a league."""
    league_id: str

@activity.defn(name="get_league_drafts")
async def get_league_drafts(input: GetLeagueDraftsParams) -> Dict[str, Any]:
    """Activity to fetch all drafts associated with a league."""
    sleeper = get_sleeper_client_manager()
    
    try:
        league_drafts = await sleeper.get_league_drafts(league_id=input.league_id)
        activity.logger.info(f"Successfully fetched {len(league_drafts)} drafts for league {input.league_id}")
        return {"league_drafts": league_drafts}
    except Exception as e:
        activity.logger.error(f"Failed to fetch league drafts {input.league_id}: {str(e)}")
        raise
```

**Key points for Sleeper API activities**:
- Use `@dataclass` for parameters with explicit type hints, frozen=True, and kw_only=True
- Use `get_sleeper_client_manager()` singleton for httpx AsyncClient
- All Sleeper API methods are already async (NO need for asyncio.to_thread)
- Use `activity.logger` for logging (injects activity context; don't add new `print()` calls)
- Return wrapped in dict with descriptive key
- Use `@activity.defn(name="...")` to explicitly name activities

### 2. Activities with Filtering/Processing

Activities can include business logic like filtering:

```python
from pydantic.dataclasses import dataclass

@dataclass(frozen=True, kw_only=True)
class GetTradedDraftPicksParams:
    """Parameters for fetching traded picks for a league."""
    league_id: str
    season: str = "2025"

@activity.defn(name="get_traded_draft_picks")
async def get_traded_draft_picks(input: GetTradedDraftPicksParams) -> Dict[str, Any]:
    """Activity to fetch all traded draft picks for a given league, filtered by season."""
    sleeper = get_sleeper_client_manager()
    
    try:
        all_traded_picks = await sleeper.get_traded_draft_picks(league_id=input.league_id)
        
        # Filter traded picks by season
        filtered_picks = [
            pick for pick in all_traded_picks
            if pick.get("season") == input.season
        ]
        
        activity.logger.info(f"Fetched {len(filtered_picks)} traded picks for season {input.season}")
        return {"traded_draft_picks": filtered_picks}
    except Exception as e:
        activity.logger.error(f"Failed to fetch traded picks: {str(e)}")
        raise
```

### 3. Database Activities

For database CRUD operations using SQLAlchemy ORM.

```python
from pydantic.dataclasses import dataclass
from temporalio import activity, workflow
from typing import Dict, Any

with workflow.unsafe.imports_passed_through():
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import League

@dataclass(frozen=True, kw_only=True)
class StoreLeagueParams:
    """Parameters for storing league data."""
    league_data: Dict[str, Any]

@activity.defn(name="store_league")
async def store_league(input: StoreLeagueParams) -> bool:
    """Store league information in database."""
    activity.logger.info(f"Storing league: {input.league_data.get('league_id')}")
    
    try:
        pg = get_postgres_client_manager()
        pg.upsert_record(model=League, data=input.league_data)
        activity.logger.info("League stored successfully")
        return True
    except Exception as e:
        activity.logger.error(f"Failed to store league: {str(e)}")
        raise
```

**Key points for database activities**:
- Store functions return `bool`
- Fetch functions return `Dict[str, Any]`
- Include TODO comments for SQLAlchemy implementation
- NEVER perform database operations in workflows

### 4. ML Activities

For machine learning operations, analysis, and computations. 

```python
from pydantic.dataclasses import dataclass
from temporalio import activity
from typing import Dict, Any

@dataclass(frozen=True, kw_only=True)
class CalculateADPParams:
    """Parameters for ADP calculation."""
    picks: list[Dict[str, Any]]
    weighted: bool = True

@activity.defn(name="calculate_adp")
async def calculate_adp(input: CalculateADPParams) -> Dict[str, Any]:
    """
    Calculate Average Draft Position weighted by recency.
    
    Args:
        input: Parameters containing picks and weighting flag
        
    Returns:
        ADP data for each player
    """
    activity.logger.info(f"Calculating ADP from {len(input.picks)} picks")
    
    try:
        # Group picks by player_id; compute mean, std_dev, sample_size;
        # apply exponential decay weighting (factor 0.7) when weighted=True.
        # See activities/ml/calculate_adp.py for the implemented version.
        adp_results = {}
        activity.logger.info(f"Calculated ADP for {len(adp_results)} players")
        return {"adp_data": adp_results}
    except Exception as e:
        activity.logger.error(f"Failed to calculate ADP: {str(e)}")
        raise
```

**Key points for ML activities**:
- Use dataclass parameters with meaningful names
- Include detailed docstrings explaining algorithms
- Use TODO comments for multi-step algorithm documentation
- Include business context (e.g., "recency weighting factor 0.7")

## General Activity Rules

All activities must:

- ✅ Use `@activity.defn(name="...")` decorator with explicit name
- ✅ Be `async def` functions
- ✅ Use `activity.logger` for logging (injects activity context; don't add new `print()` calls)
- ✅ Use `@dataclass` from pydantic.dataclasses for parameters
- ✅ Include try/except with error logging before raising
- ✅ Have type hints for parameters and return values
- ✅ Have descriptive docstrings
- ✅ Return wrapped in dict with descriptive key (e.g., `{"league_data": ...}`)

## After Creation

### 1. Register in Worker

Add to the matching worker. Imports use the `PYTHONPATH=src` top-level form (no `src.` prefix):

```python
with workflow.unsafe.imports_passed_through():
    from activities.draft.get_drafts import get_league_drafts
    from activities.draft.get_traded_draft_picks import get_traded_draft_picks
    # Add new activity import

worker = Worker(
    client,
    task_queue=temporal_task_queue,
    workflows=[...],
    activities=[
        get_league_drafts,
        get_traded_draft_picks,
        # Add new activity here
    ],
)
```

### 2. Call from Workflows

Import activities using relative imports in workflows:

```python
from temporalio import workflow
from datetime import timedelta
from pydantic.dataclasses import dataclass

with workflow.unsafe.imports_passed_through():
    from activities.draft.get_drafts import GetLeagueDraftsParams

@workflow.defn(name="my_workflow")
class MyWorkflow:
    @workflow.run
    async def run(self, input: MyWorkflowParams) -> Dict[str, Any]:
        # Call activity with timeout and retry policy
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
        return {"drafts": league_drafts}
```

### 3. Import Patterns

All imports use the top-level form resolved via `PYTHONPATH=src` — no `src.` prefix anywhere:
- **In activities**: `from activities.clients.sleeper_client_credential import ...`
- **In workflows**: `from activities.draft.get_drafts import ...`
- **In worker registration**: `from activities.draft.get_drafts import ...`
