# Database Schema Overview

Quick reference for the Sleeper Mock Draft Agent database schema.

## Tables

| Table | Primary Key | Description | Key Relationships |
|-------|-------------|-------------|-------------------|
| **users** | `user_id` (varchar 50) | Sleeper users (team owners) | → team_owners, rosters, draft_picks |
| **leagues** | `league_id` (varchar 50) | Fantasy leagues | → team_owners, rosters, drafts, traded_draft_picks |
| **team_owners** | `id` (serial) | User participation in leagues | ← users, leagues |
| **rosters** | `id` (serial) | Team rosters in leagues | ← users (owner), leagues |
| **drafts** | `draft_id` (varchar 50) | Draft events | ← leagues, → draft_picks |
| **draft_picks** | `pick_id` (serial) | Individual draft picks | ← drafts, users (picked_by), players |
| **traded_draft_picks** | `traded_pick_id` (serial) | Traded future picks | ← leagues |
| **players** | `player_id` (varchar 50) | NFL players (optional) | Referenced by rosters, draft_picks |

## Key Field Types

### JSONB Fields (Semi-Structured Data)
- `League.scoring_settings` - Scoring rules (pass_yd, rec, rush_td, etc.)
- `League.roster_positions` - Array of position slots: `["QB", "RB", "WR", ...]`
- `League.league_settings` - League configuration (num_teams, playoff_teams, etc.)
- `League.metadata` - Additional league data (divisions, keeper settings, etc.)
- `Roster.players` - Array of player_ids on roster
- `Roster.starters` - Array of starting player_ids
- `Roster.reserve` - Array of IR/reserve player_ids
- `Roster.roster_settings` - Team stats (wins, losses, points_for, etc.)
- `Draft.draft_settings` - Draft configuration
- `DraftPick.metadata` - Pick metadata (position, team, amount, etc.)

### Array Fields
- `Roster.co_owners` - ARRAY(String) of co-owner user_ids

## Unique Constraints

| Table | Constraint | Fields |
|-------|------------|--------|
| users | username unique | `username` |
| team_owners | uq_league_user | `(league_id, user_id)` |
| rosters | uq_league_roster | `(league_id, roster_id)` |
| draft_picks | uq_draft_pick_no | `(draft_id, pick_no)` |
| traded_draft_picks | uq_traded_pick | `(league_id, season, round, roster_id)` |

## Key Indexes

### User Queries
- `users.username` (unique)
- `users.display_name`

### League Queries
- `leagues.season`
- `leagues.status`
- `leagues.name`
- `leagues.draft_id`
- `(season, name)` composite

### Roster Queries
- `rosters.league_id`
- `rosters.owner_id`
- `(league_id, roster_id)` composite

### Draft Queries
- `drafts.league_id`
- `drafts.status`
- `drafts.season`
- `(league_id, season)` composite

### Draft Pick Queries
- `draft_picks.draft_id`
- `draft_picks.player_id`
- `draft_picks.roster_id`
- `draft_picks.round`
- `draft_picks.picked_by`
- `(draft_id, pick_no)` composite

### Traded Pick Queries
- `traded_draft_picks.league_id`
- `traded_draft_picks.season`
- `traded_draft_picks.owner_id`
- `(league_id, season)` composite

### Player Queries (Optional Table)
- `players.full_name`
- `players.position`
- `players.team`
- `players.status`
- `(position, team)` composite

## Relationships

```
User (1) ─────< TeamOwner (N) >───── (1) League
  │                                      │
  │                                      ├─────< Roster (N)
  │                                      │
  └──────────────────────────────────────┘ (owner_id, nullable)
  │
  │
  └───────< DraftPick (N) ─────> Player (N) (nullable)
                │
                └─────< Draft (1) ─────< League (1)
  
League (1) ──────< TradedDraftPick (N)
```

## Common Query Patterns

### 1. Get all leagues for a user in a season
```sql
SELECT l.* 
FROM leagues l
JOIN team_owners to ON l.league_id = to.league_id
WHERE to.user_id = ? AND l.season = ?
```

### 2. Get all rosters owned by a user
```sql
SELECT * FROM rosters WHERE owner_id = ?
```

### 3. Get all draft picks for a draft, ordered
```sql
SELECT * FROM draft_picks 
WHERE draft_id = ? 
ORDER BY pick_no
```

