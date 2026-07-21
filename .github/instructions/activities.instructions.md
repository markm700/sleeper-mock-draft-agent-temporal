---
applyTo: "src/activities/**/*.py"
---

# Temporal Activity Instructions

When working with Temporal activities in this project:

## Core Patterns

- Use `@activity.defn` decorator with `name` parameter on async functions
- Prefer `activity.logger` for logging (injects activity context).
- Always include try/except with error logging before raising
- All activities MUST be async
- Use dataclasses from pydantic.dataclasses for activity parameters
- Return `Dict[str, Any]` for structured results
- Activities (unlike workflows) MAY do I/O-bound operations — Sleeper API calls, PostgreSQL queries, ML training/inference. Data-collection and ML activities are registered on separate task queues/workers.

## Sleeper API Activities

For Sleeper API calls using httpx AsyncClient:

- Use `get_sleeper_client_manager()` singleton for httpx AsyncClient
- All Sleeper API methods are already async (NO need for asyncio.to_thread)
- Client has built-in timeout of 30 seconds
- Return wrapped in dict with descriptive key (e.g., `{"league_data": ...}`)
- Use dataclass from pydantic.dataclasses for parameters
- Sleeper API is read-only—NO POST, PUT, DELETE operations
- NO authentication headers required
- Use relative imports from activities (e.g., `from ..clients.sleeper_client_credential import...`)

Example:
```python
from pydantic.dataclasses import dataclass
from typing import Dict, Any
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.sleeper_client_credential import get_sleeper_client_manager

@dataclass(frozen=True, kw_only=True)
class GetLeagueDataParams:
    """Parameters for fetching league data."""
    league_id: str

@activity.defn(name="get_league_data")
async def get_league_data(input: GetLeagueDataParams) -> Dict[str, Any]:
    """Activity to fetch league information from Sleeper API."""
    sleeper = get_sleeper_client_manager()
    
    try:
        league_data = await sleeper.get_league(league_id=input.league_id)
        activity.logger.info(f"Successfully fetched league: {input.league_id}")
        return {"league_data": league_data}
    except Exception as e:
        activity.logger.error(f"Failed to fetch league {input.league_id}: {str(e)}")
        raise
```

## Activity with Filtering/Processing

Activities can include business logic like filtering:

```python
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

## Worker Registration

After creating a new activity, register it in the matching worker within the `src/workers/` folder. Imports use the `PYTHONPATH=src` top-level form (no `src.` prefix):

```python
with workflow.unsafe.imports_passed_through():
    from activities.draft.get_drafts import get_league_drafts
    from activities.draft.get_traded_draft_picks import get_traded_draft_picks
    # ... other imports

worker = Worker(
    client,
    task_queue=temporal_task_queue,
    workflows=[...],
    activities=[
        get_league_drafts,
        get_traded_draft_picks,
        # ... other activities
    ],
)
```

## Import Patterns

All imports use the top-level form resolved via `PYTHONPATH=src` — there is no `src.` prefix anywhere:
- **In activities**: `from activities.clients.sleeper_client_credential import ...`
- **In worker registration**: `from activities.draft.get_drafts import ...`
- **In workflows**: `from activities.draft.get_drafts import ...` (wrapped in `workflow.unsafe.imports_passed_through()`)
