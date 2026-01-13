# Sleeper API - Mock Draft Agent Implementation Guide v2

## Project Overview
**Goal:** Build a keeper league mock draft agent that simulates draft behavior based on 6 years of historical data, providing real-time recommendations and pick grading during the draft.

**Key Features:**
- Keeper league support (2 keepers per team, 1 round escalation on repeat keeps)
- Manager-specific draft tendency analysis
- Live draft simulation with real-time recommendations
- Dual pick grading: standard rankings vs. league-specific value
- Trade analysis for keeper determination
- n8n workflow automation with HTTP request nodes
- Docker-based data store for local deployment

**Timeline:** Draft in September 2026 (8 months development time)

---

## Requirements Summary

### League Context ✓ (Answered in v2)
- **League Type:** Keeper league (2 keepers/team, escalating 1 round if re-kept)
- **History:** 6 seasons (2021-2025), Year 6 starting Sept 2026
- **Members:** Stable roster, potential for future changes
- **Settings:** Variable (playoff structure, scoring adjustments over time)
- **Data Scope:** All available historical data for the league

### Technical Stack ✓ (Answered in v2)
- **Automation:** n8n with HTTP request nodes
- **Deployment:** Docker containers
- **Storage:** Local data store (PostgreSQL or similar)
- **API Integration:** Sleeper API (read-only, no auth required)
- **Execution:** On-demand with optional cron scheduling

### Core Functionality ✓ (Answered in v2)
1. **Pre-Draft Analysis:**
   - Predict 2 most likely keepers per team
   - Historical draft pattern analysis per manager
   - League-specific player valuations

2. **Live Draft Simulation:**
   - Real-time pick recommendations as draft progresses
   - Manager behavior predictions ("Owner X likely picks position Y")
   - Dual pick grading system:
     * Grade A: Standard/national rankings comparison
     * Grade B: League-specific historical value
   - Value alerts for both standard and owner-specific opportunities

3. **Data Analysis:**
   - All historical draft picks with positions/rounds
   - Trade analysis (impacts keeper eligibility and draft capital)
   - Waiver pickup tracking (for keeper purposes - round 15 keeps)
   - Positional scarcity timing within the league
   - Championship team composition patterns
   - ADP variance from standard rankings

---

## Sleeper API Endpoints Reference

### Base Information
**Base URL:** `https://api.sleeper.app/v1`  
**Rate Limit:** Stay under 1000 calls/minute  
**Authentication:** None required (read-only API)

### Priority 1: User & League Discovery

#### 1.1 Get User Information
```
GET /user/<username>
```
**Returns:** `user_id`, `username`, `display_name`, `avatar`  
**Note:** Template to accept any username input

#### 1.2 Get All Leagues for User
```
GET /user/<user_id>/leagues/nfl/<season>
```
**Seasons to fetch:** 2021, 2022, 2023, 2024, 2025  
**Returns:** Array of leagues with `league_id`, `draft_id`, `status`, `settings`, `scoring_settings`, `roster_positions`

#### 1.3 Get Specific League Details
```
GET /league/<league_id>
```
**Returns:** Complete league configuration including `previous_league_id` for dynasty tracking

---

### Priority 2: Historical Draft Data

#### 2.1 Get All Drafts for League
```
GET /league/<league_id>/drafts
```
**Returns:** Array of drafts (should be 1 per season for your league)

#### 2.2 Get Specific Draft Details
```
GET /draft/<draft_id>
```
**Critical fields:**
- `draft_order`: user_id → draft slot mapping
- `slot_to_roster_id`: draft slot → roster_id mapping
- `type`: "snake" (likely for your league)
- `settings`: roster slots, rounds, pick timer

#### 2.3 Get All Draft Picks
```
GET /draft/<draft_id>/picks
```
**Returns per pick:**
- `player_id`, `picked_by` (user_id), `roster_id`
- `round`, `draft_slot`, `pick_no`
- `metadata`: player name, position, team, status
- `is_keeper`: Boolean flag

**Must fetch for:** All 5 completed drafts (2021-2025)

#### 2.4 Get Traded Draft Picks
```
GET /draft/<draft_id>/traded_picks
```
**Returns:** `season`, `round`, `roster_id` (original owner), `owner_id` (current owner)  
**Importance:** Critical for accurate keeper analysis

---

