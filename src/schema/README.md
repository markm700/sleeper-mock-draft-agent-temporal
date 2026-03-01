# Database Schema for Sleeper Mock Draft Agent

This directory contains the SQLAlchemy ORM models for storing Sleeper fantasy football data collected via Temporal workflows.

## Overview

The schema is designed to store data from the Sleeper API in a normalized PostgreSQL database with proper relationships and indexes for efficient querying.

## Database Models

### Core Entities

#### 1. **User** (Team Owner)
- **Table**: `users`
- **Primary Key**: `user_id` (Sleeper user_id)
- **Purpose**: Represents a Sleeper user who owns teams across multiple leagues
- **Key Fields**:
  - `username` (unique, indexed)
  - `display_name`
  - `is_bot`
  - `metadata` (JSONB)
- **Relationships**:
  - One-to-many with `TeamOwner` (team_owners: user participates in multiple leagues)
  - One-to-many with `Roster` (rosters: user owns multiple rosters)
  - One-to-many with `DraftPick` (picks_made: picks made by this user)

#### 2. **League**
- **Table**: `leagues`
- **Primary Key**: `league_id` (Sleeper league_id)
- **Purpose**: Represents a fantasy football league
- **Key Fields**:
  - `name` (indexed)
  - `season` (indexed, e.g., "2025")
  - `status` (indexed: pre_draft, drafting, in_season, complete)
  - `sport` (default: "nfl")
  - `draft_id` (indexed, FK to drafts)
  - `roster_positions` (JSONB array: ["QB", "RB", "RB", "WR", ...])
  - `scoring_settings` (JSONB: pass_yd: 0.04, rec: 1, rush_td: 6, ...)
  - `league_settings` (JSONB: num_teams, playoff_teams, waiver_type, ...)
  - `metadata` (JSONB: divisions, keeper_deadline, ...)
- **Relationships**:
  - One-to-many with `TeamOwner` (multiple users in league)
  - One-to-many with `Roster` (multiple team rosters)
  - One-to-many with `Draft` (multiple drafts per league)
  - One-to-many with `TradedDraftPick` (traded picks)

#### 3. **TeamOwner** (Junction Table)
- **Table**: `team_owners`
- **Primary Key**: `id` (auto-increment)
- **Unique Constraint**: `(league_id, user_id)`
- **Purpose**: Represents a user's participation in a specific league with league-specific data
- **Key Fields**:
  - `league_id` (FK to leagues)
  - `user_id` (FK to users)
  - `display_name` (league-specific display name)
  - `team_name` (custom team name in this league)
  - `is_owner` (boolean: is league commissioner?)
  - `is_bot` (boolean)
  - `metadata` (JSONB: league-specific user settings)
- **Relationships**:
  - Many-to-one with `User`
  - Many-to-one with `League`

#### 4. **Roster**
- **Table**: `rosters`
- **Primary Key**: `id` (auto-increment)
- **Unique Constraint**: `(league_id, roster_id)`
- **Purpose**: Represents a team roster within a league
- **Key Fields**:
  - `league_id` (FK to leagues, indexed)
  - `roster_id` (roster number within league: 1-N)
  - `owner_id` (FK to users, nullable, indexed)
  - `co_owners` (ARRAY of user_ids)
  - `players` (JSONB array of player_ids: all players on roster)
  - `starters` (JSONB array of player_ids: starting lineup)
  - `reserve` (JSONB array of player_ids: IR/reserve)
  - `taxi` (JSONB array of player_ids: taxi squad)
  - `keepers` (JSONB array of player_ids: keepers for next season)
  - `roster_settings` (JSONB: wins, losses, points_for, points_against, waiver_position, ...)
  - `metadata` (JSONB: streak, record, division, ...)
  - `players_map` (JSONB: optional player_id mapping)
- **Relationships**:
  - Many-to-one with `League`
  - Many-to-one with `User` (owner)

