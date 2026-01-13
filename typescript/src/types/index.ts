export interface Player {
  player_id: string;
  name: string;
  position: 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'DEF';
  team: string;
  boom_bust_score?: number;
  last_updated?: Date;
}

export interface User {
  user_id: string;
  username: string;
  draft_philosophy?: DraftPhilosophy;
}

export type DraftPhilosophy = 'Zero-RB' | 'Hero-RB' | 'Robust-RB' | 'WR-Heavy' | 'Balanced';

export interface Draft {
  draft_id: string;
  season: number;
  draft_order: Record<string, any>;
  slot_to_roster_id: Record<number, string>;
}

export interface DraftPick {
  pick_id: string;
  draft_id: string;
  player_id: string;
  user_id: string;
  round: number;
  pick_no: number;
  is_keeper: boolean;
}

export interface ManagerTendency {
  user_id: string;
  round: number;
  position: string;
  frequency: number;
  avg_reach_rounds: number;
  philosophy?: string;
}

export interface KeeperPrediction {
  season: number;
  roster_id: string;
  player_id: string;
  predicted_round: number;
  confidence: number;
  is_combo_optimal: boolean;
  value: number;
}

export interface DraftState {
  draft_session_id: string;
  current_pick: number;
  available_players: Player[];
  picked_players: DraftPick[];
}

export interface ValueAlert {
  alert_id: string;
  player_id: string;
  rounds_late: number;
  triggered_at: Date;
}

export interface BoomBustProfile {
  type: 'boom-bust' | 'floor' | 'balanced';
  score: number;
  recommendation: string;
}

export interface PositionRun {
  detected: boolean;
  position?: string;
  count?: number;
}

export interface PanicPick {
  isPanic: boolean;
  confidence?: number;
  reason?: string;
}

export interface StackingRecommendation {
  qb_id: string;
  wr_id: string;
  team: string;
  expected_value: number;
  correlation: number;
}

export interface DraftRecommendation {
  player_id: string;
  name: string;
  position: string;
  rank: number;
  ceiling_rank?: number;
  confidence: number;
  boom_bust_score?: string;
  philosophy_match?: string;
  rounds_late?: number;
}

export interface LiveDraftResponse {
  recommendations: {
    bpa: DraftRecommendation[];
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
    confidence: number;
  };
  grades: {
    standard: string;
    league: string;
  };
  draft_position_insight?: string;
}

export interface ExternalADP {
  player_id: string;
  source: 'sleeper' | 'espn' | 'fantasypros' | 'yahoo';
  adp: number;
  weight: number;
}

export interface KeeperValue {
  player: Player;
  keep_cost: number;
  projected_round: number;
  base_value: number;
  opportunity_cost: number;
  total_value: number;
  confidence: number;
}

export interface KeeperCombo {
  players: Player[];
  total_value: number;
  position_diversity: number;
}
