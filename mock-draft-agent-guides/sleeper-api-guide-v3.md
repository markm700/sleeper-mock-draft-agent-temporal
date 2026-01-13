# Sleeper API - Mock Draft Agent Guide v3 (Refined)

## Project Summary
Build a keeper league mock draft agent using n8n workflows to analyze 5 years of Sleeper data and simulate the 2026 draft with real-time recommendations.

**Target Draft:** September 5, 2026  
**League:** 10-12 teams, 15 rounds, PPR + custom scoring, snake draft, inverse finish order

---

## v3 Refinements ✓

### Keeper Rules (Clarified)
- **Escalation:** Player drafted round 5 → kept for round 4 → next keep round 3
- **Clock Reset:** If not kept, clock resets to new draft position
- **Trade Impact:** Traded players keep SAME round cost for new owner (no escalation on trade)
- **Owner Restriction:** Cannot keep same player twice consecutively
- **Waiver Cost:** Round 15 (except season-ending injured players)
- **Declaration:** Set anytime before draft, officially declared at draft time

**Example:** Player X drafted R5 by Owner A → traded to Owner B → Owner B keeps for R5 next year → Owner B cannot keep again

### League Specifics
- **Draft Order:** Inverse of previous season finish (may change to regular season finish)
- **Format:** Snake draft confirmed
- **Rounds:** 15
- **Scoring:** PPR + custom (fetch from API `scoring_settings`)
- **Roster:** Fetch from API `roster_positions`
- **Pick Trading:** Allowed before/during draft (rare during)
- **Same League:** Continuous across all seasons (use `previous_league_id` to trace)

### MVP Build Priority
1. **Historical Draft Analysis Report** - Who picked what, when, patterns
2. **Manager Tendency Profiles** - Position preferences by round, reach patterns
3. **Keeper Prediction for 2026** - 2 most likely per team
4. **Live Draft Simulator** - Real-time recommendations using all data

### Development Approach
- **Iterative + Architected:** Design upfront, build incrementally, test each piece
- **Validation:** Use 2021-2023 data to predict 2024 (compare to actual), then build for 2026

### n8n Workflow Architecture
- **Experience Level:** Medium-advanced
- **Processing:** JavaScript Code nodes acceptable
- **Structure:** Separate workflows for data collection, analysis, and draft simulation
- **Master Workflow:** Optional orchestrator for development
- **Error Handling:** Descriptive logs for debugging (not super verbose)

### External Rankings Integration
- **Primary Sources:** Sleeper ADP + ESPN (combo with FantasyPros, Yahoo as available)
- **Update Trigger:** Manual (on-demand for all data updates)
- **Use All Sources:** ADP from other Sleeper leagues + expert rankings

### User Interface
- **Primary:** JSON API returning recommendations per pick
- **Secondary:** CLI showing draft board
- **Nice-to-Have:** Web UI for board visualization
- **Pre-Draft Reports:** Markdown documents
- **Recommendations:** Top 3 per category (BPA, positional need, owner tendency, value)
- **Agent Picks:** Auto-select top recommendation for non-user owners

### Performance Requirements
- **Response Time:** <10 seconds for recommendations
- **User Pick Time:** 30 seconds after recommendations display
- **Concurrent Users:** 1 primary (max 10 if shared with league)
- **Storage:** Temp storage preferred, persistent for future updates/iterations

---

## Sleeper API Quick Reference

### Base
```
https://api.sleeper.app/v1
Rate Limit: <1000 calls/min
Auth: None (read-only)
```