### Priority 3: Manager & Roster Analysis

#### 3.1 Get League Users
```
GET /league/<league_id>/users
```
**Returns:** All owners with `user_id`, `display_name`, `metadata.team_name`, `is_owner` (commissioner)

#### 3.2 Get League Rosters
```
GET /league/<league_id>/rosters
```
**Returns per roster:**
- `roster_id`, `owner_id`
- `players`: array of player_ids
- `settings`: wins, losses, total points
- `starters`: which players were started

---

### Priority 4: Season Performance Data

#### 4.1 Get Weekly Matchups
```
GET /league/<league_id>/matchups/<week>
```
**Weeks:** 1-18 (regular season + playoffs)  
**Returns:** `roster_id`, `starters`, `players`, `points`, `matchup_id`  
**Use:** Analyze which draft picks performed well, championship rosters

#### 4.2 Get Transactions
```
GET /league/<league_id>/transactions/<round>
```
**Types:** "trade", "waiver", "free_agent"  
**Returns:** `adds`, `drops`, `draft_picks` (in trades), `roster_ids`, `waiver_budget`  
**Use:** Track trades (keeper implications), waiver pickups (round 15 keeper eligibility)

#### 4.3 Get Traded Picks (All Seasons)
```
GET /league/<league_id>/traded_picks
```
**Returns:** All future traded picks across seasons  
**Use:** Track draft capital movement affecting current year

---

### Priority 5: Player Database

#### 5.1 Fetch All NFL Players
```
GET /players/nfl
```
**Size:** ~5MB  
**Frequency:** Once per day maximum (cache locally)  
**Returns:** Complete player database with:
- `player_id`, `first_name`, `last_name`
- `position`, `team`, `fantasy_positions`
- `status`, `injury_status`, `age`, `years_exp`
- `search_rank`: popularity/relevance score

#### 5.2 Get Trending Players (Optional)
```
GET /players/nfl/trending/<type>?lookback_hours=24&limit=25
```
**Types:** "add" or "drop"  
**Note:** Low priority per your answer to Q16

---

### Priority 6: Current NFL State

#### 6.1 Get NFL Season State
```
GET /state/nfl
```
**Returns:** `week`, `season`, `season_type`, `season_start_date`, `league_season`  
**Use:** Validate current season data, check if draft season is active

---

## Data Collection Workflow (n8n Implementation)

### Phase 1: Initial Data Extraction (Run Once, Cache Locally)

**Workflow: "Historical Data Import"**

1. **Input Node:** Accept username parameter
2. **HTTP Request:** Get user_id from username
3. **Loop:** For each season (2021-2025):
   - Get leagues for user/season
   - Identify target league (by name or continuity via `previous_league_id`)
   - Get league settings & scoring
   - Get draft_id from league
   - Get complete draft data (picks + traded picks)
   - Get league users
   - Get league rosters
   - For each week 1-18: Get matchups
   - For each week 1-18: Get transactions
   - Get traded picks
4. **HTTP Request:** Get player database (once)
5. **Database Insert:** Store all data in PostgreSQL/Docker

**Estimated API Calls:** 
- ~250-300 calls per season × 5 seasons = 1,250-1,500 total
- Well within rate limits if batched properly

---

### Phase 2: Data Processing & Analysis

**Workflow: "Manager Tendency Analysis"**

For each manager:
1. Extract all historical draft picks by round/position
2. Calculate positional preferences by round (e.g., "Takes RB in rounds 1-3: 80%")
3. Identify reach patterns (players drafted before their typical ADP)
4. Track keeper selections over time
5. Analyze championship roster composition
6. Calculate success metrics (wins, playoff appearances, championships)

**Workflow: "League Valuation Model"**

1. For each player drafted historically:
   - Calculate total fantasy points scored that season
   - Determine value over replacement by position
   - Compare to draft position (round/pick)
   - Generate league-specific ADP vs. national ADP variance
2. Identify league-specific position scarcity patterns
3. Map "rush" rounds for each position (when does league draft heavy at position?)
4. Calculate optimal roster construction from championship teams

**Workflow: "Keeper Prediction Model"**

For current season (2026):
1. For each team's current roster (end of 2025 season):
   - Identify eligible keepers (not kept twice by same owner)
   - Calculate keeper value (projected draft round - keeper cost)
   - Rank top 3-4 keeper candidates per team
   - Predict 2 most likely keepers based on value + owner tendencies
