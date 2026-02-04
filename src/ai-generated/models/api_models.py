"""API response models (dataclasses for type safety)"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class UserResponse:
    """Sleeper API user response"""
    user_id: str
    username: str
    display_name: str
    avatar: Optional[str] = None


@dataclass
class LeagueResponse:
    """Sleeper API league response"""
    league_id: str
    name: str
    season: str
    status: str
    draft_id: Optional[str] = None
    total_rosters: Optional[int] = None
    roster_positions: Optional[List[str]] = None
    scoring_settings: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    previous_league_id: Optional[str] = None


@dataclass
class DraftResponse:
    """Sleeper API draft response"""
    draft_id: str
    league_id: str
    type: str
    status: str
    start_time: int
    season: str
    settings: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    draft_order: Optional[Dict[str, int]] = None
    slot_to_roster_id: Optional[Dict[str, int]] = None


@dataclass
class PickResponse:
    """Sleeper API pick response"""
    player_id: str
    picked_by: str
    roster_id: str
    round: int
    draft_slot: int
    pick_no: int
    draft_id: str
    metadata: Optional[Dict[str, Any]] = None
    is_keeper: Optional[bool] = None


@dataclass
class PlayerResponse:
    """Sleeper API player response"""
    player_id: str
    first_name: str
    last_name: str
    position: str
    team: Optional[str] = None
    fantasy_positions: Optional[List[str]] = None
    depth_chart_position: Optional[int] = None
    status: Optional[str] = None
    injury_status: Optional[str] = None
    search_rank: Optional[int] = None