### 4. Find rosters containing a specific player
```sql
SELECT * FROM rosters 
WHERE players @> '["player_id"]'::jsonb
```

### 5. Get league with scoring settings
```sql
SELECT league_id, name, scoring_settings->>'pass_yd' as pass_yd_points
FROM leagues 
WHERE league_id = ?
```

### 6. Get all trades for a league in a season
```sql
SELECT * FROM traded_draft_picks 
WHERE league_id = ? AND season = ?
```

### 7. Get league standings
```sql
SELECT r.roster_id, r.owner_id, u.username,
       (r.roster_settings->>'wins')::int as wins,
       (r.roster_settings->>'losses')::int as losses,
       (r.roster_settings->>'points_for')::float as points_for
FROM rosters r
LEFT JOIN users u ON r.owner_id = u.user_id
WHERE r.league_id = ?
ORDER BY (r.roster_settings->>'wins')::int DESC
```

## Foreign Key Cascade Rules

| Parent Table | Child Table | FK Column | On Delete |
|--------------|-------------|-----------|-----------|
| leagues | team_owners | league_id | CASCADE |
| users | team_owners | user_id | CASCADE |
| leagues | rosters | league_id | CASCADE |
| users | rosters | owner_id | SET NULL |
| leagues | drafts | league_id | CASCADE |
| drafts | leagues | draft_id | SET NULL |
| drafts | draft_picks | draft_id | CASCADE |
| users | draft_picks | picked_by | SET NULL |
| players | draft_picks | player_id | SET NULL |
| leagues | traded_draft_picks | league_id | CASCADE |

## Timestamps

All tables include:
- `created_at` - Record creation timestamp (UTC)
- `updated_at` - Last update timestamp (UTC, auto-updated)

Sleeper API timestamps are stored as integers (Unix milliseconds) to preserve original format.

## JSONB Query Examples

### Accessing nested JSONB fields
```sql
-- Get league playoff settings
SELECT name, league_settings->>'playoff_teams' as playoff_teams
FROM leagues;

-- Filter by JSONB field
SELECT * FROM leagues 
WHERE (league_settings->>'num_teams')::int = 10;

-- Check if JSONB contains a key
SELECT * FROM leagues 
WHERE metadata ? 'division_1';

-- Array containment in JSONB
SELECT * FROM rosters 
WHERE players @> '["6797"]'::jsonb;
```

### Creating GIN indexes for JSONB queries
```sql
-- For frequent queries on scoring_settings
CREATE INDEX idx_league_scoring_gin ON leagues USING GIN (scoring_settings);

-- For frequent queries on roster players
CREATE INDEX idx_roster_players_gin ON rosters USING GIN (players);
```

## Storage Estimates

Based on typical Sleeper league data:

| Table | Rows per League | Est. Size per Row | Notes |
|-------|-----------------|-------------------|-------|
| users | ~10-12 | 1 KB | Users shared across leagues |
| leagues | 1 | 5-10 KB | JSONB scoring_settings is large |
| team_owners | 10-12 | 0.5 KB | Junction table |
| rosters | 10-12 | 2-5 KB | JSONB arrays of player_ids |
| drafts | 1-3 | 2 KB | Rookie + startup drafts |
| draft_picks | 150-300 | 0.5 KB | Depends on roster depth |
| traded_draft_picks | 5-20 | 0.3 KB | Varies by league activity |

**Total per league**: ~500 KB - 2 MB  
**Total for 100 leagues**: ~50-200 MB

## Import and Usage

```python
from schema.database_models import (
    Base,
    User,
    League,
    TeamOwner,
    Roster,
    Draft,
    DraftPick,
    TradedDraftPick,
    Player,  # optional
)

# Create all tables
from sqlalchemy import create_engine
engine = create_engine("postgresql://user:pass@localhost/db")
Base.metadata.create_all(engine)

# Use in activities
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)
session = Session()

# Insert user
user = User(user_id="123", username="markm700", display_name="Mark")
session.add(user)
session.commit()
```

## Next Steps

1. Create database activities in `src/activities/database/`
2. Set up Alembic for migrations
3. Integrate database persistence in workflows
4. Add indexes for performance optimization based on query patterns
5. Consider adding materialized views for complex aggregations