2. Account for traded players who could be keepers for new teams
3. Track waiver pickups eligible for round 15 keeps

---

### Phase 3: Live Mock Draft Engine

**Workflow: "Mock Draft Simulator"**

**Pre-Draft Setup:**
1. Load 2026 player rankings (external: FantasyPros, ESPN, Yahoo)
2. Load predicted keepers per team (locks 2 picks per team)
3. Set draft order for 2026
4. Initialize available player pool (remove keepers)

**Draft Loop (per pick):**
1. **Determine Current Pick:**
   - Round, pick number, owner_id
   - Remaining roster needs for owner
   - Position scarcity at current point

2. **Generate Recommendations:**
   - **Best Available Player (BPA):** Top 5 by national consensus rankings
   - **Position Need:** Top 3 players at positions of need
   - **Owner Tendency Match:** Top 3 players matching owner's historical patterns
   - **Value Pick:** Players with highest projected value vs. current pick position
   - **League Value Pick:** Players valued higher in league history than nationally

3. **Predict Owner's Actual Pick:**
   - Weight factors: 40% owner tendency, 30% BPA, 20% positional need, 10% keeper strategy
   - Return predicted player

4. **Record Pick & Update:**
   - Remove player from available pool
   - Update roster for owner
   - Advance to next pick

5. **Grade Previous Pick (if applicable):**
   - **Standard Grade:** Compare to national ADP/rankings
     * A: Drafted within 5 picks of ADP
     * B: Drafted 6-10 picks from ADP
     * C: Drafted 11-20 picks from ADP
     * D/F: Significant reach (>20 picks early)
   - **League Grade:** Compare to league historical ADP
     * Apply same grading scale using league data
   - Display both grades with explanation

6. **Value Alerts:**
   - "Player X available - typically goes in round Y (national)"
   - "Player Z available - strong fit for your draft history at position"

**Output:**
- Real-time pick-by-pick simulation
- Recommendations for user at their picks
- Predicted picks for other owners
- Dual grading system for all picks
- Value alerts throughout draft

---

### Phase 4: Real-Time Draft Integration (Future)

**Workflow: "Live Draft Monitor"**

1. Poll Sleeper API for current draft state (if draft is active)
2. Compare actual picks vs. predictions
3. Adjust future predictions based on deviations
4. Update recommendations in real-time
5. Grade picks as they occur

---

## Implementation Priority & Roadmap

### Sprint 1 (Weeks 1-2): Data Foundation
- [ ] Set up Docker environment
- [ ] Configure PostgreSQL database schema
- [ ] Build n8n workflow for user/league discovery
- [ ] Test API connectivity and rate limiting
- [ ] **Deliverable:** Can retrieve user_id and league_ids for all 5 seasons

### Sprint 2 (Weeks 3-5): Historical Data Import
- [ ] Build draft data extraction workflow (all picks, all seasons)
- [ ] Build transaction data extraction workflow
- [ ] Import player database and create daily refresh job
- [ ] Build league settings/scoring extraction
- [ ] Store all data in database with proper relationships
- [ ] **Deliverable:** Complete historical database populated

### Sprint 3 (Weeks 6-8): Manager Tendency Analysis
- [ ] Create manager draft pattern analysis queries
- [ ] Build positional preference calculator per manager
- [ ] Identify reach patterns and value picks by manager
- [ ] Calculate success metrics (wins, championships) by draft strategy
- [ ] **Deliverable:** Manager tendency reports for all owners

### Sprint 4 (Weeks 9-11): League Valuation Model
- [ ] Calculate league-specific player values (historical points)
- [ ] Build position scarcity analyzer
- [ ] Create league ADP calculator
- [ ] Compare league ADP vs. national ADP (integrate external rankings)
- [ ] Identify championship roster patterns
- [ ] **Deliverable:** League valuation model with variance reports

### Sprint 5 (Weeks 12-14): Keeper Prediction System
- [ ] Build keeper eligibility checker (track who kept whom)
- [ ] Create keeper value calculator (draft round - keep cost)
- [ ] Implement keeper escalation logic (1 round higher if re-kept)
- [ ] Account for traded players and waiver pickups
- [ ] Predict 2 keepers per team for 2026
- [ ] **Deliverable:** 2026 keeper predictions for all 12 teams

