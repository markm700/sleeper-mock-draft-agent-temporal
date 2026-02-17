---
applyTo: "src/activities/**/*.py"
---

# Temporal Activity Instructions

When working with Temporal activities in this project:

## Core Patterns

- Use `@activity.defn` decorator on async functions
- Use `activity.logger` for logging (NEVER standard Python logging)
- Always include try/except with error logging before raising
- All activities MUST be async

## API Activities (`api_client.py`)

- Wrap synchronous requests with `await asyncio.to_thread()`
- Use singleton client with `requests.Session()` for connection pooling
- All Sleeper API calls target `https://api.sleeper.app/v1/`
- Specify `timeout=30` on HTTP requests
- Return type: `Dict[str, Any]` for single resources, `List[Dict[str, Any]]` for collections
- Sleeper API is read-only—NO POST, PUT, DELETE operations
- NO authentication headers required

Example:
```python
from temporalio import activity
import asyncio

@activity.defn
async def fetch_league(league_id: str) -> Dict[str, Any]:
    """Fetch league information from Sleeper API."""
    print(f"Fetching league: {league_id}")
    
    try:
        league_data = await asyncio.to_thread(
            _client._make_request,
            f"league/{league_id}"
        )
        print(f"Successfully fetched league: {league_id}")
        return league_data
    except Exception as e:
        activity.logger.error(f"Failed to fetch league {league_id}: {str(e)}")
        raise
```

## Database Activities (`database.py`)

- Store functions return `bool` to indicate success
- Fetch functions return `Dict[str, Any]` or `List[Dict[str, Any]]`
- Accept dict parameters with unpacking: `params: Dict[str, Any]`
- Include TODO comments for SQLAlchemy implementation details
- NEVER perform database operations directly in workflows—only in activities

Example:
```python
from temporalio import activity

@activity.defn
async def store_league(league_data: Dict[str, Any]) -> bool:
    """Store league information in database."""
    print(f"Storing league: {league_data.get('league_id')}")
    
    try:
        # TODO: Implement SQLAlchemy insert/update
        # session = get_db_session()
        # league = League(**league_data)
        # session.merge(league)
        # session.commit()
        
        print("League stored successfully")
        return True
    except Exception as e:
        activity.logger.error(f"Failed to store league: {str(e)}")
        raise
```

## ML Activities (`ml_models.py`)

- Accept dict parameters: `params: Dict[str, Any]`
- Include detailed docstrings explaining algorithms
- Use TODO comments for multi-step algorithm documentation
- Domain-specific names: `calculate_adp`, `identify_owner_archetypes`, `detect_homer_bias`
- Business context: recency weighting (0.7 decay), k-means clustering, Monte Carlo batching

Example:
```python
from temporalio import activity

@activity.defn
async def calculate_adp(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate Average Draft Position weighted by recency.
    
    Args:
        params: Dict with picks, seasons, weighted flag
        
    Returns:
        ADP data for each player
    """
    picks = params["picks"]
    weighted = params.get("weighted", True)
    
    print(f"Calculating ADP from {len(picks)} picks")
    
    try:
        # TODO: Implement ADP calculation
        # - Group picks by player_id
        # - Calculate mean, std_dev, sample_size
        # - Apply exponential decay weighting (factor 0.7) if weighted=True
        # - Store results in adp_cache table
        
        adp_results = {}
        print(f"Calculated ADP for {len(adp_results)} players")
        return adp_results
    except Exception as e:
        activity.logger.error(f"Failed to calculate ADP: {str(e)}")
        raise
```