### Core Endpoints
```
# User & League Discovery
GET /user/<username>                              → user_id
GET /user/<user_id>/leagues/nfl/<season>         → league_id, draft_id
GET /league/<league_id>                          → settings, scoring_settings, roster_positions

# Draft Data (repeat for 2021-2025)
GET /league/<league_id>/drafts                   → draft_id
GET /draft/<draft_id>                            → draft_order, slot_to_roster_id
GET /draft/<draft_id>/picks                      → all picks (player_id, round, pick_no, is_keeper)
GET /draft/<draft_id>/traded_picks               → traded draft picks

# Performance & Roster Analysis
GET /league/<league_id>/users                    → all owners
GET /league/<league_id>/rosters                  → final rosters, wins/losses, points
GET /league/<league_id>/matchups/<week>          → weekly performance (weeks 1-18)
GET /league/<league_id>/transactions/<week>      → trades, waivers (keeper tracking)
GET /league/<league_id>/traded_picks             → all traded picks across seasons

# Players
GET /players/nfl                                 → full player database (~5MB, cache daily)
GET /state/nfl                                   → current season state
```

### API Call Estimate
- Initial import: ~250-300 calls per season × 5 = 1,250-1,500 total
- Well within rate limits if batched

---

## n8n Workflow Design

### Workflow 1: Historical Data Import
**Trigger:** Manual  
**Steps:**
1. Input username → Get user_id
2. Loop seasons 2021-2025:
   - Get league → Get draft → Get picks
   - Get users, rosters, matchups (weeks 1-18)
   - Get transactions (weeks 1-18), traded picks
3. Get player database
4. Store in PostgreSQL/temp storage
5. Log completion

### Workflow 2: Analysis Engine
**Trigger:** Manual (after data import)  
**Steps:**
1. **Manager Tendencies:** Extract picks by owner/round/position, calculate preferences
2. **League Valuations:** Player performance vs draft position, position scarcity patterns
3. **Keeper Predictor:** Calculate keeper value, predict top 2 per team (track escalation + trades)
4. Generate markdown reports

### Workflow 3: Mock Draft Simulator
**Trigger:** Webhook/API  
**Input:** `{username, season: 2026, draft_state, current_pick}`  
**Steps:**
1. Load predicted keepers (preset in draft)
2. Load external rankings (Sleeper ADP + ESPN)
3. For current pick:
   - Calculate Top 3 BPA
   - Calculate Top 3 by positional need
   - Calculate Top 3 by owner tendency
   - Calculate Top 3 value picks
   - Generate value alerts
4. Predict opponent pick (weighted: 40% tendency, 30% BPA, 20% need, 10% keeper strategy)
5. Return JSON response
6. Log pick to draft state

**Output:**
```json
{
  "recommendations": {
    "bpa": [{player_id, name, position, rank}, ...],
    "positional_need": [...],
    "owner_tendency": [...],
    "value": [...]
  },
  "predicted_pick": {player_id, name, confidence},
  "value_alerts": ["Player X available - typically R5"],
  "pick_grades": {
    "standard": "A",
    "league_specific": "B+"
  }
}
```

### Workflow 4: Player Data Refresh
**Trigger:** Manual or daily cron  
**Steps:**
1. GET /players/nfl
2. Update player table
3. Log timestamp

---

## Database Schema (Simplified)

```sql
-- Core Tables
users(user_id PK, username, display_name)
leagues(league_id PK, season, scoring_settings JSONB, roster_positions JSONB)
drafts(draft_id PK, league_id FK, season, draft_order JSONB, slot_to_roster_id JSONB)
draft_picks(pick_id PK, draft_id FK, player_id, user_id FK, round, pick_no, is_keeper)
players(player_id PK, name, position, team, status, last_updated)

-- Analysis Tables
rosters(roster_id PK, league_id FK, owner_id FK, season, players JSONB, wins, losses, points)
matchups(matchup_id PK, league_id FK, season, week, roster_id FK, starters JSONB, points)
transactions(transaction_id PK, league_id FK, season, week, type, adds JSONB, drops JSONB, draft_picks JSONB)

-- Keeper Tracking
keeper_history(keeper_id PK, season, roster_id FK, player_id FK, keep_cost_round, times_kept)
keeper_predictions(prediction_id PK, season, roster_id FK, player_id FK, predicted_round, confidence)

-- Computed Data
manager_tendencies(user_id FK, season, round, position, frequency, is_reach)
league_valuations(player_id FK, season, draft_round, actual_points, value_score)
```

---

## Key Algorithms