### Sprint 6 (Weeks 15-18): Mock Draft Engine Core
- [ ] Build draft state manager (tracks picks, roster composition)
- [ ] Implement player recommendation engine (BPA, need, tendency, value)
- [ ] Create pick prediction algorithm (owner behavior model)
- [ ] Build dual grading system (standard + league grades)
- [ ] Implement value alert system
- [ ] **Deliverable:** Working mock draft simulator (command-line/API)

### Sprint 7 (Weeks 19-21): Integration & Testing
- [ ] Integrate all components into unified n8n workflow
- [ ] Build REST API endpoints for draft queries
- [ ] Create manual trigger for on-demand execution
- [ ] Test with historical draft data (simulate 2025 draft)
- [ ] Validate predictions against actual outcomes
- [ ] **Deliverable:** End-to-end mock draft system

### Sprint 8 (Weeks 22-24): External Rankings Integration
- [ ] Scrape/integrate FantasyPros consensus rankings
- [ ] Integrate ESPN and Yahoo rankings
- [ ] Build ranking aggregator and comparator
- [ ] Update grading system with multi-source rankings
- [ ] **Deliverable:** Enhanced grading with external data sources

### Sprint 9 (Weeks 25-28): UI & Usability
- [ ] Create draft board visualization (optional web UI)
- [ ] Build recommendation display interface
- [ ] Implement pick grading display
- [ ] Add draft history review tool
- [ ] **Deliverable:** User-friendly draft interface

### Sprint 10 (Weeks 29-32): Pre-Season Preparation
- [ ] Update player database for 2026 season
- [ ] Refresh external rankings (July/August 2026)
- [ ] Run keeper predictions for all teams
- [ ] Validate 2026 draft order
- [ ] Test complete draft simulation
- [ ] **Deliverable:** Production-ready system for September 2026 draft

---

## Database Schema

### Tables

#### `users`
- `user_id` (PK)
- `username`
- `display_name`
- `avatar`

#### `leagues`
- `league_id` (PK)
- `season` (year)
- `name`
- `status`
- `total_rosters`
- `scoring_settings` (JSONB)
- `roster_positions` (JSONB)
- `previous_league_id` (FK to leagues)

#### `drafts`
- `draft_id` (PK)
- `league_id` (FK)
- `season`
- `type` (snake/linear)
- `status`
- `draft_order` (JSONB)
- `slot_to_roster_id` (JSONB)
- `settings` (JSONB)

#### `draft_picks`
- `pick_id` (PK)
- `draft_id` (FK)
- `player_id`
- `picked_by_user_id` (FK to users)
- `roster_id`
- `round`
- `draft_slot`
- `pick_no`
- `is_keeper`
- `player_metadata` (JSONB)

#### `rosters`
- `roster_id` (PK)
- `league_id` (FK)
- `owner_id` (FK to users)
- `season`
- `players` (JSONB array)
- `settings` (JSONB - wins/losses/points)

#### `matchups`
- `matchup_id` (PK)
- `league_id` (FK)
- `season`
- `week`
- `roster_id` (FK)
- `starters` (JSONB)
- `players` (JSONB)
- `points`

#### `transactions`
- `transaction_id` (PK)
- `league_id` (FK)
- `season`
- `week`
- `type` (trade/waiver/free_agent)
- `roster_ids` (JSONB)
- `adds` (JSONB)
- `drops` (JSONB)
- `draft_picks` (JSONB)
- `creator_user_id` (FK)

#### `players`
- `player_id` (PK)
- `first_name`
- `last_name`
- `position`
- `team`
- `fantasy_positions` (JSONB)
- `status`
- `injury_status`
- `age`
- `years_exp`
- `search_rank`
- `last_updated` (for daily refresh)

#### `keeper_history`
- `keeper_id` (PK)
- `season`
- `roster_id` (FK)
- `player_id` (FK)
- `keep_cost` (round number)
- `times_kept` (count for escalation)

#### `manager_tendencies` (computed table)
- `tendency_id` (PK)
- `user_id` (FK)
- `season`
- `round_number`
- `position_drafted`
- `was_reach` (boolean)
- `adp_variance`

---

## n8n Workflow Structure

