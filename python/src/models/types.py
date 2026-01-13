from typing import Optional, Dict, List
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class Position(str, Enum):
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    K = "K"
    DEF = "DEF"


class DraftPhilosophy(str, Enum):
    ZERO_RB = "Zero-RB"
    HERO_RB = "Hero-RB"
    ROBUST_RB = "Robust-RB"
    WR_HEAVY = "WR-Heavy"
    BALANCED = "Balanced"


class Player(BaseModel):
    player_id: str
    name: str
    position: Position
    team: str
    boom_bust_score: Optional[float] = None
    last_updated: Optional[datetime] = None


class User(BaseModel):
    user_id: str
    username: str
    draft_philosophy: Optional[DraftPhilosophy] = None


class Draft(BaseModel):
    draft_id: str
    season: int
    draft_order: Dict
    slot_to_roster_id: Dict[int, str]


class DraftPick(BaseModel):
    pick_id: str
    draft_id: str
    player_id: str
    user_id: str
    round: int
    pick_no: int
    is_keeper: bool = False


class ManagerTendency(BaseModel):
    user_id: str
    round: int
    position: str
    frequency: float
    avg_reach_rounds: float
    philosophy: Optional[str] = None


class KeeperPrediction(BaseModel):
    season: int
    roster_id: str
    player_id: str
    predicted_round: int
    confidence: float
    is_combo_optimal: bool
    value: float


class DraftState(BaseModel):
    draft_session_id: str
    current_pick: int
    available_players: List[Player]
    picked_players: List[DraftPick]


class ValueAlert(BaseModel):
    alert_id: str
    player_id: str
    rounds_late: float
    triggered_at: datetime


class BoomBustProfile(BaseModel):
    type: str  # 'boom-bust', 'floor', 'balanced'
    score: float
    recommendation: str


class PositionRun(BaseModel):
    detected: bool
    position: Optional[str] = None
    count: Optional[int] = None


class PanicPick(BaseModel):
    is_panic: bool
    confidence: Optional[float] = None
    reason: Optional[str] = None


class StackingRecommendation(BaseModel):
    qb_id: str
    wr_id: str
    team: str
    expected_value: float
    correlation: float


class DraftRecommendation(BaseModel):
    player_id: str
    name: str
    position: str
    rank: int
    ceiling_rank: Optional[int] = None
    confidence: float
    boom_bust_score: Optional[str] = None
    philosophy_match: Optional[str] = None
    rounds_late: Optional[float] = None


class LiveDraftResponse(BaseModel):
    recommendations: Dict[str, List]
    alerts: Dict[str, Optional[str | List[str]]]
    predicted_next_pick: Dict[str, any]
    grades: Dict[str, str]
    draft_position_insight: Optional[str] = None


class ExternalADP(BaseModel):
    player_id: str
    source: str  # 'sleeper', 'espn', 'fantasypros', 'yahoo'
    adp: float
    weight: float


class KeeperValue(BaseModel):
    player: Player
    keep_cost: int
    projected_round: int
    base_value: float
    opportunity_cost: float
    total_value: float
    confidence: float


class KeeperCombo(BaseModel):
    players: List[Player]
    total_value: float
    position_diversity: float
