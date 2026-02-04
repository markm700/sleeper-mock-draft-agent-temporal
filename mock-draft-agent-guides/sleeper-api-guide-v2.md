# Sleeper API Guide for Mock Draft Agent (v2)
*Created: January 27, 2026*  
*Updated: January 27, 2026*  
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
- `requests` - HTTP client for API calls (async implementation)
- `tenacity` - Retry logic with exponential backoff (if needed beyond Temporal retries)

**Data Processing**:
- `pandas` - Data analysis and manipulation
- Raw Python data structures for lightweight operations

**Storage**:
- `sqlalchemy` - ORM for PostgreSQL operations
- `alembic` - Database migrations

**ML/Analysis**:
- `tensorflow` or `pytorch` - Deep learning if needed, otherwise TemporalAI
- `scikit-learn` - Traditional ML models
- `numpy` - Numerical computing

**Temporal**:
- `temporalio` - Temporal Python SDK

**Utilities**:
- `python-dotenv` - Environment configuration
- Standard `logging` module with structured logging

**Code Quality**:
- `black` - Code formatting
- `ruff` - Fast Python linter
- `mypy` - Static type checking
- Pre-commit hooks for automated checks

---

## Implementation Specifications (v2)

### ✅ Answered Questions (v2): 100/100

## Project Structure

```
sleeper-mock-draft-agent-temporal/
├── src/
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── data_collection.py
│   │   ├── analysis.py
│   │   └── mock_draft_simulation.py
│   ├── activities/
│   │   ├── __init__.py
│   │   ├── api_client.py
│   │   ├── database.py
│   │   └── ml_models.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database_models.py
│   │   └── api_models.py
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       └── logging.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── migrations/
│   └── versions/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── requirements.txt
```

---

## Database Schema (PostgreSQL)

### Core Tables