### Workflow 1: Data Import Orchestrator
**Trigger:** Manual or scheduled (annual)
**Nodes:**
1. Manual trigger with username input
2. Get user data (HTTP Request)
3. Loop seasons 2021-2025 (Split in Batches)
4. Per season:
   - Get leagues (HTTP Request)
   - Filter target league (IF node)
   - Get draft data (HTTP Request)
   - Get picks (HTTP Request)
   - Get users (HTTP Request)
   - Get rosters (HTTP Request)
   - Get transactions (Loop weeks, HTTP Request)
   - Get matchups (Loop weeks, HTTP Request)
5. Get players database (HTTP Request)
6. Transform and insert to PostgreSQL (Postgres nodes)
7. Success notification

### Workflow 2: Keeper Predictor
**Trigger:** Manual (pre-season)
**Nodes:**
1. Manual trigger
2. Query current rosters (Postgres)
3. Query keeper history (Postgres)
4. Calculate keeper eligibility (Code node)
5. Calculate keeper values (Code node)
6. Rank keepers per team (Code node)
7. Predict top 2 (Function node)
8. Store predictions (Postgres)
9. Output keeper report

### Workflow 3: Mock Draft Simulator API
**Trigger:** Webhook (REST API endpoint)
**Nodes:**
1. Webhook trigger (accepts: draft_state, current_pick, user_id)
2. Load predicted keepers (Postgres)
3. Load player rankings (Postgres/HTTP)
4. Load manager tendencies (Postgres)
5. Calculate recommendations (Code node):
   - BPA
   - Position need
   - Owner tendency match
   - Value picks
6. Predict opponent picks (Function node)
7. Grade previous pick if applicable (Code node)
8. Generate value alerts (Function node)
9. Return JSON response with all recommendations
10. Log pick to draft state (Postgres)

### Workflow 4: Player Database Refresh
**Trigger:** Cron (daily at 3 AM)
**Nodes:**
1. Schedule trigger
2. Get players from Sleeper (HTTP Request)
3. Truncate/update players table (Postgres)
4. Success notification

---

## API Endpoints (n8n Webhooks)

### POST `/api/mock-draft/start`
**Body:** `{ "username": "string", "season": 2026 }`  
**Returns:** Draft session ID, predicted keepers, draft order

### POST `/api/mock-draft/next-pick`
**Body:** `{ "session_id": "string", "draft_state": {...} }`  
**Returns:** Recommendations, predicted pick, value alerts

### POST `/api/mock-draft/record-pick`
**Body:** `{ "session_id": "string", "player_id": "string" }`  
**Returns:** Pick grades (standard + league), updated draft state

### GET `/api/managers/{user_id}/tendencies`
**Returns:** Historical draft patterns for specific manager

### GET `/api/keepers/predictions/{season}`
**Returns:** Predicted keepers for all teams

### GET `/api/league/valuation/{season}`
**Returns:** League-specific player valuations and ADP data

---

## Key Algorithms

### 1. Keeper Value Calculator
```
keeper_value = (projected_draft_round - keep_cost_round) × position_scarcity_multiplier

Where:
- keep_cost_round = last_draft_round - 1 (or 15 for waivers)
- If player kept before by same owner: keep_cost_round = previous_keep_round - 1
- position_scarcity_multiplier = based on league historical positional runs
```

### 2. Manager Pick Prediction
```
predicted_pick = weighted_score(available_players)

weighted_score = 
  (0.40 × manager_tendency_match_score) +
  (0.30 × bpa_ranking_score) +
  (0.20 × positional_need_score) +
  (0.10 × keeper_strategy_score)

Adjust weights based on:
- Round number (early rounds favor BPA)
- Manager's historical variance from rankings
- Positional scarcity at current pick
```

### 3. Pick Grading Algorithm
```
standard_grade = calculate_adp_variance(player, pick_number, national_adp)
league_grade = calculate_adp_variance(player, pick_number, league_adp)

adp_variance = abs(pick_number - adp)

Grading scale:
A: variance ≤ 5 picks
B: variance 6-10 picks
C: variance 11-20 picks
D: variance 21-30 picks
F: variance > 30 picks

Special considerations:
- Position runs (grade more favorably if position scarce)
- Injury news (adjust expectations)
- Keeper escalation (account for limited keeper pool)
```

