# Sleeper API - Mock Draft Agent Data Guide

## Overview
The Sleeper API is a **read-only HTTP API** that provides access to fantasy football league data without requiring authentication. Rate limit: Stay under 1000 API calls per minute.

Base URL: `https://api.sleeper.app/v1`

---

## Key Endpoints for Mock Draft Agent

### 1. User Information
**Get user by username or ID:**
```
GET /user/<username>
GET /user/<user_id>
```

Response includes:
- `user_id` (permanent identifier)
- `username` (can change over time)
- `display_name`
- `avatar`

**Important:** Store `user_id` not `username` as usernames can change.

---

### 2. League Data
**Get all leagues for a user:**
```
GET /user/<user_id>/leagues/<sport>/<season>
```
- `sport`: "nfl" (only supported sport currently)
- `season`: "2017", "2018", "2024", etc.

**Get specific league:**
```
GET /league/<league_id>
```

**League Response includes:**
- `league_id`
- `draft_id`
- `status` ("pre_draft", "drafting", "in_season", "complete")
- `total_rosters`
- `roster_positions` (array of position slots)
- `scoring_settings` (scoring configuration)
- `settings` (league rules)
- `previous_league_id` (for dynasty leagues)

---

### 3. Rosters & Users
**Get rosters in a league:**
```
GET /league/<league_id>/rosters
```

Response includes per roster:
- `roster_id`
- `owner_id` (user_id of owner)
- `players` (array of player_ids)
- `starters` (array of player_ids)
- `settings` (wins, losses, points, etc.)

**Get users in a league:**
```
GET /league/<league_id>/users
```

Response includes:
- `user_id`
- `username`
- `display_name`
- `avatar`
- `metadata.team_name` (user's custom team name)
- `is_owner` (commissioner status)

---

### 4. Draft Information

**Get all drafts for a user:**
```
GET /user/<user_id>/drafts/<sport>/<season>
```

**Get all drafts for a league:**
```
GET /league/<league_id>/drafts
```

**Get specific draft:**
```
GET /draft/<draft_id>
```

Draft response includes:
- `draft_id`
- `type` ("snake", "linear", etc.)
- `status` ("complete", "drafting", etc.)
- `settings` (teams, rounds, pick_timer, roster slots)
- `season`
- `draft_order` (user_id to draft slot mapping)
- `slot_to_roster_id` (draft slot to roster_id mapping)

**Get all picks in a draft:**
```
GET /draft/<draft_id>/picks
```

Pick response includes:
- `player_id`
- `picked_by` (user_id)
- `roster_id`
- `round`
- `draft_slot` (column on draft board)
- `pick_no` (overall pick number)
- `metadata` (player details: name, team, position, etc.)
- `is_keeper` (whether it was a keeper pick)

**Get traded picks in a draft:**
```
GET /draft/<draft_id>/traded_picks
```

---

### 5. Player Information

**Fetch all NFL players (USE SPARINGLY - ~5MB):**
```
GET /players/nfl
```

**Important:** Call this endpoint **once per day maximum**. Cache the results on your server.

Player object includes:
- `player_id` (e.g., "3086")
- `first_name`, `last_name`
- `position` (QB, RB, WR, TE, K, DEF)
- `team` (NFL team abbreviation)
- `fantasy_positions` (array of eligible positions)
- `status` ("Active", "Injured Reserve", etc.)
- `injury_status`
- `age`, `years_exp`
- `college`
- `search_rank` (popularity/relevance)

**Trending players (adds/drops):**
```
GET /players/nfl/trending/<type>?lookback_hours=<hours>&limit=<int>
```
- `type`: "add" or "drop"
- `lookback_hours`: default 24
- `limit`: default 25

---

### 6. Season History & Analytics

**Get matchups for a specific week:**
```
GET /league/<league_id>/matchups/<week>
```

Response per team:
- `roster_id`
- `matchup_id` (teams with same ID played each other)
- `starters` (ordered array of player_ids)
- `players` (all player_ids including bench)
- `points` (total points scored)

**Get transactions:**
```
GET /league/<league_id>/transactions/<round>
```

Transaction types: "trade", "free_agent", "waiver"

Response includes:
- `type`
- `roster_ids` (involved rosters)
- `adds` (player_id: roster_id mapping)
- `drops` (player_id: roster_id mapping)
- `draft_picks` (traded picks with season, round, ownership)
- `waiver_budget` (FAAB transactions)
- `creator` (user_id who initiated)

**Get traded picks (all seasons):**
```
GET /league/<league_id>/traded_picks
```

**Get playoff bracket:**
```
GET /league/<league_id>/winners_bracket
GET /league/<league_id>/losers_bracket
```

---

### 7. NFL State Information

**Get current NFL state:**
```
GET /state/nfl
```

Response includes:
- `week` (current week)
- `season` (current year)
- `season_type` ("pre", "regular", "post")
- `season_start_date`
- `league_season` (active season for leagues)
- `display_week`

---

## Data Collection Strategy for Mock Draft Agent

### Step 1: Identify User & League
1. Get user by username to retrieve `user_id`
2. Get all leagues for user across multiple seasons
3. Identify target league(s) for historical analysis

### Step 2: Historical Draft Data
For each relevant season:
1. Get league information (settings, scoring)
2. Get draft(s) for the league
3. Get all picks from each draft
4. Get traded picks to understand draft capital movements
5. Map `draft_order` and `slot_to_roster_id` to understand draft position strategy

### Step 3: League Performance Analysis
For each historical season:
1. Get rosters to see final team compositions
2. Get matchups for all weeks to analyze:
   - Scoring trends by position
   - Lineup decisions (starters vs bench)
   - Performance by draft position
3. Get transactions to understand:
   - Waiver wire activity patterns
   - Trade patterns
   - Player value over time

### Step 4: Player Data
1. Fetch complete player database (cache locally, update daily)
2. Cross-reference player_ids from drafts with player metadata
3. Analyze trending players for current draft preparation

### Step 5: Team Analysis
1. Get users in league to understand managers
2. Analyze draft patterns by manager:
   - Position preferences by round
   - Tendency for positional runs
   - Risk tolerance (injury-prone players, rookies)

---

## Mock Draft Agent Insights

### Historical Patterns to Analyze:
- **Draft Position Value:** Which draft slots historically perform best?
- **Positional Scarcity:** When does each position see runs in your league?
- **Manager Tendencies:** Does Manager X always reach for QBs early?
- **Roster Construction:** What team builds lead to championships?
- **Breakout Indicators:** What late-round picks became league winners?
- **Keeper/Dynasty Trends:** Long-term value assessment

### Recommended Data Points:
- Last 3-5 seasons of draft picks
- Weekly scoring data for roster analysis
- Transaction history to identify value adds
- Playoff results to weight successful strategies
- Current year trending data for player popularity

---

## Implementation Notes

1. **Start with one user_id and one league_id** to test your data pipeline
2. **Cache player data** - it's 5MB and shouldn't be called frequently
3. **Rate limiting** - Stay well under 1000 calls/minute
4. **Dynasty leagues** - Use `previous_league_id` to trace league history
5. **Player IDs** - All player references are strings (e.g., "1042", "CAR" for defenses)
6. **Error handling** - API returns standard HTTP codes (400, 404, 429, 500, 503)
