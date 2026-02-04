# Sleeper API Guide for Mock Draft Agent (v1)
*Created: January 27, 2026*  
*Technology Stack: Python + Temporal*

## Overview

The Sleeper API is a **read-only HTTP API** that provides free access to users' leagues, drafts, and rosters. This guide focuses on the endpoints and data structures needed to build a mock draft agent based on your fantasy league's historical data.

**Implementation Strategy**: This project will be built using **Python** for data processing and analysis, with **Temporal** orchestrating the workflows for data collection, analysis, and mock draft simulation.

### Key Constraints
- **No authentication required** (read-only API)
- **Rate limit**: Stay under 1000 API calls per minute to avoid IP blocking
- **Base URL**: `https://api.sleeper.app/v1/`

---

## Core Workflow for Mock Draft Agent

### 1. Get User Information
Start by identifying the user whose league history you want to analyze.

**Endpoint**: `GET /user/<username>` or `GET /user/<user_id>`

```bash
curl "https://api.sleeper.app/v1/user/<username>"
```

**Response**:
```json
{
  "username": "sleeperuser",
  "user_id": "12345678",
  "display_name": "SleeperUser",
  "avatar": "cc12ec49965eb7856f84d71cf85306af"
}
```

**⚠️ Important**: Store `user_id` (not `username`) as usernames can change over time.

---

### 2. Get All Leagues for User
Retrieve all leagues the user participated in for a specific sport and season.

**Endpoint**: `GET /user/<user_id>/leagues/<sport>/<season>`

```bash
curl "https://api.sleeper.app/v1/user/<user_id>/leagues/nfl/2024"
```

**Response**:
```json
[
  {
    "league_id": "289646328504385536",
    "name": "Sleeperbot Friends League",
    "season": "2024",
    "status": "complete",
    "draft_id": "289646328508579840",
    "total_rosters": 12,
    "roster_positions": [...],
    "scoring_settings": {...},
    "settings": {...},
    "previous_league_id": "198946952535085056"
  }
]
```

**Key Fields**:
- `league_id`: Unique identifier for the league
- `draft_id`: Links to the draft data
- `status`: Can be `"pre_draft"`, `"drafting"`, `"in_season"`, or `"complete"`
- `previous_league_id`: For dynasty leagues, links to previous season
- `scoring_settings`: PPR, half-PPR, standard, etc.
- `roster_positions`: Array showing roster construction (QB, RB, WR, TE, FLEX, etc.)

---

### 3. Get League Details
Fetch comprehensive information about a specific league.

**Endpoint**: `GET /league/<league_id>`

```bash
curl "https://api.sleeper.app/v1/league/<league_id>"
```

This returns the same structure as the leagues array above but for a single league.

---

### 4. Get League Rosters
Retrieve all rosters in a league to see player ownership and roster construction.

**Endpoint**: `GET /league/<league_id>/rosters`

```bash
curl "https://api.sleeper.app/v1/league/<league_id>/rosters"
```

**Response**:
```json
[
  {
    "roster_id": 1,
    "owner_id": "188815879448829952",
    "league_id": "206827432160788480",
    "players": ["1046", "138", "147", "2257", "2307", ...],
    "starters": ["2307", "2257", "4034", "147", "642", ...],
    "reserve": [],
    "settings": {
      "wins": 5,
      "losses": 9,
      "ties": 0,
      "fpts": 1617,
      "fpts_decimal": 78,
      "fpts_against": 1670,
      "fpts_against_decimal": 32,
      "waiver_position": 7,
      "waiver_budget_used": 0,
      "total_moves": 0
    }
  }
]
```

**Key Fields**:
- `players`: Array of all player IDs on the roster
- `starters`: Ordered array of starting player IDs
- `settings`: Season statistics (wins, losses, points scored, etc.)

---

### 5. Get League Users
Retrieve all users participating in a league.

**Endpoint**: `GET /league/<league_id>/users`

```bash
curl "https://api.sleeper.app/v1/league/<league_id>/users"
```

**Response**:
```json
[
  {
    "user_id": "<user_id>",
    "username": "<username>",
    "display_name": "<display_name>",
    "avatar": "1233456789",
    "is_owner": true,
    "metadata": {
      "team_name": "Dezpacito"
    }
  }
]
```

**Key Fields**:
- `is_owner`: Indicates commissioner status
- `metadata.team_name`: Custom team name if set

---

### 6. Get Draft Information

#### Get All Drafts for User
**Endpoint**: `GET /user/<user_id>/drafts/<sport>/<season>`

```bash
curl "https://api.sleeper.app/v1/user/<user_id>/drafts/nfl/2024"
```

#### Get All Drafts for League
**Endpoint**: `GET /league/<league_id>/drafts`