### 4. Value Alert System
```
For each unpicked player:
  standard_value = (player_national_adp - current_pick_number)
  league_value = (player_league_adp - current_pick_number)
  
  If standard_value > 10: Alert "Standard value available"
  If league_value > 10: Alert "League-specific value available"
  
  If player matches current_owner tendencies AND value > 5:
    Alert "Excellent fit for your draft history"
```

---

## Testing Strategy

### Unit Tests
- Keeper eligibility checker (edge cases: trades, repeats)
- Pick grading algorithm (various ADPs)
- Manager tendency scoring
- Value calculator

### Integration Tests
- Complete data import from Sleeper API (mock 2025 season)
- End-to-end mock draft simulation
- Keeper prediction accuracy (validate against actual 2025 keepers)
- Manager prediction accuracy (simulate 2024 draft, compare to actual)

### Performance Tests
- API rate limiting compliance
- Database query performance (draft recommendations < 500ms)
- Mock draft simulation speed (full 15-round draft < 30 seconds)

### Validation Tests
- Historical validation: Simulate 2024 draft with 2021-2023 data
- Compare predictions to actual 2024 results
- Measure prediction accuracy:
  - Keeper predictions: Target 80%+ accuracy (16+ of 20 keepers correct)
  - Manager pick predictions: Target 60%+ exact match, 85%+ correct position
  - Value alerts: Validate ROI of recommended picks

---

## Success Metrics

### Primary Goals (for Sept 2026 draft)
1. **Keeper Predictions:** ≥80% accuracy on 2 keepers per team
2. **Manager Predictions:** ≥60% exact player match, ≥85% correct position
3. **Pick Grading:** ≥90% consistency with post-season analysis
4. **Value Recommendations:** Positive ROI (recommended picks outperform draft position)

### Secondary Goals
1. Complete historical database (all 5 seasons imported)
2. Sub-500ms recommendation generation time
3. Zero API rate limit violations during data import
4. Successful Docker deployment on local machine

---

## Risk Mitigation

### Risk 1: Sleeper API Changes
**Mitigation:** 
- Version all API endpoints in documentation
- Implement error handling for API changes
- Test connections monthly leading up to draft

### Risk 2: Manager Behavior Changes
**Mitigation:**
- Weight recent seasons more heavily (2024-2025: 40%, 2023: 30%, 2021-2022: 30%)
- Implement confidence scores on predictions
- Provide multiple recommendation options vs. single prediction

### Risk 3: Keeper Rule Complexity
**Mitigation:**
- Thoroughly document keeper escalation logic
- Build test cases for all keeper scenarios
- Manual validation of keeper predictions with league commissioner

### Risk 4: External Ranking Data Availability
**Mitigation:**
- Support multiple ranking sources (FantasyPros, ESPN, Yahoo)
- Graceful degradation if external data unavailable
- Fallback to prior season rankings if necessary

### Risk 5: Timeline Slippage
**Mitigation:**
- Build MVP first (core mock draft without all features)
- Prioritize keeper predictions and manager tendencies
- External rankings and advanced grading can be added post-MVP
- Monthly checkpoint reviews against roadmap

---

## Future Enhancements (Post-Sept 2026)

1. **Machine Learning Model:** Replace weighted scoring with trained ML model on historical data
2. **Trade Analyzer:** Suggest in-season trades based on roster needs and opponent tendencies
3. **Waiver Wire Assistant:** Recommend pickups based on league value patterns
4. **League Shareability:** Allow all league members to use the tool
5. **Mobile App:** Build iOS/Android app for draft-day use
6. **Real-Time Draft Sync:** Auto-sync with live Sleeper draft (no manual input)
7. **Multi-League Support:** Analyze and compare across multiple leagues
8. **Injury Impact Modeling:** Real-time adjustment of recommendations based on injury news
9. **Auction Draft Support:** Adapt for auction/salary cap drafts
10. **Custom Scoring Rules:** More granular handling of unique league scoring

---

## Conclusion

This specification provides a complete roadmap for building a keeper league mock draft agent using the Sleeper API, n8n automation, and Docker deployment. The phased approach prioritizes data foundation, analysis, and core functionality to deliver a working system by September 2026.

**Next Steps:**
1. Review and approve this specification
2. Set up development environment (Docker, PostgreSQL, n8n)
3. Begin Sprint 1: Data Foundation
4. Establish weekly progress check-ins

**Questions or concerns? Add them to the custom-specs file for iteration to v3.**
