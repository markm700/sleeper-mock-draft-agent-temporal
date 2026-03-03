"""
SQLAlchemy ORM models for Sleeper Fantasy Football data storage.

This module defines the database schema for storing team owners (users), leagues,
rosters, drafts, and draft picks collected from the Sleeper API via Temporal workflows.

Database: PostgreSQL 13+
ORM: SQLAlchemy 2.0+
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

@dataclass # no FKs
class User(Base):
    """
    Represents a Sleeper user (team owner).

    Maps to the user data returned by GET /user/{username} endpoint.
    Primary entity for tracking fantasy football team owners across leagues.
    """

    __tablename__ = "users"

    # Primary Key
    user_id = Column(String(50), primary_key=True, comment="Sleeper user_id")

    # Core User Fields
    username = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=False)
    is_bot = Column(Boolean, default=False, nullable=False)

    # Optional User Fields (mostly null from public API)
    real_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    # Semi-structured data
    api_metadata = Column(JSONB, nullable=True, comment="User metadata from API")

    # Audit fields
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False
    )
    data_updated = Column(
        DateTime, nullable=True, comment="Last update timestamp from Sleeper API"
    )

    # Relationships
    # Note: team_owners, rosters, and picks_made relationships removed since those tables
    # use reference-only user_id fields (no FK constraints for ETL flexibility)

    # Indexes
    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_display_name", "display_name"),
        Index("idx_users_username_updated_at", "username", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, username={self.username})>"

@dataclass
class League(Base):
    """
    Represents a Sleeper fantasy football league.

    Maps to the league data returned by GET /league/{league_id} endpoint.
    Contains league settings, scoring rules, and roster configuration.
    """

    __tablename__ = "leagues"

    # Primary Key
    league_id = Column(String(50), primary_key=True, comment="Sleeper league_id")
    
    # Reference Fields (no FK constraint for ETL flexibility)
    draft_id = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Primary draft_id (reference only, no FK constraint for ETL flexibility)"
    )

    # Core League Fields
    name = Column(String(255), nullable=False, index=True, comment="Sleeper league name")
    season = Column(String(10), nullable=False, index=True, comment="e.g., '2025'")
    sport = Column(String(20), default="nfl", nullable=False)
    status = Column(
        String(50),
        nullable=False,
        index=True,
        comment="League status: pre_draft, drafting, in_season, complete",
    )

    # League Configuration
    total_rosters = Column(Integer, nullable=True, comment="Number of teams")
    shard = Column(Integer, nullable=True, comment="Sleeper server shard")

    # Related IDs
    previous_league_id = Column(
        String(50), nullable=True, comment="League ID from previous season"
    )
    bracket_id = Column(BigInteger, nullable=True)
    loser_bracket_id = Column(BigInteger, nullable=True)
    bracket_overrides_id = Column(BigInteger, nullable=True)
    loser_bracket_overrides_id = Column(BigInteger, nullable=True)

    # League Type
    season_type = Column(
        String(50), default="regular", nullable=True, comment="regular, playoff, etc."
    )

    # Semi-structured Configuration (JSONB for flexibility)
    roster_positions = Column(
        JSONB, nullable=True, comment="Array of roster position slots, e.g., ['QB', 'RB', 'WR']"
    )
    scoring_settings = Column(
        JSONB,
        nullable=True,
        comment="Scoring rules: pass_yd, rec, rush_td, etc. with point values",
    )
    league_settings = Column(
        JSONB,
        nullable=True,
        comment="League settings: num_teams, playoff_teams, waiver_type, etc.",
    )
    api_metadata = Column(
        JSONB,
        nullable=True,
        comment="Additional league metadata: divisions, keeper settings, auto_continue, etc.",
    )

    # Audit fields
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    team_owners = relationship(
        "TeamOwner", back_populates="league", cascade="all, delete-orphan"
    )
    rosters = relationship("Roster", back_populates="league", cascade="all, delete-orphan")
    drafts = relationship(
        "Draft",
        foreign_keys="Draft.league_id",
        back_populates="league",
        cascade="all, delete-orphan"
    )
    traded_picks = relationship(
        "TradedDraftPick", back_populates="league", cascade="all, delete-orphan"
    )

    # Indexes and Constraints
    __table_args__ = (
        Index("idx_leagues_season", "season"),
        Index("idx_leagues_name", "name"),
        Index("idx_leagues_draft_id", "draft_id"),
        Index("idx_leagues_season_name", "season", "name"),
        Index("idx_leagues_name_draft_id", "draft_id", "name"),
        Index("idx_leagues_name_updated_at", "name", "updated_at"),
        Index("idx_leagues_season_name_updated_at", "season", "name", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<League(league_id={self.league_id}, name={self.name}, season={self.season})>"

@dataclass
class TeamOwner(Base):
    """
    Junction table representing a user/team owner's participation in a league.

    Contains league-specific user data like team name, roster_id, user_id, and league-specific metadata.
    Maps to data from GET /league/{league_id}/users endpoint.
    """

    __tablename__ = "team_owners"

    # Composite Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(
        String(50), ForeignKey("leagues.league_id", ondelete="CASCADE"), nullable=False
    )
    
    # Reference Fields (no FK constraint for ETL flexibility)
    user_id = Column(
        String(50),
        nullable=False,
        index=True,
        comment="User_id reference (no FK constraint for ETL flexibility)"
    )

    # League-specific User Data
    display_name = Column(String(255), nullable=False, comment="Display name in this league")
    is_owner = Column(Boolean, default=False, comment="Is this user the league commissioner?")
    is_bot = Column(Boolean, default=False)

    # League-specific metadata
    api_metadata = Column(
        JSONB,
        nullable=True,
        comment="League-specific user metadata: team_name, allow_pn, mention_pn, etc.",
    )

    # Audit fields
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    league = relationship("League", back_populates="team_owners")
    # Note: No relationship to User - user_id is reference-only for ETL flexibility

    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("league_id", "user_id", name="uq_league_user"),
        Index("idx_team_owners_league_id", "league_id"),
        Index("idx_team_owners_user_id", "user_id"),
        Index("idx_team_owners_league_id_user_id_updated_at", "league_id", "user_id", "updated_at")
    )

    def __repr__(self) -> str:
        return f"<TeamOwner(league_id={self.league_id}, user_id={self.user_id})>"

@dataclass
class Roster(Base):
    """
    Represents a team roster in a league.

    Contains player IDs, starters, bench, taxi squad, and team settings/stats.
    Maps to data from GET /league/{league_id}/rosters endpoint.
    """

    __tablename__ = "rosters"

    # Composite Primary Key (league_id + roster_id is unique per league)
    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(
        String(50),
        ForeignKey("leagues.league_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    roster_id = Column(Integer, nullable=False, comment="Roster ID within the league (1-N), typuically N = 10 or 12 (total_rosters)")

    # Reference Fields (no FK constraint for ETL flexibility)
    owner_id = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Primary owner user_id (reference only, no FK constraint for ETL flexibility)",
    )
    co_owners = Column(
        ARRAY(String(50)), nullable=True, comment="Array of co-owner user_ids"
    )

    # Player Rosters (arrays of player IDs)
    players = Column(
        JSONB,
        nullable=True,
        comment="Array of all player_ids on this roster (starters + bench + reserve + taxi)",
    )
    starters = Column(
        JSONB, nullable=True, comment="Array of player_ids in starting lineup slots"
    )
    reserve = Column(JSONB, nullable=True, comment="Array of player_ids on reserve/IR")
    taxi = Column(JSONB, nullable=True, comment="Array of player_ids on taxi squad")

    # Keeper Configuration
    keepers = Column(
        JSONB,
        nullable=True,
        comment="Array of player_ids designated as keepers for next season",
    )

    # Roster Settings & Stats (JSONB for flexibility)
    roster_settings = Column(
        JSONB,
        nullable=True,
        comment="Team stats: wins, losses, points_for, points_against, waiver_position, etc.",
    )
    api_metadata = Column(
        JSONB,
        nullable=True,
        comment="Roster metadata: streak, record, division, continued_from, etc.",
    )

    # Players Map (if needed for lookup)
    players_map = Column(
        JSONB,
        nullable=True,
        comment="Optional mapping of player_ids to additional player data",
    )

    # Audit fields
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    league = relationship("League", back_populates="rosters")
    # Note: No relationship to User - owner_id is reference-only for ETL flexibility
    # Note: No direct relationship to DraftPick - roster_id in DraftPick is league-internal number, not FK

    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("league_id", "roster_id", name="uq_league_roster"),
        Index("idx_rosters_league_id", "league_id"),
        Index("idx_rosters_owner_id", "owner_id"),
        Index("idx_rosters_league_roster", "league_id", "roster_id"),
        Index("idx_rosters_league_roster_updated_at", "league_id", "roster_id", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Roster(league_id={self.league_id}, roster_id={self.roster_id}, owner_id={self.owner_id})>"

@dataclass
class Draft(Base):
    """
    Represents a draft event in a league.

    Maps to data from GET /league/{league_id}/drafts and GET /draft/{draft_id} endpoints.
    """

    __tablename__ = "drafts"

    # Primary Key
    draft_id = Column(String(50), primary_key=True, comment="Sleeper draft_id")

    # Foreign Keys
    league_id = Column(
        String(50),
        ForeignKey("leagues.league_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Draft Configuration
    type = Column(
        String(50),
        nullable=True,
        comment="Draft type: snake, linear, auction, etc.",
    )
    status = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Draft status: pre_draft, drafting, complete",
    )
    season = Column(String(10), nullable=False, index=True, comment="Season year")
    season_type = Column(String(50), nullable=True, comment="regular, playoff, etc.")
    sport = Column(String(20), default="nfl", nullable=False)

    # Draft Settings & Metadata
    draft_order = Column(JSONB, nullable=True, comment="Mapping of roster_id to draft position")
    draft_settings = Column(
        JSONB,
        nullable=True,
        comment="Draft settings: rounds, slots_per_round, reversal_round, etc.",
    )
    api_metadata = Column(JSONB, nullable=True, comment="Additional draft metadata")

    # Creator Info
    creator_id = Column(String(50), nullable=True, comment="User who created the draft")
    created = Column(BigInteger, nullable=True, comment="Creation timestamp (Unix ms)")

    # Audit fields
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    league = relationship(
        "League",
        foreign_keys=[league_id],
        back_populates="drafts"
    )
    picks = relationship("DraftPick", back_populates="draft", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_drafts_league_id", "league_id"),
        Index("idx_drafts_status", "status"),
        Index("idx_drafts_season", "season"),
        Index("idx_drafts_league_season", "league_id", "season"),
        Index("idx_drafts_league_season_updated_at", "league_id", "season", "updated_at")
    )

    def __repr__(self) -> str:
        return f"<Draft(draft_id={self.draft_id}, league_id={self.league_id}, status={self.status})>"

@dataclass
class DraftPick(Base):
    """
    Represents an individual pick in a draft.

    Maps to data from GET /draft/{draft_id}/picks endpoint.
    """

    __tablename__ = "draft_picks"

    # Primary Key
    pick_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign Keys
    draft_id = Column(
        String(50),
        ForeignKey("drafts.draft_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Draft_id the pick occurred in"
    )
    
    # Reference Fields (no FK constraint for ETL flexibility)
    picked_by = Column(
        String(50),
        nullable=True,
        index=True,
        comment="User_id who made the pick (reference only, no FK constraint for ETL flexibility)"
    )
    
    # Reference Fields (no FK constraint for ETL flexibility)
    player_id = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Sleeper player_id that was picked (reference only, no FK constraint since Player table is optional)"
    )
    
    # Non-FK Fields (roster_id is league-internal number, not DB FK)
    roster_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="Roster_id (league-internal number) that received the player"
    )

    # Pick Details
    pick_no = Column(Integer, nullable=False, comment="Overall pick number (1-N)")
    round = Column(Integer, nullable=False, comment="Round number")
    draft_slot = Column(Integer, nullable=False, comment="Draft position within round")

    # Pick Details
    is_keeper = Column(Boolean, default=False, comment="Was this a keeper pick?")
    api_metadata = Column(
        JSONB,
        nullable=True,
        comment="Pick metadata: years_owned, position, team, amount (auction), etc.",
    )

    # Audit fields
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    draft = relationship("Draft", back_populates="picks")
    # Note: No relationship to User - picked_by is reference-only for ETL flexibility
    # Note: No direct relationship to Player - player_id is reference-only for ETL flexibility

    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("draft_id", "pick_no", name="uq_draft_pick_no"),
        Index("idx_draft_picks_draft_id", "draft_id"),
        Index("idx_draft_picks_player_id", "player_id"),
        Index("idx_draft_picks_roster_id", "roster_id"),
        Index("idx_draft_picks_round", "round"),
        Index("idx_draft_picks_draft_id_updated_at", "draft_id", "updated_at"),
        Index("idx_draft_picks_draft_id_pick_no", "draft_id", "pick_no"),
    )

    def __repr__(self) -> str:
        return f"<DraftPick(draft_id={self.draft_id}, pick_no={self.pick_no}, player_id={self.player_id})>"

@dataclass
class TradedDraftPick(Base):
    """
    Represents a traded draft pick.

    Tracks future draft picks that have been traded between teams.
    Maps to data from GET /league/{league_id}/traded_picks endpoint.
    """

    __tablename__ = "traded_draft_picks"

    # Primary Key
    traded_pick_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign Keys
    league_id = Column(
        String(50),
        ForeignKey("leagues.league_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Pick Identification
    season = Column(String(10), nullable=False, index=True, comment="Season of the pick")
    round = Column(Integer, nullable=False, comment="Round number of the pick")

    # Roster IDs (league-internal numbers, not DB FKs)
    roster_id = Column(
        Integer, nullable=False, comment="Roster_id of the original owner of this pick"
    )

    # Previous and Current Owner
    previous_owner_id = Column(
        Integer,
        nullable=True,
        comment="Roster_id of the previous owner (before most recent trade)",
    )
    owner_id = Column(
        Integer, nullable=False, comment="Roster_id of the current owner of this pick"
    )

    # Audit fields
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    league = relationship("League", back_populates="traded_picks")

    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint(
            "league_id", "season", "round", "roster_id", name="uq_traded_pick"
        ),
        Index("idx_traded_picks_league_id", "league_id"),
        Index("idx_traded_picks_season", "season"),
        Index("idx_traded_picks_owner_id", "owner_id"),
        Index("idx_traded_picks_league_season", "league_id", "season"),
    )

    def __repr__(self) -> str:
        return f"<TradedDraftPick(league_id={self.league_id}, season={self.season}, round={self.round}, owner_id={self.owner_id})>"

@dataclass # no FKs
class Player(Base):
    """
    Represents an NFL player from the Sleeper player database.

    Optional table for storing player metadata from GET /players/nfl endpoint.
    Players are referenced by player_id in rosters and draft picks.
    """

    __tablename__ = "players"

    # Primary Key
    player_id = Column(String(50), primary_key=True, comment="Sleeper player_id")

    # Player Identity
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True, index=True)

    # Player Status
    status = Column(
        String(50), nullable=True, comment="Active, Inactive, Reserve, etc."
    )
    position = Column(String(10), nullable=True, index=True, comment="QB, RB, WR, TE, K, DEF")
    team = Column(String(10), nullable=True, index=True, comment="NFL team abbreviation")
    number = Column(Integer, nullable=True, comment="Jersey number")

    # Player Details
    age = Column(Integer, nullable=True)
    years_exp = Column(Integer, nullable=True, comment="Years of NFL experience")
    height = Column(String(20), nullable=True, comment="Height in inches or format")
    weight = Column(String(20), nullable=True, comment="Weight in pounds")
    college = Column(String(255), nullable=True)
    high_school = Column(String(255), nullable=True)
    birth_date = Column(String(50), nullable=True)
    birth_city = Column(String(255), nullable=True)
    birth_state = Column(String(100), nullable=True)
    birth_country = Column(String(100), nullable=True)

    # Identifiers
    espn_id = Column(String(50), nullable=True)
    yahoo_id = Column(String(50), nullable=True)
    fantasy_data_id = Column(String(50), nullable=True)
    rotowire_id = Column(String(50), nullable=True)
    sportradar_id = Column(String(50), nullable=True)
    gsis_id = Column(String(50), nullable=True)
    stats_id = Column(String(50), nullable=True)
    rotoworld_id = Column(String(50), nullable=True)

    # Player Metadata
    api_metadata = Column(
        JSONB,
        nullable=True,
        comment="Additional player metadata from Sleeper API",
    )

    # Injury Info
    injury_status = Column(String(50), nullable=True)
    injury_body_part = Column(String(100), nullable=True)
    injury_notes = Column(Text, nullable=True)
    injury_start_date = Column(String(50), nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    # Note: No back_populates from DraftPick - player_id is reference-only for ETL flexibility

    # Indexes
    __table_args__ = (
        Index("idx_players_full_name", "full_name"),
        Index("idx_players_position", "position"),
        Index("idx_players_team", "team"),
        Index("idx_players_status", "status"),
        Index("idx_players_position_team", "position", "team"),
        Index("idx_players_position_status", "position", "status"),
    )

    def __repr__(self) -> str:
        return f"<Player(player_id={self.player_id}, full_name={self.full_name}, position={self.position}, team={self.team})>"
