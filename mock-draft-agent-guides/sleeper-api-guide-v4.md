# Sleeper API - Mock Draft Agent Guide v4 (Advanced)

## Project Summary
Keeper league mock draft agent with real-time adaptation, advanced analytics, and strategic intelligence using n8n + Sleeper API.

**Target:** September 5, 2026 | **League:** 10-12 teams, 15 rounds, PPR, snake draft | **Data:** 2021-2025 seasons

---

## v4 Enhancements ✓

### Advanced Keeper Strategy
- **Position Weighting:** Primary weight on owner's previous keepers + likely patterns per owner; secondary weight on position scarcity
- **Injury History:** Tracked but not weighted if player returned during regular season
- **Opportunity Cost:** Calculate expected value of players available at keeper's round cost
- **Multi-Keeper Optimization:** Display both top 2 individual values (default) AND best 2-keeper combo per team

### Real-Time Draft Adaptation  
- **Run Detection:** When 3+ consecutive picks same position → adjust scarcity immediately
- **Panic Pick Flagging:** Alert when owner deviates significantly from historical patterns (e.g., 3rd QB early)
- **Value Alerts:** Trigger when player available 1 round + 3 picks late from ADP
- **No Live Learning:** Owner predictions static during draft (based on historical only)

### League Configuration
- **Teams:** 10 (not 12)
- **Playoffs:** Regular season wins weighted highest
- **Trade Deadline:** Week 11 (no keeper prediction impact)
- **Manual Adjustments:** Year 5 toilet bowl only flagged outlier

### Data Quality
- **Missing Data:** No interpolation needed (complete from Sleeper API)
- **Outliers:** Identify but don't exclude (e.g., COVID 2020 patterns)
- **Staleness Warning:** Alert if player data >1 month old pre-draft
- **Confidence Scores:** Granular (e.g., "85% confident RB", "40% confident specific player")

### n8n Optimization
- **API Calls:** Sequential to respect rate limits
- **Caching:** Use optimal strategy for player DB + manager tendencies (Redis/PostgreSQL as appropriate)
- **Workflow Restart:** Context-dependent (data import = restart, live draft = checkpoint resume)
- **Test Mode:** Not implemented (use historical validation instead)

### Advanced Analytics
- **Draft Position Analysis:** Track which slots (1st, 5th, 12th) produce best results historically
- **Boom/Bust Tracking:** Identify high-variance vs. consistent floor players, recommend by draft stage
- **Late-Round Targets:** Rounds 12-15 special logic for lottery tickets (high upside rookies, handcuffs)
- **Stacking Strategies:** Recommend QB-WR stacks from same team; identify negative correlations to avoid
- **Draft Philosophies:** Detect Zero-RB, Hero-RB, Robust-RB patterns per owner and predict accordingly

### User Experience
- **Draft Recap:** Post-draft report comparing predictions vs. actual, lessons learned for next year
- **What-If Scenarios:** Nice-to-have feature for pre-draft simulation
- **Mobile Notifications:** Alert when user's pick (not value alerts during others' picks)
- **No Study Mode:** Skip quiz/flashcard features

### External Data
- **Breaking News:** No manual input (rely on ranking source updates)
- **ADP Weighting:** Equal weight across sources, Sleeper ADP slightly higher (e.g., 1.2x vs 1.0x)
- **Consensus + Ceiling:** Show both average rankings and upside rankings
- **Preseason Games:** Ignore performance; only track injuries from preseason

### Performance
- **Simulation Speed:** 1 mock draft at a time, max 5/minute capacity
- **Historical Weighting:** All seasons equal (2021 = 2025 weight)
- **Recommendation Caching:** Nice-to-have for unchanged draft states (5-10 sec cache)

### Edge Cases
- **Player Changes:** Track mid-season team changes, weight current production by position; rank players with same name separately
- **Keeper Overrides:** Track from draft board via API `is_keeper` flag
- **Partial Drafts:** Not supported (nice-to-have for interruption resume)
- **Keeper Deadline:** Single snapshot only

### Strategic Intelligence
- **Championship Learning:** Learn from playoff teams only (not just champions)
- **Rookie Hype:** Track owners who historically over-draft rookies vs. veterans
- **Best Ball:** Don't incorporate (focus on redraft keeper league only)