#### 5. **Draft**
- **Table**: `drafts`
- **Primary Key**: `draft_id` (Sleeper draft_id)
- **Purpose**: Represents a draft event in a league
- **Key Fields**:
  - `league_id` (FK to leagues, indexed)
  - `type` (snake, linear, auction, ...)
  - `status` (indexed: pre_draft, drafting, complete)
  - `season` (indexed)
  - `draft_order` (JSONB: mapping of roster_id to draft position)
  - `draft_settings` (JSONB: rounds, slots_per_round, reversal_round, ...)
  - `metadata` (JSONB)
  - `creator_id` (user who created draft)
  - `created` (creation timestamp Unix ms)
- **Relationships**:
  - Many-to-one with `League`
  - One-to-many with `DraftPick`

#### 6. **DraftPick**
- **Table**: `draft_picks`
- **Primary Key**: `pick_id` (auto-increment)
- **Unique Constraint**: `(draft_id, pick_no)`
- **Purpose**: Represents an individual pick in a draft
- **Key Fields**:
  - `draft_id` (FK to drafts, indexed)
  - `pick_no` (overall pick number: 1-N)
  - `round` (round number, indexed)
  - `draft_slot` (position within round)
  - `player_id` (FK to players, indexed, SET NULL on delete)
  - `picked_by` (FK to users.user_id who made the pick, SET NULL on delete)
  - `roster_id` (Integer: league-internal roster number, NOT a FK)
  - `is_keeper` (boolean)
  - `metadata` (JSONB: position, team, amount for auction, ...)
- **Relationships**:
  - Many-to-one with `Draft` (draft)
  - Many-to-one with `Player` (player)
  - Many-to-one with `User` (picked_by_user)
- **Note**: roster_id is a league-internal number (1-N), not a database foreign key