### Keeper Value Calculator
```javascript
function calculateKeeperValue(player, lastDraftRound, timesKept, ownerChanged) {
  let keepCost = lastDraftRound - timesKept;
  if (ownerChanged) timesKept = 0; // Reset on trade
  
  const projectedRound = getProjectedDraftRound(player);
  const value = projectedRound - keepCost;
  const positionScarcity = getPositionScarcityMultiplier(player.position);
  
  return value * positionScarcity;
}
```

### Pick Prediction
```javascript
function predictPick(availablePlayers, owner, draftState) {
  const scores = availablePlayers.map(player => {
    const tendencyScore = getOwnerTendencyMatch(owner, player, draftState.round);
    const bpaScore = getBPARanking(player);
    const needScore = getPositionalNeed(owner, draftState);
    const keeperScore = getKeeperStrategyFit(player, owner);
    
    return {
      player,
      score: (0.40 * tendencyScore) + (0.30 * bpaScore) + 
             (0.20 * needScore) + (0.10 * keeperScore)
    };
  });
  
  return scores.sort((a, b) => b.score - a.score)[0];
}
```

### Pick Grading
```javascript
function gradePick(player, pickNumber, nationalADP, leagueADP) {
  const standardVariance = Math.abs(pickNumber - nationalADP);
  const leagueVariance = Math.abs(pickNumber - leagueADP);
  
  const gradeScale = {
    'A': [0, 5], 'B': [6, 10], 'C': [11, 20], 'D': [21, 30], 'F': [31, Infinity]
  };
  
  return {
    standard: getGrade(standardVariance, gradeScale),
    league: getGrade(leagueVariance, gradeScale)
  };
}
```

---

## Implementation Roadmap (Condensed)

### Phase 1: Foundation (Weeks 1-5)
- [ ] Docker + PostgreSQL setup
- [ ] n8n workflow: User/league discovery
- [ ] n8n workflow: Historical data import (all 5 seasons)
- [ ] Database populated with draft picks, transactions, rosters
- **Deliverable:** Complete historical database

### Phase 2: Analysis (Weeks 6-11)
- [ ] Manager tendency calculator
- [ ] League valuation model (position scarcity, ADP variance)
- [ ] Keeper prediction system (with escalation logic)
- [ ] Generate markdown analysis reports
- **Deliverable:** Historical draft analysis + manager profiles + keeper predictions

### Phase 3: Draft Engine (Weeks 12-18)
- [ ] Mock draft state manager
- [ ] Recommendation engine (BPA, need, tendency, value)
- [ ] Pick prediction algorithm
- [ ] Dual grading system
- [ ] JSON API + CLI interface
- **Deliverable:** Working mock draft simulator

### Phase 4: Integration (Weeks 19-24)
- [ ] External rankings integration (Sleeper ADP + ESPN)
- [ ] Historical validation (2021-2023 → predict 2024)
- [ ] Refinement based on validation results
- **Deliverable:** Validated system with external data

### Phase 5: Pre-Season Prep (Weeks 25-32)
- [ ] 2026 player rankings update
- [ ] Final keeper predictions
- [ ] End-to-end testing
- [ ] Optional web UI (nice-to-have)
- **Deliverable:** Production-ready for September 5, 2026 draft

---

## Success Metrics
- **Keeper Accuracy:** ≥80% (16+ of 20 correct)
- **Pick Prediction:** ≥60% exact player, ≥85% correct position
- **Response Time:** <10 seconds
- **API Reliability:** Zero rate limit violations

---

## Version History
- **v1:** Initial API documentation and endpoint reference
- **v2:** Full implementation plan with detailed workflows and algorithms
- **v3:** Refined with keeper logic clarifications, MVP priorities, condensed roadmap

---

## Quick Start Checklist
1. Get Sleeper username → user_id
2. Identify league_id for target league
3. Run Historical Data Import workflow (seasons 2021-2025)
4. Run Analysis Engine workflow → generate reports
5. Review manager tendencies and keeper predictions
6. Configure Mock Draft Simulator with 2026 keepers
7. Test with CLI interface
8. Use for September 5, 2026 draft
