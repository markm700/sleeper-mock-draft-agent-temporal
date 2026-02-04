"""SQLAlchemy database models"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class League(Base):
    """League table"""
    __tablename__ = "leagues"
    
    league_id = Column(String(50), primary_key=True)
    name = Column(String(255))
    season = Column(String(10))
    status = Column(String(50))
    total_rosters = Column(Integer)
    scoring_settings = Column(JSONB)
    roster_positions = Column(JSONB)
    settings = Column(JSONB)
    previous_league_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    drafts = relationship("Draft", back_populates="league")
    rosters = relationship("Roster", back_populates="league")
    transactions = relationship("Transaction", back_populates="league")
    league_owners = relationship("LeagueOwner", back_populates="league")


class LeagueOwner(Base):
    """League owners/users table"""
    __tablename__ = "league_owners"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False)
    username = Column(String(255))
    display_name = Column(String(255))
    league_id = Column(String(50), ForeignKey("leagues.league_id"))
    is_owner = Column(Boolean, default=False)
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    league = relationship("League", back_populates="league_owners")


class Draft(Base):
    """Drafts table"""
    __tablename__ = "drafts"
    
    draft_id = Column(String(50), primary_key=True)
    league_id = Column(String(50), ForeignKey("leagues.league_id"))
    type = Column(String(50))
    status = Column(String(50))
    start_time = Column(BigInteger)
    season = Column(String(10))
    settings = Column(JSONB)
    metadata = Column(JSONB)
    draft_order = Column(JSONB)
    slot_to_roster_id = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    league = relationship("League", back_populates="drafts")
    picks = relationship("Pick", back_populates="draft")
    
    # Indexes
    __table_args__ = (
        Index("idx_drafts_league_id", "league_id"),
        Index("idx_drafts_season", "season"),
    )


class Pick(Base):
    """Draft picks table"""
    __tablename__ = "picks"
    
    id = Column(Integer, primary_key=True)
    pick_no = Column(Integer, nullable=False)
    draft_id = Column(String(50), ForeignKey("drafts.draft_id"))
    player_id = Column(String(50), nullable=False)
    picked_by = Column(String(50))
    roster_id = Column(String(50))
    round = Column(Integer)
    draft_slot = Column(Integer)
    is_keeper = Column(Boolean)
    metadata = Column(JSONB)  # Snapshot of player info at draft time
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    draft = relationship("Draft", back_populates="picks")
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("draft_id", "pick_no", name="uq_draft_pick"),
        Index("idx_picks_draft_id", "draft_id"),
        Index("idx_picks_player_id", "player_id"),
    )


class Player(Base):
    """Players table"""
    __tablename__ = "players"
    
    player_id = Column(String(50), primary_key=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    position = Column(String(10))
    team = Column(String(10))
    fantasy_positions = Column(JSONB)
    depth_chart_position = Column(Integer)
    status = Column(String(50))
    injury_status = Column(String(255))
    search_rank = Column(Integer)
    metadata = Column(JSONB)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_players_position", "position"),
        Index("idx_players_team", "team"),
        Index(
            "idx_players_name_gin",
            text("to_tsvector('english', first_name || ' ' || last_name)"),
            postgresql_using="gin"
        ),
    )


class Roster(Base):
    """Rosters table"""
    __tablename__ = "rosters"
    
    id = Column(Integer, primary_key=True)
    roster_id = Column(Integer, nullable=False)
    league_id = Column(String(50), ForeignKey("leagues.league_id"))
    owner_id = Column(String(50))
    players = Column(JSONB)
    starters = Column(JSONB)
    settings = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    league = relationship("League", back_populates="rosters")
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("league_id", "roster_id", name="uq_league_roster"),
        Index("idx_rosters_league_id", "league_id"),
    )


class Transaction(Base):
    """Transactions table"""
    __tablename__ = "transactions"
    
    transaction_id = Column(String(50), primary_key=True)
    league_id = Column(String(50), ForeignKey("leagues.league_id"))
    type = Column(String(50))
    status = Column(String(50))
    leg = Column(Integer)
    roster_ids = Column(JSONB)
    adds = Column(JSONB)
    drops = Column(JSONB)
    draft_picks = Column(JSONB)
    settings = Column(JSONB)
    created = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    league = relationship("League", back_populates="transactions")
    
    # Indexes
    __table_args__ = (
        Index("idx_transactions_league_id", "league_id"),
    )


class ADPCache(Base):
    """Pre-calculated ADP table for performance"""
    __tablename__ = "adp_cache"
    
    id = Column(Integer, primary_key=True)
    league_id = Column(String(50))
    player_id = Column(String(50))
    season = Column(String(10))
    avg_pick = Column(Numeric(5, 2))
    std_dev = Column(Numeric(5, 2))
    sample_size = Column(Integer)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("league_id", "player_id", "season", name="uq_adp_league_player_season"),
        Index("idx_adp_league_season", "league_id", "season"),
    )