### Documentation
- **Setup Guide:** Not included (technical users assumed)
- **Troubleshooting:** Not included
- **Video:** Not needed
- **API Keys:** Local storage if external sources require (but shouldn't)

---

## Sleeper API Quick Reference

**Base:** `https://api.sleeper.app/v1` | **Rate Limit:** <1000/min | **Auth:** None

```bash
# Discovery
GET /user/<username>                          → user_id
GET /user/<user_id>/leagues/nfl/<season>     → league_id, draft_id

# Draft Data (2021-2025)
GET /draft/<draft_id>                         → draft_order, settings
GET /draft/<draft_id>/picks                   → picks (player_id, round, pick_no, is_keeper)
GET /draft/<draft_id>/traded_picks            → traded draft picks

# Performance
GET /league/<league_id>/rosters               → wins/losses, points
GET /league/<league_id>/matchups/<week>       → weekly scores (1-18)
GET /league/<league_id>/transactions/<week>   → trades, waivers

# Players
GET /players/nfl                              → full DB (~5MB, cache daily)
GET /state/nfl                                → current season/week
```

---

## n8n Workflows (Optimized)

### WF1: Historical Import
**Trigger:** Manual | **Sequential API calls**
1. Input username → user_id
2. Loop 2021-2025: Get league → draft → picks, rosters, matchups (1-18), transactions (1-18)
3. Get player DB + NFL state
4. Store PostgreSQL/temp
5. Flag outliers (year 5 toilet bowl)

### WF2: Analysis + Predictions
**Trigger:** Manual post-import
1. **Manager Tendencies:** Position frequency by round, reach patterns, draft philosophies (Zero-RB detection)
2. **Draft Position Value:** Historical success by slot
3. **Boom/Bust Profiles:** Player variance scores
4. **Keeper Predictions:**
   - Calculate value: `(projected_round - keep_cost) × position_weight × owner_history_multiplier`
   - Generate top 2 individual + best combo per team
   - Track escalation (-1/keep), trade resets, consecutive restrictions
5. Export markdown reports with confidence scores

### WF3: Live Draft Simulator
**Trigger:** Webhook/API | **Input:** `{username, draft_state, current_pick}`
1. Load predicted keepers (preset)
2. Load external ADP (Sleeper 1.2x, ESPN/FantasyPros/Yahoo 1.0x)
3. Detect position runs (3+ consecutive) → adjust scarcity
4. **Recommendations (top 3 each):**
   - **BPA:** Consensus + ceiling rankings
   - **Positional Need:** Based on roster gaps
   - **Owner Tendency:** Historical patterns + philosophy match
   - **Value:** Players 1 round + 3 picks late
5. **Panic Pick Detection:** Flag 3-sigma deviations from owner norms
6. **Stacking Suggestions:** QB-WR from same team in appropriate rounds
7. **Late-Round Logic:** Rounds 12-15 prioritize lottery tickets
8. **Opponent Prediction:** 40% tendency, 30% BPA, 20% need, 10% keeper strategy
9. **Dual Grading:** Standard (national ADP) + league-specific (historical)
10. Return JSON with confidence scores

**Output:**
```json
{
  "recommendations": {
    "bpa": [{player_id, name, position, rank, ceiling_rank, confidence: 0.85}, ...],
    "positional_need": [{..., boom_bust_score: "floor", confidence: 0.72}],
    "owner_tendency": [{..., philosophy_match: "zero-rb", confidence: 0.91}],
    "value": [{..., rounds_late: 1.3, confidence: 0.68}],
    "stacking": [{qb_id, wr_id, team, expected_value}]
  },
  "alerts": {
    "value_alerts": ["Player X available - typically R5P3"],
    "position_run": "RB run detected (4 consecutive)",
    "panic_risk": null
  },
  "predicted_next_pick": {player_id, name, confidence: 0.78},
  "grades": {"standard": "A", "league": "B+"},
  "draft_position_insight": "Pick 5: Historically 2nd best performance"
}
```

### WF4: Player Refresh
**Trigger:** Daily cron | **Sequential**
1. GET /players/nfl
2. Check staleness (>30 days → warn)
3. Update DB with timestamp

### WF5: Post-Draft Recap
**Trigger:** Manual post-draft
1. Compare predictions vs. actual picks
2. Calculate accuracy: keeper predictions, pick predictions, value alerts
3. Identify missed patterns
4. Generate lessons-learned markdown
5. Store for next season's learning

---

## Database Schema (Minimal)

```sql
-- Core
users(user_id PK, username, draft_philosophy TEXT) -- zero-rb, hero-rb, etc
drafts(draft_id PK, season, draft_order JSONB, slot_to_roster_id JSONB)
draft_picks(pick_id PK, draft_id FK, player_id, user_id FK, round, pick_no, is_keeper BOOL)
players(player_id PK, name, position, team, boom_bust_score FLOAT, last_updated)

-- Analysis
manager_tendencies(user_id FK, round, position, frequency, avg_reach_rounds, philosophy TEXT)
draft_position_value(slot INT, total_points_avg, playoff_rate, championship_rate)
keeper_predictions(season, roster_id FK, player_id FK, predicted_round, confidence, is_combo_optimal BOOL)

-- Live Draft
draft_state(draft_session_id PK, current_pick, available_players JSONB, picked_players JSONB)
value_alerts(alert_id PK, player_id, rounds_late, triggered_at)
```

---

## Key Algorithms (Enhanced)

### Advanced Keeper Value
```javascript
function calculateKeeperValue(player, keepCost, ownerHistory, positionScarcity) {
  const projectedRound = getProjectedDraftRound(player); // Consensus ADP
  const baseValue = projectedRound - keepCost;
  
  // Opportunity cost
  const avgPlayerValueAtRound = getAverageValueAtRound(keepCost);
  const opportunityCost = player.projectedPoints - avgPlayerValueAtRound;
  
  // Owner tendency multiplier (primary weight)
  const ownerMultiplier = ownerHistory.keeperPatterns[player.position] || 1.0;
  
  // Position scarcity (secondary weight)  
  const scarcityMultiplier = positionScarcity[player.position] || 1.0;
  
  return (baseValue * ownerMultiplier * scarcityMultiplier) + (opportunityCost * 0.3);
}

function getBest2KeeperCombo(players, keepCost, rosterNeeds) {
  const combos = combinations(players, 2);
  return combos.map(combo => ({
    players: combo,
    totalValue: combo.reduce((sum, p) => sum + calculateKeeperValue(p, ...), 0),
    positionDiversity: combo[0].position !== combo[1].position ? 1.2 : 1.0
  })).sort((a, b) => b.totalValue * b.positionDiversity - a.totalValue * a.positionDiversity)[0];
}
```

### Real-Time Position Run Detection
```javascript
function detectPositionRun(recentPicks, threshold = 3) {
  const lastN = recentPicks.slice(-threshold);
  const positions = lastN.map(p => p.position);
  const mostCommon = mode(positions);
  
  if (positions.filter(p => p === mostCommon).length >= threshold) {
    return { detected: true, position: mostCommon, count: positions.filter(p => p === mostCommon).length };
  }
  return { detected: false };
}

function adjustScarcity(position, runCount) {
  const scarcityMultipliers = { RB: 1.3, WR: 1.1, TE: 1.2, QB: 1.0 };
  return scarcityMultipliers[position] * (1 + (runCount - 3) * 0.15); // +15% per pick beyond 3
}
```

### Panic Pick Detection
```javascript
function isPanicPick(owner, pick, round) {
  const historicalPattern = owner.tendencies[round] || {};
  const expectedPositions = Object.keys(historicalPattern).filter(pos => historicalPattern[pos] > 0.2);
  
  if (!expectedPositions.includes(pick.position)) {
    const deviation = 1.0 - (historicalPattern[pick.position] || 0);
    if (deviation > 0.85) { // 3-sigma equivalent
      return { isPanic: true, confidence: deviation, reason: `${pick.position} rarely taken R${round}` };
    }
  }
  
  // Early QB check
  if (pick.position === 'QB' && round < 8 && owner.avgQBRound > 10) {
    return { isPanic: true, confidence: 0.9, reason: "QB reach (historically waits)" };
  }
  
  return { isPanic: false };
}
```

### Draft Philosophy Detection
```javascript
function detectDraftPhilosophy(ownerPicks) {
  const earlyRounds = ownerPicks.filter(p => p.round <= 5);
  const rbCount = earlyRounds.filter(p => p.position === 'RB').length;
  const wrCount = earlyRounds.filter(p => p.position === 'WR').length;
  
  if (rbCount === 0 && wrCount >= 3) return 'Zero-RB';
  if (rbCount >= 1 && earlyRounds[0].position === 'RB') return 'Hero-RB';
  if (rbCount >= 3) return 'Robust-RB';
  if (wrCount >= 3) return 'WR-Heavy';
  return 'Balanced';
}
```

### Boom/Bust Scoring
```javascript
function calculateBoomBustScore(player, historicalWeeks) {
  const weeklyScores = historicalWeeks.map(w => w.points);
  const mean = average(weeklyScores);
  const variance = standardDeviation(weeklyScores);
  const coefficient = variance / mean; // Coefficient of variation
  
  if (coefficient > 0.5) return { type: 'boom-bust', score: coefficient, recommendation: 'Late round lottery' };
  if (coefficient < 0.2) return { type: 'floor', score: coefficient, recommendation: 'Safe early pick' };
  return { type: 'balanced', score: coefficient, recommendation: 'Flexible' };
}
```

### Stacking Recommendations
```javascript
function generateStackingRecs(availablePlayers, rosterState, round) {
  if (round < 4 || round > 10) return []; // Only middle rounds
  
  const qbOnRoster = rosterState.players.filter(p => p.position === 'QB');
  if (qbOnRoster.length === 0) return [];
  
  const qbTeam = qbOnRoster[0].team;
  const availableWRs = availablePlayers.filter(p => p.position === 'WR' && p.team === qbTeam);
  
  return availableWRs.map(wr => ({
    qb_id: qbOnRoster[0].player_id,
    wr_id: wr.player_id,
    team: qbTeam,
    expected_value: calculateStackValue(qbOnRoster[0], wr),
    correlation: 0.7 // QB-WR positive correlation
  }));
}
```

---

## Implementation Roadmap (5 Phases)

### Phase 1: Advanced Data Collection (Weeks 1-4)
- [ ] Historical import with outlier flagging
- [ ] Draft philosophy detection per owner
- [ ] Boom/bust scoring for all players
- [ ] Draft position value analysis

### Phase 2: Enhanced Keeper System (Weeks 5-8)  
- [ ] Opportunity cost calculator
- [ ] Multi-keeper combo optimizer
- [ ] Position + owner weighting
- [ ] Confidence score generation

### Phase 3: Real-Time Intelligence (Weeks 9-14)
- [ ] Position run detection
- [ ] Panic pick alerts
- [ ] Value alert system (1 round + 3 picks)
- [ ] Stacking recommendations

### Phase 4: Integration + Validation (Weeks 15-20)
- [ ] External ADP weighted integration
- [ ] Historical validation (predict 2024 from 2021-2023)
- [ ] Recommendation caching
- [ ] Mobile notification system

### Phase 5: Production + Recap (Weeks 21-26)
- [ ] 2026 player updates with staleness checks
- [ ] Final keeper predictions
- [ ] End-to-end testing
- [ ] Post-draft recap generator

---

## Success Metrics (Enhanced)
- **Keeper Accuracy:** ≥80% both players per team
- **Keeper Combo Optimization:** ≥70% accuracy on best combo vs. individual picks
- **Pick Prediction:** ≥60% exact, ≥85% position
- **Value Alert Precision:** ≥75% alerted players drafted within 2 rounds
- **Panic Pick Detection:** ≥80% of 3-sigma deviations caught
- **Draft Position Insight:** Correlation coefficient >0.6 between predicted slot performance and actual
- **Response Time:** <10 seconds
- **Post-Draft Lessons:** 5+ actionable insights per season

---

## Version History
- **v1:** API documentation
- **v2:** Full implementation (782 lines)
- **v3:** Refined keeper rules, MVP priorities (330 lines)
- **v4:** Advanced analytics, real-time adaptation, strategic intelligence, boom/bust tracking, stacking, draft philosophies

---

## Quick Start (v4)
1. Run WF1: Historical import → detect philosophies + outliers
2. Run WF2: Analysis → boom/bust scores + keeper predictions (individual + combo)
3. Configure WF3: Load 2026 keepers + external ADP
4. Test real-time features: Run detection, panic alerts, value triggers
5. Run WF5 post-draft: Recap analysis + lessons learned
6. Deploy for September 5, 2026
