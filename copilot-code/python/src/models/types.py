"""Pydantic models for type safety"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Player(BaseModel):
    """NFL Player model"""
    player_id: str
    first_name: str
    last_name: str
    position: str
    team: Optional[str] = None
    age: Optional[int] = None
    status: Optional[str] = None


class User(BaseModel):
    """Sleeper user model"""
    user_id: str
    username: str
    display_name: str


class Draft(BaseModel):
    """Draft information model"""
    draft_id: str
    league_id: str
    season: int
    type: str
    status: str
    settings: Dict[str, Any]


class DraftPick(BaseModel):
    """Individual draft pick model"""
    pick_number: int
    round: int
    draft_slot: int
    player_id: str
    picked_by: str
    is_keeper: bool = False
    metadata: Optional[Dict[str, Any]] = None


class ManagerTendency(BaseModel):
    """Manager draft tendency analysis"""
    user_id: str
    avg_rb_round: float
    avg_wr_round: float
    avg_qb_round: float
    avg_te_round: float
    rb_heavy: bool
    wr_heavy: bool
    position_flexibility: float


class KeeperPrediction(BaseModel):
    """Keeper value prediction"""
    user_id: str
    player_id: str
    keeper_round: int
    expected_value: float
    opportunity_cost: float
    confidence: float


class DraftState(BaseModel):
    """Current state of an ongoing draft"""
    draft_id: str
    current_pick: int
    available_players: List[str]
    rosters: Dict[str, List[str]]


class ValueAlert(BaseModel):
    """Value pick opportunity alert"""
    player_id: str
    current_pick: int
    expected_pick: int
    value_score: float
    reason: str


class BoomBustProfile(BaseModel):
    """Player variance analysis"""
    player_id: str
    boom_rate: float
    bust_rate: float
    consistency_score: float
    variance: float


class PositionRun(BaseModel):
    """Position run detection"""
    position: str
    start_pick: int
    consecutive_picks: int
    scarcity_multiplier: float


class PanicPick(BaseModel):
    """Panic pick detection"""
    user_id: str
    pick_number: int
    player_id: str
    position: str
    deviation_score: float


class StackingRecommendation(BaseModel):
    """QB-WR stacking recommendation"""
    qb_id: str
    wr_ids: List[str]
    correlation_score: float
    team: str


class DraftRecommendation(BaseModel):
    """Draft pick recommendation"""
    player_id: str
    player_name: str
    position: str
    reason: str
    confidence: float
    value_score: float


class LiveDraftResponse(BaseModel):
    """Live draft recommendation response"""
    current_pick: int
    recommendations: List[DraftRecommendation]
    value_alerts: List[ValueAlert]
    position_runs: List[PositionRun]
    stacking_recommendations: List[StackingRecommendation]