```sql
-- Leagues table
CREATE TABLE leagues (
    league_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    season VARCHAR(10),
    status VARCHAR(50),
    total_rosters INTEGER,
    scoring_settings JSONB,
    roster_positions JSONB,
    settings JSONB,
    previous_league_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- League owners/users
CREATE TABLE league_owners (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    username VARCHAR(255),
    display_name VARCHAR(255),
    league_id VARCHAR(50) REFERENCES leagues(league_id),
    is_owner BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Drafts table
CREATE TABLE drafts (
    draft_id VARCHAR(50) PRIMARY KEY,
    league_id VARCHAR(50) REFERENCES leagues(league_id),
    type VARCHAR(50),
    status VARCHAR(50),
    start_time BIGINT,
    season VARCHAR(10),
    settings JSONB,
    metadata JSONB,
    draft_order JSONB,
    slot_to_roster_id JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Draft picks table
CREATE TABLE picks (
    id SERIAL PRIMARY KEY,
    pick_no INTEGER NOT NULL,
    draft_id VARCHAR(50) REFERENCES drafts(draft_id),
    player_id VARCHAR(50) NOT NULL,
    picked_by VARCHAR(50),
    roster_id VARCHAR(50),
    round INTEGER,
    draft_slot INTEGER,
    is_keeper BOOLEAN,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(draft_id, pick_no)
);

-- Players table
CREATE TABLE players (
    player_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    position VARCHAR(10),
    team VARCHAR(10),
    fantasy_positions JSONB,
    depth_chart_position INTEGER,
    status VARCHAR(50),
    injury_status VARCHAR(255),
    search_rank INTEGER,
    metadata JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Rosters table
CREATE TABLE rosters (
    id SERIAL PRIMARY KEY,
    roster_id INTEGER NOT NULL,
    league_id VARCHAR(50) REFERENCES leagues(league_id),
    owner_id VARCHAR(50),
    players JSONB,
    starters JSONB,
    settings JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(league_id, roster_id)
);

-- Transactions table
CREATE TABLE transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    league_id VARCHAR(50) REFERENCES leagues(league_id),
    type VARCHAR(50),
    status VARCHAR(50),
    leg INTEGER,
    roster_ids JSONB,
    adds JSONB,
    drops JSONB,
    draft_picks JSONB,
    settings JSONB,
    created BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pre-calculated ADP table for performance
CREATE TABLE adp_cache (
    id SERIAL PRIMARY KEY,
    league_id VARCHAR(50),
    player_id VARCHAR(50),
    season VARCHAR(10),
    avg_pick DECIMAL(5,2),
    std_dev DECIMAL(5,2),
    sample_size INTEGER,
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(league_id, player_id, season)
);

-- Indexes for performance
CREATE INDEX idx_picks_draft_id ON picks(draft_id);
CREATE INDEX idx_picks_player_id ON picks(player_id);
CREATE INDEX idx_drafts_league_id ON drafts(league_id);
CREATE INDEX idx_drafts_season ON drafts(season);
CREATE INDEX idx_rosters_league_id ON rosters(league_id);
CREATE INDEX idx_transactions_league_id ON transactions(league_id);
CREATE INDEX idx_players_position ON players(position);
CREATE INDEX idx_players_team ON players(team);
CREATE INDEX idx_adp_league_season ON adp_cache(league_id, season);

-- Full-text search on player names
CREATE INDEX idx_players_name_gin ON players 
USING gin(to_tsvector('english', first_name || ' ' || last_name));
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- ✅ Set up project structure
- ✅ Configure Python environment (modern stable version)
- ✅ Set up PostgreSQL database
- ✅ Initialize Temporal server (Docker)
- ✅ Create database schema with migrations (Alembic)
- ✅ Set up environment configuration (.env)
- ✅ Configure code quality tools (Black, ruff, mypy)

### Phase 2: Data Collection (Weeks 3-4)
- Implement Sleeper API client activities (async with requests)
- Build data collection workflows
  - User/league discovery
  - Historical draft data collection (last 5 years)
  - Player database sync (daily scheduled)
  - Transaction history collection
  - Weekly matchup data collection
- Implement request queuing for rate limiting
- Set up caching in PostgreSQL
- Test with personal league data

### Phase 3: Data Processing & Storage (Week 5)
- Implement database operations with SQLAlchemy
- Build data transformation activities
- Calculate and store ADP (weighted by recency)
- Process keeper data separately
- Handle scoring_settings per season
- Implement player ID mapping (PostgreSQL lookup)

### Phase 4: Analysis & User Profiling (Weeks 6-7)
- Build owner profiling workflows
  - K-means clustering for archetypes
  - Draft position adaptation analysis
  - Reach/value metrics calculation
  - Homer bias detection
  - Risk tolerance modeling
  - Handcuff pattern tracking
- Apply exponential decay to historical behavior
- Identify positional run patterns
- Calculate team needs based on roster construction

### Phase 5: ML Model Development (Weeks 8-10)
- Frame prediction as ranking problem
- Feature engineering
  - Player features (position, ADP, injury history)
  - Drafter features (past picks, preferences, risk profile)
  - Context features (round, pick, remaining positions, team needs)
- Implement categorical encoding (embeddings, one-hot)
- Build league-specific models (TensorFlow/PyTorch or TemporalAI)
- Handle class imbalance (class weights/focal loss)
- Temporal split for train/test
- Model evaluation (% predicted in correct round)
- Track performance for 60-75% accuracy target

### Phase 6: Mock Draft Simulation (Weeks 11-12)
- Build mock draft simulation workflow
- Implement Monte Carlo simulation (1000+ iterations)
- Support user overrides (e.g., keeper selections)
- Calculate pick probabilities
- Generate top 3 best available + top 3 best value recommendations
- Export results to CSV/JSON
- Optimize for < 1 minute runtime
- Cache common scenarios

### Phase 7: API & Integration (Week 13)
- Build FastAPI REST endpoints
- Implement Temporal signals for triggers
- Use Temporal queries for status updates
- Configure workflow scheduling
  - Weekly league sync
  - Daily player updates (season)
  - Event-driven offseason updates
- Set up Temporal search attributes

### Phase 8: Monitoring & Deployment (Week 14)
- Configure Temporal Web UI monitoring
- Implement structured logging
- Set up dead letter queue for failed activities
- Create Docker containers
- Configure self-hosted Temporal server
- Deploy to production environment
- Test end-to-end workflow

### Phase 9: Testing & Validation (Week 15)
- Unit tests for critical functions (pytest)
- Integration tests for workflows
- Validate against historical drafts
- Measure accuracy (60-75% target)
- Test with incomplete data scenarios
- Performance optimization

### Phase 10: Future Enhancements (Post-MVP)
- 80% test coverage
- Frontend development (React/Vue)
- Real-time draft simulation during live drafts
- Expert rankings integration (secondary)
- Advanced visualizations (heat maps, draft boards)
- Multi-league support
- Benchmarking against ADP/expert consensus
- Custom metrics export

---

## Key Dependencies

```toml
# pyproject.toml or requirements.txt
[tool.poetry.dependencies]
python = "^3.12"
temporalio = "^1.5.0"
requests = "^2.31.0"
sqlalchemy = "^2.0.0"
alembic = "^1.13.0"
psycopg2-binary = "^2.9.0"
pandas = "^2.1.0"
numpy = "^1.26.0"
python-dotenv = "^1.0.0"
tensorflow = "^2.15.0"  # or pytorch
scikit-learn = "^1.3.0"

[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
black = "^23.12.0"
ruff = "^0.1.9"
mypy = "^1.7.0"
pre-commit = "^3.6.0"
```

---

## Next Steps

1. ✅ **Complete specification** - All 100 questions answered in v2
2. **Initialize project structure** - Set up directories and files
3. **Configure development environment** - Python, PostgreSQL, Temporal, Docker
4. **Begin Phase 1** - Foundation setup
5. **Start data collection** - Connect to Sleeper API and collect league history
6. **Build iteratively** - Follow roadmap phases

---

## Success Metrics

- **Data Collection**: Successfully collect 5 years of league history
- **Model Accuracy**: 60-75% of picks predicted in correct round
- **Performance**: < 1 minute for 1000 mock draft simulations
- **Reliability**: Workflows handle failures gracefully with retries
- **Code Quality**: Pass all linting/type checks, 80% test coverage (future)
- **User Value**: Provide actionable draft recommendations

---

*Last Updated: v2 - January 27, 2026*  
*Status: Complete specification with all 100 questions answered*
