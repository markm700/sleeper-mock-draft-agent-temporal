-- Sleeper Mock Draft Agent Database Schema
-- PostgreSQL

-- Core Tables

CREATE TABLE IF NOT EXISTS users (
  user_id VARCHAR(50) PRIMARY KEY,
  username VARCHAR(100) NOT NULL,
  draft_philosophy VARCHAR(20),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS drafts (
  draft_id VARCHAR(50) PRIMARY KEY,
  season INTEGER NOT NULL,
  draft_order JSONB,
  slot_to_roster_id JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS draft_picks (
  pick_id SERIAL PRIMARY KEY,
  draft_id VARCHAR(50) REFERENCES drafts(draft_id),
  player_id VARCHAR(50) NOT NULL,
  user_id VARCHAR(50) REFERENCES users(user_id),
  round INTEGER NOT NULL,
  pick_no INTEGER NOT NULL,
  is_keeper BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS players (
  player_id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  position VARCHAR(10),
  team VARCHAR(10),
  boom_bust_score FLOAT,
  last_updated TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis Tables

CREATE TABLE IF NOT EXISTS manager_tendencies (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(50) REFERENCES users(user_id),
  round INTEGER NOT NULL,
  position VARCHAR(10) NOT NULL,
  frequency FLOAT NOT NULL,
  avg_reach_rounds FLOAT,
  philosophy VARCHAR(20),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, round, position)
);

CREATE TABLE IF NOT EXISTS draft_position_value (
  slot INTEGER PRIMARY KEY,
  total_points_avg FLOAT,
  playoff_rate FLOAT,
  championship_rate FLOAT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS keeper_predictions (
  id SERIAL PRIMARY KEY,
  season INTEGER NOT NULL,
  roster_id VARCHAR(50) NOT NULL,
  player_id VARCHAR(50) REFERENCES players(player_id),
  predicted_round INTEGER NOT NULL,
  confidence FLOAT NOT NULL,
  is_combo_optimal BOOLEAN DEFAULT FALSE,
  value_score FLOAT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(season, roster_id, player_id)
);

-- Live Draft Tables

CREATE TABLE IF NOT EXISTS draft_sessions (
  draft_session_id VARCHAR(50) PRIMARY KEY,
  draft_id VARCHAR(50) REFERENCES drafts(draft_id),
  current_pick INTEGER NOT NULL,
  available_players JSONB,
  picked_players JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS value_alerts (
  alert_id SERIAL PRIMARY KEY,
  draft_session_id VARCHAR(50) REFERENCES draft_sessions(draft_session_id),
  player_id VARCHAR(50) REFERENCES players(player_id),
  rounds_late FLOAT NOT NULL,
  triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Tracking Tables

CREATE TABLE IF NOT EXISTS rosters (
  roster_id VARCHAR(50) PRIMARY KEY,
  league_id VARCHAR(50) NOT NULL,
  season INTEGER NOT NULL,
  user_id VARCHAR(50) REFERENCES users(user_id),
  wins INTEGER DEFAULT 0,
  losses INTEGER DEFAULT 0,
  points FLOAT DEFAULT 0,
  made_playoffs BOOLEAN DEFAULT FALSE,
  won_championship BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matchups (
  matchup_id SERIAL PRIMARY KEY,
  league_id VARCHAR(50) NOT NULL,
  season INTEGER NOT NULL,
  week INTEGER NOT NULL,
  roster_id VARCHAR(50) NOT NULL,
  points FLOAT NOT NULL,
  opponent_roster_id VARCHAR(50),
  opponent_points FLOAT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
  transaction_id VARCHAR(50) PRIMARY KEY,
  league_id VARCHAR(50) NOT NULL,
  season INTEGER NOT NULL,
  week INTEGER NOT NULL,
  type VARCHAR(20) NOT NULL,
  roster_id VARCHAR(50) NOT NULL,
  player_id VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Weekly Performance (for boom/bust calculations)

CREATE TABLE IF NOT EXISTS weekly_performance (
  id SERIAL PRIMARY KEY,
  player_id VARCHAR(50) REFERENCES players(player_id),
  season INTEGER NOT NULL,
  week INTEGER NOT NULL,
  points FLOAT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(player_id, season, week)
);

-- Indexes for performance

CREATE INDEX IF NOT EXISTS idx_draft_picks_draft_id ON draft_picks(draft_id);
CREATE INDEX IF NOT EXISTS idx_draft_picks_user_id ON draft_picks(user_id);
CREATE INDEX IF NOT EXISTS idx_draft_picks_player_id ON draft_picks(player_id);
CREATE INDEX IF NOT EXISTS idx_manager_tendencies_user_id ON manager_tendencies(user_id);
CREATE INDEX IF NOT EXISTS idx_keeper_predictions_season ON keeper_predictions(season);
CREATE INDEX IF NOT EXISTS idx_rosters_season ON rosters(season);
CREATE INDEX IF NOT EXISTS idx_matchups_season_week ON matchups(season, week);
CREATE INDEX IF NOT EXISTS idx_weekly_performance_player_season ON weekly_performance(player_id, season);

-- Comments

COMMENT ON TABLE users IS 'Sleeper users and their draft philosophies';
COMMENT ON TABLE drafts IS 'Draft metadata and configuration';
COMMENT ON TABLE draft_picks IS 'All historical draft picks';
COMMENT ON TABLE players IS 'NFL player database with boom/bust scores';
COMMENT ON TABLE manager_tendencies IS 'Historical drafting patterns per manager';
COMMENT ON TABLE draft_position_value IS 'Historical success rates by draft slot';
COMMENT ON TABLE keeper_predictions IS 'AI-generated keeper predictions';
COMMENT ON TABLE draft_sessions IS 'Live draft state tracking';
COMMENT ON TABLE value_alerts IS 'Triggered value alerts during live drafts';