```bash
curl "https://api.sleeper.app/v1/league/<league_id>/drafts"
```

**Response**:
```json
[
  {
    "draft_id": "257270643320426496",
    "league_id": "257270637750382592",
    "type": "snake",
    "status": "complete",
    "start_time": 1515700800000,
    "season": "2024",
    "settings": {
      "teams": 12,
      "rounds": 15,
      "pick_timer": 120,
      "slots_qb": 1,
      "slots_rb": 2,
      "slots_wr": 2,
      "slots_te": 1,
      "slots_flex": 2,
      "slots_def": 1,
      "slots_k": 1,
      "slots_bn": 5
    },
    "metadata": {
      "scoring_type": "ppr",
      "name": "My Dynasty",
      "description": ""
    },
    "draft_order": {
      "12345678": 1,
      "23434332": 2
    },
    "slot_to_roster_id": {
      "1": 10,
      "2": 3,
      "3": 5
    }
  }
]
```

**Key Fields**:
- `type`: Draft type (typically `"snake"` or `"linear"`)
- `draft_order`: Maps `user_id` to draft slot position
- `slot_to_roster_id`: Maps draft slot to `roster_id`

---

### 7. Get All Draft Picks
**This is critical for training your mock draft agent!**

**Endpoint**: `GET /draft/<draft_id>/picks`

```bash
curl "https://api.sleeper.app/v1/draft/<draft_id>/picks"
```

**Response**:
```json
[
  {
    "player_id": "2391",
    "picked_by": "234343434",
    "roster_id": "1",
    "round": 1,
    "draft_slot": 1,
    "pick_no": 1,
    "metadata": {
      "team": "ARI",
      "position": "RB",
      "first_name": "David",
      "last_name": "Johnson",
      "status": "Active",
      "injury_status": ""
    },
    "is_keeper": null,
    "draft_id": "257270643320426496"
  }
]
```

