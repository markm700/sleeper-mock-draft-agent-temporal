/**
 * TypeScript interfaces for Sleeper Mock Draft Agent
 * Based on sleeper-api-guide-v4.md
 */

/**
 * Sleeper Player from /players/nfl endpoint
 */
export interface Player {
  player_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  position: 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'DEF';
  team: string | null;
  status: 'Active' | 'Inactive' | 'Injured Reserve' | 'PUP';
  injury_status: string | null;
  age: number | null;
  years_exp: number | null;
  fantasy_positions: string[];
  search_rank: number;
  last_updated?: Date;
}

/**
 * Sleeper User from /user endpoint
 */
export interface User {
  user_id: string;
  username: string;
  display_name: string;
  avatar: string | null;
  created?: number;
  draft_philosophy?: 'zero-rb' | 'hero-rb' | 'robust-rb' | 'balanced' | null;
}

/**
 * Sleeper Draft from /draft endpoint
 */
export interface Draft {
  draft_id: string;
  league_id: string;
  season: string;
  season_type: 'regular' | 'pre' | 'post';
  type: 'snake' | 'linear';
  status: 'pre_draft' | 'drafting' | 'complete';
  settings: {
    teams: number;
    rounds: number;
    pick_timer: number;
    slots_wr: number;
    slots_rb: number;
    slots_te: number;
    slots_qb: number;
    slots_flex: number;
    slots_bn: number;
  };
  draft_order: { [rosterId: string]: number } | null;
  slot_to_roster_id: { [slot: string]: string } | null;
  start_time: number | null;
  created: number;
}

/**
 * Sleeper Draft Pick from /draft/picks endpoint
 */
export interface DraftPick {
  pick_id: string;
  draft_id: string;
  player_id: string;
  picked_by: string; // roster_id
  roster_id: string;
  round: number;
  draft_slot: number;
  pick_no: number;
  is_keeper: boolean;
  metadata?: {
    team: string;
    position: string;
    player_name: string;
  };
}

/**
 * Manager tendency analysis by round and position
 */
export interface ManagerTendency {
  user_id: string;
  round: number;
  position: string;
  frequency: number; // 0-1 probability
  avg_reach_rounds: number; // positive = early, negative = late
  philosophy: 'zero-rb' | 'hero-rb' | 'robust-rb' | 'balanced' | null;
  rookie_bias: number; // -1 to 1, positive = prefers rookies
}

/**
 * Keeper prediction for upcoming season
 */
export interface KeeperPrediction {
  season: number;
  roster_id: string;
  user_id: string;
  player_id: string;
  player_name: string;
  position: string;
  predicted_round: number;
  keep_cost: number;
  keeper_value: number;
  confidence: number; // 0-1
  is_combo_optimal: boolean;
  opportunity_cost: number;
  position_scarcity_multiplier: number;
  owner_tendency_multiplier: number;
}

/**
 * Current draft state for live recommendations
 */
export interface DraftState {
  draft_id: string;
  current_pick: number;
  current_round: number;
  on_the_clock: string; // roster_id
  available_players: string[]; // player_ids
  picked_players: DraftPick[];
  team_rosters: { [rosterId: string]: string[] }; // roster_id -> player_ids
  keepers: { [rosterId: string]: string[] }; // roster_id -> player_ids
}

/**
 * Value alert for players available late
 */
export interface ValueAlert {
  alert_id: string;
  player_id: string;
  player_name: string;
  position: string;
  adp_rank: number;
  current_pick: number;
  rounds_late: number;
  confidence: number;
  triggered_at: Date;
}

/**
 * Boom/bust profile for player variance
 */
export interface BoomBustProfile {
  player_id: string;
  variance_score: number; // 0-1, higher = more volatile
  floor_score: number; // minimum expected points
  ceiling_score: number; // maximum expected points
  consistency_rating: 'boom' | 'bust' | 'floor' | 'ceiling';
  recommended_draft_stage: 'early' | 'mid' | 'late';
}

/**
 * Position run detection result
 */
export interface PositionRun {
  detected: boolean;
  position: string;
  consecutive_count: number;
  picks: number[]; // pick numbers
  scarcity_adjustment: number; // multiplier to apply
}

/**
 * Panic pick detection result
 */
export interface PanicPick {
  detected: boolean;
  roster_id: string;
  player_id: string;
  position: string;
  expected_position: string;
  sigma_deviation: number;
  reason: string;
}

/**
 * Stacking recommendation (QB-WR from same team)
 */
export interface StackingRecommendation {
  qb_id: string;
  qb_name: string;
  wr_id: string;
  wr_name: string;
  team: string;
  expected_value: number;
  correlation_score: number; // 0-1
  recommended_rounds: [number, number]; // [qb_round, wr_round]
}

/**
 * Draft recommendation with confidence
 */
export interface DraftRecommendation {
  player_id: string;
  name: string;
  position: string;
  rank: number;
  ceiling_rank?: number;
  confidence: number; // 0-1
  boom_bust_score?: 'boom' | 'bust' | 'floor' | 'ceiling';
  philosophy_match?: 'zero-rb' | 'hero-rb' | 'robust-rb' | 'balanced';
  rounds_late?: number;
  reasoning: string;
}

/**
 * Live draft response with all recommendations and alerts
 */
export interface LiveDraftResponse {
  draft_id: string;
  current_pick: number;
  on_the_clock: string;
  recommendations: {
    bpa: DraftRecommendation[]; // Best player available
    positional_need: DraftRecommendation[];
    owner_tendency: DraftRecommendation[];
    value: DraftRecommendation[];
    stacking: StackingRecommendation[];
  };
  alerts: {
    value_alerts: string[];
    position_run: string | null;
    panic_risk: string | null;
  };
  predicted_next_pick: {
    player_id: string;
    name: string;
    position: string;
    confidence: number;
  } | null;
  grades: {
    standard: string; // Letter grade based on national ADP
    league: string; // Letter grade based on historical league patterns
  };
  draft_position_insight: string;
}

/**
 * Draft position historical performance
 */
export interface DraftPositionValue {
  slot: number;
  total_points_avg: number;
  playoff_rate: number; // 0-1
  championship_rate: number; // 0-1
  best_strategy: string;
}

/**
 * League roster from /league/rosters endpoint
 */
export interface LeagueRoster {
  roster_id: number;
  owner_id: string;
  league_id: string;
  players: string[];
  starters: string[];
  settings: {
    wins: number;
    losses: number;
    ties: number;
    fpts: number;
  };
}

/**
 * Weekly matchup from /league/matchups endpoint
 */
export interface WeeklyMatchup {
  roster_id: number;
  matchup_id: number;
  points: number;
  starters: string[];
  players: string[];
  custom_points: number | null;
}

/**
 * Transaction from /league/transactions endpoint
 */
export interface Transaction {
  transaction_id: string;
  type: 'trade' | 'waiver' | 'free_agent';
  status: 'complete' | 'pending';
  roster_ids: number[];
  adds: { [playerId: string]: number } | null;
  drops: { [playerId: string]: number } | null;
  draft_picks: any[];
  created: number;
  week: number;
}