#### 7. **TradedDraftPick**
- **Table**: `traded_draft_picks`
- **Primary Key**: `traded_pick_id` (auto-increment)
- **Unique Constraint**: `(league_id, season, round, roster_id)`
- **Purpose**: Tracks future draft picks that have been traded
- **Key Fields**:
  - `league_id` (FK to leagues, indexed)
  - `season` (indexed: season of the pick)
  - `round` (round number)
  - `roster_id` (Integer: original owner's roster number, NOT a FK)
  - `previous_owner_id` (Integer: roster number of previous owner)
  - `owner_id` (Integer: roster number of current owner)
- **Relationships**:
  - Many-to-one with `League` (league)
- **Note**: All roster_id fields are league-internal numbers (1-N), not database foreign keys

#### 8. **Player** (Optional)
- **Table**: `players`
- **Primary Key**: `player_id` (Sleeper player_id)
- **Purpose**: Stores NFL player metadata from Sleeper's player database
- **Key Fields**:
  - `first_name`, `last_name`, `full_name` (indexed)
  - `position` (indexed: QB, RB, WR, TE, K, DEF)
  - `team` (indexed: NFL team abbreviation)
  - `status` (Active, Inactive, Reserve, ...)
  - `number` (jersey number)
  - `age`, `height`, `weight`, `college`
  - `years_exp`, `draft_year`, `draft_round`, `draft_pick`
  - External IDs: `espn_id`, `yahoo_id`, `fantasy_data_id`, etc.
  - `injury_status`, `injury_body_part`, `injury_notes`
  - `metadata` (JSONB)
- **Relationships**:
  - One-to-many with `DraftPick` (draft_picks: picks of this player)
- **Note**: This table is optional and can be populated separately from the main data collection workflows

## Entity Relationship Diagram

```
User (team owner)
├─── TeamOwner (many-to-many through junction)
│    └─── League
│         ├─── TeamOwner (many users per league)
│         ├─── Roster (many rosters per league)
│         │    └─── User (owner, nullable)
│         ├─── Draft (many drafts per league)
│         │    └─── DraftPick (many picks per draft)
│         │         ├─── User (picked_by_user, nullable)
│         │         └─── Player (player, nullable)
│         └─── TradedDraftPick (many traded picks per league)
│
├─── Roster (one user owns many rosters across leagues)
└─── DraftPick (picks_made: picks made by this user)

Player (optional, referenced by FK in draft_picks)
 └─── DraftPick (draft_picks: picks selecting this player)
```

## Key Design Decisions

### 1. **User vs Team Owner**
- The Sleeper API calls this entity "user" but in the context of fantasy football, they are "team owners"
- We use `User` as the model name for consistency with API terminology
- User data is stored once and referenced across leagues

### 2. **JSONB Usage**
PostgreSQL JSONB columns are used for semi-structured data that:
- Has flexible/variable schema (metadata, settings)
- Is queried occasionally but not primary filter criteria
- Comes directly from API as nested objects

Examples:
- `League.scoring_settings`: Complex scoring rules with many optional fields
- `League.roster_positions`: Array of position slots
- `League.league_settings`: League configuration (num_teams, playoff_teams, etc.)
- `Roster.players`: Array of player IDs (allows direct storage of API response)
- `Roster.roster_settings`: Team stats (wins, losses, points, etc.)
- `Draft.draft_settings`: Draft configuration

### 3. **Array vs Separate Tables**
- Player IDs in rosters are stored as JSONB arrays rather than separate roster_player junction table
- Rationale: Rosters are snapshots in time; arrays make it easier to store historical roster states
- For querying specific players, use JSONB containment operators: `players @> '["12345"]'`

### 4. **League-Internal vs Database IDs**
- `roster_id` in DraftPick and TradedDraftPick is an Integer representing the league-internal roster number (1-N), NOT a database foreign key
- Rationale: Sleeper API uses roster_id as a sequential number within each league, not a global identifier
- To link picks to rosters, join on `(league_id, roster_id)` composite key

### 5. **Traded Picks**
- Separate table for traded picks because they represent future picks, not completed picks
- Tracks ownership chain: `roster_id` (original) → `previous_owner_id` → `owner_id` (current)
- All roster IDs are league-internal numbers, not FKs

### 6. **Timestamps**
- All tables have `created_at` and `updated_at` for audit trail
- Sleeper API timestamps are stored as integers (Unix ms) to preserve original format
- Database timestamps use `datetime.now(datetime.timezone.utc)` for consistency

### 7. **Indexes**
Strategic indexes for common query patterns:
- `users.username` (unique, indexed)
- `leagues.season`, `leagues.status`, `leagues.name`, `leagues.draft_id`
- `rosters.league_id`, `rosters.owner_id`
- `drafts.league_id`, `drafts.season`, `drafts.status`
- `draft_picks.draft_id`, `draft_picks.player_id`, `draft_picks.roster_id`, `draft_picks.round`, `draft_picks.picked_by`
- `team_owners.league_id`, `team_owners.user_id`
- Composite indexes with updated_at for efficient time-based queries
- Composite indexes for common joins: `(league_id, season)`, `(league_id, roster_id)`, `(draft_id, pick_no)`

### 8. **Foreign Key Cascade Rules**
- `CASCADE` on delete:
  - When a league is deleted, all rosters, drafts, picks, team_owners, and traded_picks are deleted
  - When a draft is deleted, all draft_picks are deleted
- `SET NULL` on delete:
  - `Roster.owner_id`: If a user is deleted, their rosters remain but owner_id becomes null
  - `League.draft_id`: If a draft is deleted, league remains but draft_id becomes null
  - `DraftPick.player_id`: If a player is deleted, pick history remains with null player_id
  - `DraftPick.picked_by`: If a user is deleted, pick history remains with null picked_by
- This preserves data integrity while allowing historical data to persist

## Usage Examples

### Creating Tables

```python
from sqlalchemy import create_engine
from schema.database_models import Base

engine = create_engine("postgresql://user:password@localhost:5432/sleeper_db")
Base.metadata.create_all(engine)
```

### Querying Data

```python
from sqlalchemy.orm import sessionmaker
from schema.database_models import User, League, Roster, Draft, DraftPick, TeamOwner

Session = sessionmaker(bind=engine)
session = Session()

# Find a user by username
user = session.query(User).filter_by(username="markm700").first()

# Get all leagues for a user in 2025 season
leagues = (
    session.query(League)
    .join(TeamOwner)
    .filter(TeamOwner.user_id == user.user_id)
    .filter(League.season == "2025")
    .all()
)

# Get all rosters owned by a user
rosters = session.query(Roster).filter_by(owner_id=user.user_id).all()

# Get all draft picks for a draft
picks = (
    session.query(DraftPick)
    .filter_by(draft_id="1205370713322557440")
    .order_by(DraftPick.pick_no)
    .all()
)

# Complex query: Find all drafts for leagues in 2025 season with status "complete"
drafts = (
    session.query(Draft)
    .join(League)
    .filter(League.season == "2025")
    .filter(Draft.status == "complete")
    .all()
)

# JSONB query: Find rosters that have a specific player
player_id = "6797"
rosters_with_player = (
    session.query(Roster)
    .filter(Roster.players.contains([player_id]))
    .all()
)
```

### Inserting Data

```python
from schema.database_models import User, League, Roster

# Create a new user
user = User(
    user_id="732752302007545856",
    username="markm700",
    display_name="markm700",
    avatar="2c83c9e64a60bd42699a91a09d34dda3",
    is_bot=False
)
session.add(user)

# Create a new league
league = League(
    league_id="1205370713318371328",
    name="DTA Jehovahs",
    season="2025",
    status="complete",
    sport="nfl",
    total_rosters=10,
    draft_id="1205370713322557440",
    roster_positions=["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "FLEX", "K", "DEF", "BN", "BN", "BN", "BN", "BN"],
    scoring_settings={"pass_yd": 0.04, "rec": 1, "rush_td": 6},
    league_settings={"num_teams": 10, "playoff_teams": 8}
)
session.add(league)

# Create a roster
roster = Roster(
    league_id="1205370713318371328",
    roster_id=1,
    owner_id="732752302007545856",
    players=["6797", "4866", "7553"],
    starters=["6797", "4866"],
    roster_settings={"wins": 6, "losses": 8, "points_for": 1500.5}
)
session.add(roster)

session.commit()
```

## Integration with Temporal Workflows

The schema is designed to store data collected by Temporal workflows:

1. **Data Collection Workflows** (`src/workflows/`)
   - `team_owner_data_collection.py` → populates `User`, `TeamOwner`
   - `league_data_collection.py` → populates `League`, `TeamOwner`, `Roster`
   - `draft_data_collection.py` → populates `Draft`, `DraftPick`, `TradedDraftPick`
   - `full_data_collection.py` → orchestrates all workflows

2. **Database Activities** (to be created in `src/activities/database/`)
   - `upsert_user.py` - Insert/update user data
   - `upsert_league.py` - Insert/update league data
   - `upsert_roster.py` - Insert/update roster data
   - `upsert_draft.py` - Insert/update draft data
   - `upsert_draft_picks.py` - Batch insert draft picks

3. **Workflow Pattern**
   ```
   API Activity (fetch data) → Transform → Database Activity (persist)
   ```

## Migration Strategy

For schema changes, use Alembic:

```bash
# Initialize Alembic (first time)
alembic init alembic

# Create a new migration
alembic revision --autogenerate -m "Add player injury fields"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Performance Considerations

1. **Indexes**: Strategic indexes are defined for common query patterns
2. **JSONB**: Use GIN indexes for JSONB columns if querying nested fields frequently:
   ```sql
   CREATE INDEX idx_league_scoring ON leagues USING GIN (scoring_settings);
   ```
3. **Array Containment**: JSONB arrays support fast containment queries with GIN indexes
4. **Batch Inserts**: Use `session.bulk_insert_mappings()` for large datasets like draft picks
5. **Connection Pooling**: Configure SQLAlchemy connection pool for concurrent workers

## Future Enhancements

- **Player Stats Table**: Store weekly/seasonal player statistics
- **Matchup Table**: Store head-to-head matchup results
- **Transaction Table**: Store trades, adds, drops, waiver claims
- **League History Table**: Track league settings changes over time
- **User Preferences Table**: Store user-specific app settings
- **ML Features Table**: Store computed features for draft predictions

## References

- Sleeper API Documentation: [Sleeper API Guide](../../mock-draft-agent-guides/sleeper-api-guide-v2.md)
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- PostgreSQL JSONB Documentation: https://www.postgresql.org/docs/current/datatype-json.html