**Key Fields**:
- `pick_no`: Overall pick number (1, 2, 3...)
- `round`: Draft round
- `draft_slot`: Which column on the draft board (user's position)
- `player_id`: ID to look up in players database
- `is_keeper`: Indicates if this was a keeper pick
- `metadata`: Contains player info snapshot at draft time

---

### 8. Get Player Information
Since all player references use IDs, you need the player database.

**Endpoint**: `GET /players/nfl`

```bash
curl "https://api.sleeper.app/v1/players/nfl"
```

**⚠️ Important**: 
- Response size is ~5MB
- Call **once per day maximum**
- Store data locally
- Use for mapping player IDs to player details

**Response Structure**:
```json
{
  "3086": {
    "player_id": "3086",
    "first_name": "Tom",
    "last_name": "Brady",
    "position": "QB",
    "team": "NE",
    "number": 12,
    "age": 40,
    "height": "6'4\"",
    "weight": "220",
    "college": "Michigan",
    "years_exp": 14,
    "fantasy_positions": ["QB"],
    "depth_chart_position": 1,
    "depth_chart_order": 1,
    "status": "Active",
    "injury_status": null,
    "search_rank": 24
  }
}
```

**Key Fields for Mock Draft Agent**:
- `position`: Player position
- `fantasy_positions`: Eligible fantasy positions
- `team`: Current NFL team
- `depth_chart_position`: Depth on team
- `search_rank`: Sleeper's internal ranking
- `status`: Active, Injured Reserve, etc.
- `injury_status`: Current injury status

---

### 9. Get Matchups (Weekly Performance)
Analyze weekly performance to understand player value in your league.

**Endpoint**: `GET /league/<league_id>/matchups/<week>`

```bash
curl "https://api.sleeper.app/v1/league/<league_id>/matchups/1"
```

**Response**:
```json
[
  {
    "roster_id": 1,
    "matchup_id": 2,
    "points": 124.5,
    "custom_points": null,
    "starters": ["421", "4035", "3242", ...],
    "players": ["421", "4035", "3242", "2133", ...]
  }
]
```

**Key Fields**:
- `points`: Total points scored based on league scoring
- `starters`: Players who started (in order)
- `players`: All players on roster that week
- Teams with same `matchup_id` played against each other

---

### 10. Get Transactions
Track waiver wire activity, trades, and roster moves.

**Endpoint**: `GET /league/<league_id>/transactions/<round>`

```bash
curl "https://api.sleeper.app/v1/league/<league_id>/transactions/1"
```

**Response Types**:

**Trade**:
```json
{
  "type": "trade",
  "transaction_id": "434852362033561600",
  "status": "complete",
  "roster_ids": [2, 1],
  "leg": 1,
  "draft_picks": [
    {
      "season": "2024",
      "round": 5,
      "roster_id": 1,
      "previous_owner_id": 1,
      "owner_id": 2
    }
  ],
  "adds": {"2315": 1},
  "drops": {"1736": 2},
  "waiver_budget": [
    {
      "sender": 2,
      "receiver": 3,
      "amount": 55
    }
  ],
  "creator": "160000000000000000",
  "consenter_ids": [2, 1]
}
```

**Free Agent/Waiver**:
```json
{
  "type": "free_agent",
  "transaction_id": "434890120798142464",
  "status": "complete",
  "roster_ids": [1],
  "leg": 1,
  "adds": {"2315": 1},
  "drops": {"1736": 1},
  "settings": {"waiver_bid": 44},
  "metadata": null
}
```

---

### 11. Get Traded Picks
Important for dynasty leagues.

**Endpoint**: `GET /league/<league_id>/traded_picks`

```bash
curl "https://api.sleeper.app/v1/league/<league_id>/traded_picks"
```

**Response**:
```json
[
  {
    "season": "2025",
    "round": 5,
    "roster_id": 1,
    "previous_owner_id": 1,
    "owner_id": 2
  }
]
```

---

### 12. Get NFL State
Get current NFL season information.

**Endpoint**: `GET /state/nfl`

```bash
curl "https://api.sleeper.app/v1/state/nfl"
```

**Response**:
```json
{
  "week": 2,
  "season_type": "regular",
  "season_start_date": "2025-09-10",
  "season": "2025",
  "previous_season": "2024",
  "leg": 2,
  "league_season": "2026",
  "league_create_season": "2026",
  "display_week": 3
}
```

---

### 13. Get Playoff Brackets
**Endpoint**: `GET /league/<league_id>/winners_bracket`  
**Endpoint**: `GET /league/<league_id>/losers_bracket`

```bash
curl "https://api.sleeper.app/v1/league/<league_id>/winners_bracket"
```

**Response Structure**:
```json
[
  {
    "r": 1,
    "m": 1,
    "t1": 3,
    "t2": 6,
    "w": null,
    "l": null
  },
  {
    "r": 2,
    "m": 3,
    "t1": 1,
    "t2": null,
    "t2_from": {"w": 1},
    "w": null,
    "l": null
  }
]
```

**Key Fields**:
- `r`: Round number
- `m`: Match ID
- `t1`, `t2`: `roster_id` of teams (or derived from previous matches)
- `w`, `l`: Winner and loser `roster_id` (if completed)
- `t1_from`, `t2_from`: Where teams come from in bracket progression

---

### 14. Trending Players
Get trending add/drop data (optional, for context).

**Endpoint**: `GET /players/nfl/trending/<type>?lookback_hours=<hours>&limit=<int>`

```bash
curl "https://api.sleeper.app/v1/players/nfl/trending/add?lookback_hours=24&limit=25"
```

**Response**:
```json
[
  {
    "player_id": "1111",
    "count": 45
  }
]
```

---

## Data Collection Strategy for Mock Draft Agent

### Phase 1: Historical League Data
1. **Get user ID** from username
2. **Retrieve all leagues** for past 3-5 seasons
3. For each league:
   - Get league details (scoring settings, roster positions)
   - Get all rosters (to see team composition)
   - Get all users (to map roster IDs to users)

### Phase 2: Historical Draft Data
1. **Get all drafts** for each league
2. For each draft:
   - Get draft details (draft order, settings)
   - Get all draft picks (most critical data)
   - Get traded picks (if dynasty)
3. **Build draft history database**:
   - Player → Average draft position (ADP)
   - Player → Position rank when drafted
   - User → Draft tendencies (QB early/late, RB heavy, etc.)

### Phase 3: Season Performance Data
1. **Get weekly matchups** for all weeks
2. **Track player performance** across seasons:
   - Points per game
   - Consistency
   - Week-to-week variance
3. **Analyze roster decisions**:
   - Who was started vs benched
   - Correlation between draft position and season performance

### Phase 4: Transaction Data
1. **Get all transactions** for each league/season
2. **Analyze patterns**:
   - Which drafted players were dropped (busts)
   - High-value waiver pickups
   - Trade frequency and player values

### Phase 5: Player Database
1. **Fetch player data once daily**
2. **Store locally** for quick lookups
3. **Track changes** over time:
   - Team changes
   - Injury status
   - Depth chart movements

---

## Python + Temporal Implementation Architecture

### Temporal Workflow Structure

```python
# workflows/data_collection.py
@workflow.defn
class DataCollectionWorkflow:
    """Main workflow for collecting historical league data"""
    
    @workflow.run
    async def run(self, user_id: str, seasons: list[str]) -> dict:
        # Orchestrate data collection activities
        pass

@workflow.defn
class MockDraftSimulationWorkflow:
    """Workflow for running mock draft simulations"""
    
    @workflow.run
    async def run(self, league_id: str, settings: dict) -> dict:
        # Run draft simulation
        pass
```

### Activity Structure

```python
# activities/api_client.py
@activity.defn
async def fetch_user(username: str) -> dict:
    """Activity to fetch user data from Sleeper API"""
    pass

@activity.defn
async def fetch_league_drafts(league_id: str) -> list[dict]:
    """Activity to fetch all drafts for a league"""
    pass

@activity.defn
async def fetch_draft_picks(draft_id: str) -> list[dict]:
    """Activity to fetch all picks in a draft"""
    pass
```

### Recommended Python Libraries

**API & HTTP**:
- `httpx` - Modern async HTTP client
- `tenacity` - Retry logic with exponential backoff

**Data Processing**:
- `pandas` - Data analysis and manipulation
- `pydantic` - Data validation and parsing

**Storage**:
- `sqlalchemy` - ORM for database operations
- `alembic` - Database migrations

**ML/Analysis**:
- `scikit-learn` - Machine learning models
- `numpy` - Numerical computing

**Temporal**:
- `temporalio` - Temporal Python SDK

**Utilities**:
- `python-dotenv` - Environment configuration
- `loguru` - Better logging

---

## API Response Error Codes

| Code | Meaning |
|------|---------|
| 400  | Bad Request - Invalid request format |
| 404  | Not Found - Resource doesn't exist |
| 429  | Too Many Requests - Rate limit exceeded |
| 500  | Internal Server Error - Try again later |
| 503  | Service Unavailable - Maintenance mode |

---

## Avatar URLs
Users and leagues have avatars accessible via:

**Full size**: `https://sleepercdn.com/avatars/<avatar_id>`  
**Thumbnail**: `https://sleepercdn.com/avatars/thumbs/<avatar_id>`

---

## Questions for Improvement & Iteration (100 Total)

### ✅ Answered Questions (v1)
- ✅ **What API endpoints are available?** *(v1)* - Documented all major endpoints above
- ✅ **How do I get draft history?** *(v1)* - Use `/draft/<draft_id>/picks` endpoint
- ✅ **How do I map player IDs to names?** *(v1)* - Use `/players/nfl` endpoint (once daily max)
- ✅ **What's the rate limit?** *(v1)* - 1000 calls per minute
- ✅ **Is authentication required?** *(v1)* - No, API is read-only
- ✅ **What technology stack?** *(v1)* - Python + Temporal

---

### ❓ Open Questions for Future Versions

#### 1. API Data Collection Strategy (Questions 1-15)

1. **How many seasons of historical data should we collect?** 
   - Balance relevance vs. sample size
   - Consider meta changes, rule changes, scoring updates
ANSWER: all historical data per league, per player is not as important but is needed to help rank and determine the owner trends over time for drafting


2. **Should we prioritize recent seasons with different weights?**
   - Exponential decay for older seasons?
   - Hard cutoff (e.g., only last 3 years)?
ANSWER: personal league will be only the last 5 years since we will start season 6 in 2026. No decay needed, but more recent should be weighted a little heavier than first seasons

3. **How to handle leagues that changed scoring mid-history?**
   - Track scoring_settings per season
   - Normalize across different scoring systems?
ANSWER: store scoring settings per season and use that to help weight player values accordingly per season

4. **Should we collect data from multiple leagues or just one?**
   - Single league (intimate knowledge) vs aggregate data
   - How to weight league-specific vs general trends?
ANSWER: focus on the personal league primarily for intimate knowledge, but consider data from other leagues/sources for broader drafting trends

5. **What's the optimal API call batching strategy?**
   - Batch multiple requests per minute?
   - Parallel vs sequential calls?
ANSWER: batch where possible, but respect rate limits. Parallelize within limits.

6. **How to handle API rate limiting gracefully?**
   - Exponential backoff?
   - Request queuing system?
   - Circuit breaker pattern?
ANSWER:request queueing system 

7. **Should we cache API responses?**
   - Cache duration for different endpoints
   - Cache invalidation strategy
   - Storage backend (Redis, local filesystem)?
ANSWER: Cache, storage backend postgresql

8. **How to detect and handle API schema changes?**
   - Version API response schemas?
   - Automated testing against expected structure?
ANSWER: version response schemas

9. **Should we track keeper league data separately?**
   - `is_keeper` field in picks
   - How do keepers skew ADP?
ANSWER: track separately, adjust ADP calculations accordingly

10. **How to handle dynasty league continuity?**
    - Track via `previous_league_id`
    - Handle roster carryover effects
ANSWER: track, but this is not needed for the personal league

11. **Do we need historical transaction data?**
    - Waiver wire patterns
    - Trade frequency and player values
    - Dropped players = draft busts?
ANSWER: yes, to help better identify booms/busts and successful pickups. FA/waiver wire pickups can be kept for 15th pick (last pick in draft)

12. **Should we collect matchup/weekly scoring data?**
    - Season-long performance validation
    - Correlation between draft position and final rank
ANSWER: yes, to help validate draft pick values and player performance over season

13. **How to handle incomplete historical data?**
    - Missing weeks, incomplete rosters
    - Skip or impute missing data?
ANSWER: skip incomplete data for accuracy

14. **Should we store raw API responses or processed data?**
    - Reproducibility vs storage efficiency
    - Data warehouse vs operational database?
ANSWER: store processed data for efficiency, raw responses for critical endpoints only

15. **How frequently should we refresh player database?**
    - Daily during season?
    - Weekly in offseason?
    - Event-driven (trades, injuries)?
ANSWER: all of the above except weekly during both season and offseason
---

#### 2. Python Implementation (Questions 16-30)

16. **Which HTTP library for API calls?**
    - `requests`, `httpx`, `aiohttp`?
    - Async vs sync implementation?
ANSWER: requests, async 

17. **What Python version should we target?**
    - 3.10+, 3.11+, 3.12+?
    - Type hints and modern features?
ANSWER: most modern stable version  

18. **How to structure the Python project?**
    - Monorepo vs separate packages?
    - Directory structure (src layout vs flat)?
ANSWER: src layout with clear separation of workflows, activities, models, utils

19. **Should we use Pydantic for data validation?**
    - Type-safe API response parsing
    - Automatic validation and serialization
ANSWER: maybe in the future, performance tradeoffs to consider. not needed for intial implementation

20. **What data processing libraries?**
    - pandas for analysis?
    - polars for performance?
    - Raw Python data structures?
ANSWER: pandas for analysis, raw python data structures for lightweight operations

21. **How to handle player ID mapping efficiently?**
    - In-memory dictionary?
    - SQLite lookup?
    - Redis cache?
ANSWER: either in-memory dictionary or postgresql lookup depending on size of data

22. **Should we use async/await for API calls?**
    - `asyncio` with `aiohttp`
    - Performance benefits vs complexity
ANSWER: yes, for performance benefits
    
23. **What logging strategy?**
    - `logging` module configuration
    - Structured logging (JSON)?
    - Log levels and rotation
ANSWER: structured logging as a start
    
24. **How to handle environment configuration?**
    - `.env` files with `python-dotenv`?
    - Config classes?
    - Environment-specific settings
ANSWER: use `.env` files with `python-dotenv` for simplicity

25. **What testing framework?**
    - `pytest` for unit tests?
    - `pytest-asyncio` for async tests?
    - Mock API responses or use VCR.py?
ANSWER: not sure, whichever is best and most efficient

26. **Should we use dataclasses or Pydantic models?**
    - Performance vs validation tradeoffs
    - Serialization requirements
ANSWER: dataclasses

27. **How to handle timezone conversions?**
    - Draft timestamps in UTC?
    - Local time display?
    - Use `pendulum` or `arrow`?
ANSWER: nice to have localization, UTC for initial implementation

28. **What dependency management?**
    - Poetry, pip-tools, PDM?
    - Lock file strategy
ANSWER: not sure, which would be best if any is needed?

29. **Should we implement retry logic?**
    - `tenacity` library?
    - Custom retry decorator?
    - Temporal's built-in retries?
ANSWER: not right now, Temporal's built-in retries should suffice for now

30. **Code quality tools?**
    - Black, ruff, mypy?
    - Pre-commit hooks?
    - CI/CD integration?
ANSWER: yes to all needed for this personal project, code quality is important
---

#### 3. Temporal Workflow Design (Questions 31-45)

31. **How to structure Temporal workflows?**
    - Separate workflows for data collection, analysis, simulation?
    - Parent-child workflow relationships?
ANSWER: separate workflows for each major phase, parent-child relationships where needed. Child workflows can be used for specific data collection tasks

32. **What should be workflows vs activities?**
    - Workflow: orchestration logic
    - Activity: API calls, DB operations, calculations?
ANSWER: yes, keep orchestration in workflows and all external calls or internal operations/code in activities

33. **How to handle long-running data collection?**
    - Temporal's durable execution
    - Continue-as-new for large datasets?
ANSWER: continue-as-new for large datasets to avoid timeouts

34. **Should data collection be a scheduled workflow?**
    - Daily player updates
    - Weekly league sync
    - Cron schedule configuration
ANSWER: yes, scheduled workflows for weekly league syncs, player updates during the season. The offseason can be event-driven (injury, trade, FA signing)

35. **How to handle workflow versioning?**
    - Temporal's versioning support
    - Backward compatibility strategy
ANSWER: use Temporal's versioning support, ensure backward compatibility where possible

36. **What activity timeout settings?**
    - Start-to-close timeout for API calls
    - Heartbeat timeout for long operations
    - Retry policy configuration
ANSWER: configure timeouts based on expected operation duration, use retries with exponential backoff

37. **Should we use Temporal signals?**
    - Pause/resume data collection
    - Update configuration mid-workflow
    - Trigger mock drafts
ANSWER: yes, use Temporal signals for pause/resume, configuration updates, and triggering mock drafts

38. **How to handle workflow failures?**
    - Automatic retry with backoff
    - Manual intervention points
    - Dead letter queue for failed activities
ANSWER: automatic retry with backoff, dead queue for failed activities for debug

39. **Should we use Temporal queries?**
    - Get current workflow state
    - Progress reporting
    - Real-time status updates
ANSWER: yes, use Temporal queries for real-time status updates and progress reporting

40. **How to organize workflow code?**
    - Separate files per workflow type
    - Shared activities module
    - Type hints for workflow parameters
ANSWER: separate files per workflow type, shared activities module, use type hints for clarity

41. **What's the workflow execution order?**
    - Data collection → Analysis → Model training → Simulation?
    - Parallel execution where possible?
ANSWER: data collection → analysis → model training → simulation, parallel execution where possible to speed up data collection

42. **Should mock draft be a separate workflow?**
    - Triggered on-demand
    - Inputs: league_id, draft settings, user overrides
    ANSWER: yes, separate workflow for mock draft simulation, triggered on-demand with necessary inputs (sleeper user creds, that user's league_id, draft settings, etc.)

43. **How to pass large data between activities?**
    - Temporal's 2MB payload limit
    - Use database IDs instead of full objects
    - External storage references?
ANSWER: use database IDs instead of full objects to stay within limits

44. **Should we use Temporal's search attributes?**
    - Index by league_id, season, workflow type
    - Enable filtering and querying workflows
ANSWER: yes, use search attributes for better workflow management and querying

45. **How to monitor workflow performance?**
    - Temporal Web UI
    - Custom metrics export
    - OpenTelemetry integration?
ANSWER: yes, use Temporal Web UI for monitoring, consider custom metrics export for deeper insights in the future
---

#### 4. Data Storage & Schema (Questions 46-55)

46. **Which database should we use?**
    - PostgreSQL for relational data?
    - MongoDB for flexible schema?
    - SQLite for simplicity?
ANSWER: PostgreSQL for relational data and robustness

47. **How to structure the database schema?**
    - Tables: users, leagues, drafts, picks, players, rosters?
    - Normalization level?
ANSWER: leagues, drafts, picks, players, rosters, league_owner, transactions tables. Normalize to 3NF for data integrity

48. **Should we use an ORM?**
    - SQLAlchemy for PostgreSQL?
    - Peewee for SQLite?
    - Raw SQL for performance?
ANSWER: unsure, probably sqlaclhemy for ease of use and flexibility

49. **How to handle schema migrations?**
    - Alembic for SQLAlchemy?
    - Version control migrations?
ANSWER: version control migrations with git

50. **Should we denormalize for performance?**
    - Pre-calculate ADP tables?
    - Materialized views?
ANSWER: pre-calculate ADP tables for faster lookups

51. **How to store player data efficiently?**
    - Full player object vs just IDs?
    - Historical snapshots vs current state?
ANSWER: store full player object for critical fields, IDs for references. Historical snapshots for draft time data

52. **Should we use time-series database for matchups?**
    - Weekly scoring data
    - InfluxDB, TimescaleDB?
ANSWER: no, use PostgreSQL with time-series optimizations if needed

53. **How to handle draft pick storage?**
    - One row per pick?
    - Include metadata snapshot?
ANSWER: one row per pick with metadata snapshot for draft-time player info to use for owner trend analysis

54. **Should we store raw API responses?**
    - Audit trail and debugging
    - Replay capability
    - JSONB columns in PostgreSQL?
ANSWER: not needed now

55. **How to implement full-text search?**
    - Player name search
    - PostgreSQL GIN index?
    - Elasticsearch?
ANSWER: PostgreSQL GIN index for player name search for simplicity

---

#### 5. Machine Learning & Analysis (Questions 56-70)

56. **What ML framework should we use?**
    - scikit-learn for traditional ML?
    - TensorFlow/PyTorch for deep learning?
    - LightGBM/XGBoost for gradient boosting?
ANSWER: TensorFlow/PyTorch for deep learning if needed, TemporalAI otherwise

57. **How to frame the prediction problem?**
    - Classification: which player will be picked?
    - Ranking: order players by likelihood?
    - Regression: predict pick number?
ANSWER: ranking problem to order players by likelihood of being picked by that specific owner at that pick

58. **What features should we extract?**
    - Player: position, ADP, projection, injury history
    - Drafter: past picks, position preferences, risk profile
    - Context: round, pick number, remaining positions
ANSWER: all of the above, plus team needs based on roster construction

59. **How to encode categorical features?**
    - One-hot encoding for positions?
    - Label encoding for ordinal data?
    - Embeddings for high-cardinality features?
ANSWER: embeddings for high-cardinality features, one-hot for positions

60. **Should we build separate models per league?**
    - League-specific vs generalized model
    - Transfer learning possible?
ANSWER: league-specific model, app should be from user/owner's perspective 

61. **How to handle class imbalance?**
    - Many players, few picks per round
    - SMOTE, class weights, focal loss?
ANSWER: class weights or focal loss to handle imbalance

62. **What's the train/test split strategy?**
    - Temporal split (early seasons train, recent test)?
    - Leave-one-draft-out cross-validation?
ANSWER: temporal split to respect time series nature of data

63. **How to calculate Average Draft Position (ADP)?**
    - Simple mean?
    - Weighted by recency?
    - Confidence intervals?
ANSWER: weighted by recency to reflect current drafting trends

64. **Should we model positional runs?**
    - Detect when position starts getting drafted heavily
    - Separate model or feature?
ANSWER: feature to detect positional runs

65. **How to model draft position effects?**
    - Early picks = RB heavy?
    - Late picks = WR heavy?
    - Positional value by draft slot?
ANSWER: feature to model positional value by draft slot, personalized for each owner after analysis

66. **Should we use ensemble methods?**
    - Combine multiple model predictions
    - Voting, stacking, blending?
ANSWER: unsure, blending to improve accuracy

67. **How to incorporate expert rankings?**
    - Blend with ADP?
    - Use as feature?
    - Weight expert vs historical?
ANSWER: as secondary, main focus should be historical data for the user from that specific league

68. **How to measure model performance?**
    - Accuracy, precision, recall?
    - Mean absolute error for pick number?
    - Custom metric (% predicted in round)?
ANSWER: custom metric (% predicted in round) to reflect draft pick accuracy for that specific user at that specific draft position

69. **Should we implement online learning?**
    - Update model as new drafts complete
    - Incremental training
ANSWER: no, retrain periodically after new draft data is collected

70. **How to handle rookies without history?**
    - Expert consensus?
    - College statistics?
    - Draft capital (NFL draft position)?
ANSWER: expert consensus and draft capital primarily, no college stats (except for rookies)

---

#### 6. User Profiling & Behavior (Questions 71-78)

71. **What drafter archetypes should we identify?**
    - Value drafter, position-focused, homer, contrarian?
    - Clustering algorithm?
ANSWER: k-means clustering to identify drafter archetypes based on historical draft behavior

72. **How to quantify draft position adaptation?**
    - Early vs late draft strategy differences
    - Positional preference by draft slot
ANSWER: analyze historical picks by draft slot to identify patterns, analyze if the owner adjusts strategy based on draft position/needs

73. **Should we track reach/value metrics per user?**
    - How often they reach for need
    - How often they take BPA (best player available)
ANSWER: yes, track reach/value metrics to better understand drafting tendencies

74. **How to detect homer bias?**
    - Players from favorite NFL team
    - Same college affiliation
ANSWER: bias is definitely present for homer picks, track frequency of picks compared to league average to identify

75. **Should we model risk tolerance?**
    - Injury-prone players
    - Rookie draft picks
    - Suspended players
ANSWER: model risk tolerance by tracking frequency of high-risk picks and their outcomes

76. **How to handle first-time league members?**
    - No historical data
    - Use league average profile?
    - Most conservative strategy?
ANSWER: use league average profile as a starting point, adjust as more data is collected

77. **Should we track handcuff drafting patterns?**
    - Backup RBs to starters
    - Late-round strategy
ANSWER: track frequency of handcuff picks relative to starters, analyze success rate and timing

78. **How to weight recent vs old user behavior?**
    - People learn and adapt
    - Recency bias in weighting
ANSWER: apply exponential decay weighting to historical data to emphasize recent behavior, include recency bias

---

#### 7. Mock Draft Simulation (Questions 79-85)

79. **How to initialize mock draft state?**
    - Load league settings
    - Load drafter profiles
    - Current player pool
ANSWER: all of the above to accurately reflect the draft environment

80. **Should simulation be deterministic or probabilistic?**
    - Single prediction per pick
    - Monte Carlo simulation with multiple outcomes
ANSWER: Monte Carlo simulation for better probability distribution of likely picks

81. **How many mock drafts should we run?**
    - Single run vs 100+ for probability distribution
    - Computational cost vs accuracy
ANSWER: at least 1000 simulations to get a good probability distribution of likely picks

82. **How to handle user override inputs?**
    - "Force pick X for user Y in round Z"
    - Adjust downstream predictions accordingly
ANSWER: allow user overrides to simulate specific scenarios (such as setting the owner's 2 keepers), adjust downstream predictions based on forced picks

83. **Should we show alternative scenarios?**
    - "If Player X is taken, then..."
    - Decision tree visualization
ANSWER: only for top 3 likely picks per slot, not full decision tree to avoid complexity

84. **How to present pick probabilities?**
    - Top 5 likely picks per slot
    - Percentage likelihood
    - Heat map visualization
ANSWER: display top 5 likely picks with their percentage likelihoods, heat map for visual emphasis is nice to have

85. **Should we allow real-time simulation during live drafts?**
    - Re-run after each actual pick
    - Adjust strategy recommendations
ANSWER: nice to have, but not critical for initial implementation. Can be considered for future versions

---

#### 8. User Interface & Experience (Questions 86-92)

86. **What's the primary user interface?**
    - CLI tool for power users?
    - Web dashboard for accessibility?
    - Desktop app?
ANSWER: Temporal web dashboard for accessibility and ease of use, eventually can be api for users/other owners to access

87. **Should we build a web API?**
    - FastAPI for REST endpoints
    - GraphQL?
    - WebSocket for real-time updates?
ANSWER: FastAPI for REST endpoints

88. **What frontend framework if web-based?**
    - React, Vue, Svelte?
    - Server-side rendering?
    - Static site?
ANSWER: do not worry about front end for now, focus on backend and Temporal workflows

89. **How to visualize draft boards?**
    - Grid layout with snake order
    - Player cards with metadata
    - Color coding by position
ANSWER: do not worry about front end for now, focus on backend and Temporal workflows

90. **Should we provide draft recommendations?**
    - "Best available player"
    - "Best value pick"
    - "Fill positional need"
ANSWER: yes, provide top 3 best available players and top 3 best value pick recommendations based on simulation results

91. **How to display ADP and rankings?**
    - Compare league ADP vs expert ADP
    - Highlight value discrepancies
ANSWER: do not worry about front end for now, focus on backend and Temporal workflows\

92. **Should we allow configuration exports?**
    - Save mock draft results
    - Export to CSV/JSON
    - Share with league members?
ANSWER: export to CSV/JSON for personal analysis, sharing is nice to have but not critical for initial implementation
---

#### 9. Testing, Validation & Performance (Questions 93-100)

93. **What's our test coverage target?**
    - Unit tests for all functions?
    - Integration tests for workflows?
    - End-to-end tests for full pipeline?
ANSWER: aim for at least 80% coverage, focus on unit tests for critical functions and integration tests for workflows. This can be in the future

94. **How to validate mock draft accuracy?**
    - Predict completed draft
    - Compare to actual results
    - What accuracy is "good enough"?
ANSWER: compare predicted draft to actual results, aim for at least 60-75% accuracy in predicting picks within the correct round

95. **Should we implement benchmarking?**
    - Compare to random baseline
    - Compare to ADP-only strategy
    - Compare to expert consensus
ANSWER: not right now

96. **How to optimize API call performance?**
    - Async concurrent requests
    - Request pooling
    - Connection reuse
ANSWER: async concurrent requests with connection reuse for efficiency

97. **What's acceptable mock draft generation time?**
    - < 1 second for single simulation?
    - < 30 seconds for 100 simulations?
ANSWER: < 1 minute for 1000 simulations, ideally faster

98. **Should we implement caching for simulations?**
    - Cache common scenarios
    - Cache invalidation strategy
ANSWER: cache common scenarios to speed up repeated simulations. Example (highest rated players tend to go first round "sure-bets", owner picks tend to be similar across drafts, etc.)

99. **How to monitor production performance?**
    - Application metrics (latency, throughput)
    - Error rates and alerts
    - Cost tracking (API calls, compute)
ANSWER: Use Temporal Web UI for workflow monitoring

100. **What's the deployment strategy?**
     - Docker containers?
     - Cloud platform (AWS, GCP, Azure)?
     - Self-hosted vs managed services?
     - CI/CD pipeline setup?
ANSWER: Docker containers for easy deployment, self-hosted Temporal server for control
---

## Next Steps

1. **Answer Key Questions**: Start with questions 1-15 (data collection) and 31-45 (Temporal design)
2. **Set Up Development Environment**: Python virtual environment, Temporal server
3. **Build MVP**: Simple data collection workflow
4. **Iterate**: Add analysis and simulation capabilities
5. **Test**: Validate against historical drafts
6. **Deploy**: Production-ready system

---

*Last Updated: v1 - January 27, 2026*
