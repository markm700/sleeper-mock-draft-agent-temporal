from typing import List, Dict
from dataclasses import dataclass
from src.models.types import Player, BoomBustProfile
import statistics


@dataclass
class WeeklyPerformance:
    week: int
    points: float


def calculate_boom_bust_score(
    player: Player, historical_weeks: List[WeeklyPerformance]
) -> BoomBustProfile:
    """
    Calculate boom/bust score based on historical weekly variance
    Uses coefficient of variation (standard deviation / mean)
    """
    if not historical_weeks:
        return BoomBustProfile(
            type="balanced", score=0.3, recommendation="Insufficient data"
        )

    weekly_scores = [w.points for w in historical_weeks]
    mean = statistics.mean(weekly_scores)

    if mean == 0:
        return BoomBustProfile(type="balanced", score=0.3, recommendation="No data")

    std_dev = statistics.stdev(weekly_scores) if len(weekly_scores) > 1 else 0

    # Coefficient of variation
    coefficient = std_dev / mean

    # Classify player type
    if coefficient > 0.5:
        return BoomBustProfile(
            type="boom-bust", score=coefficient, recommendation="Late round lottery"
        )

    if coefficient < 0.2:
        return BoomBustProfile(
            type="floor", score=coefficient, recommendation="Safe early pick"
        )

    return BoomBustProfile(type="balanced", score=coefficient, recommendation="Flexible")


def recommend_by_boom_bust(
    players: List[Player], round_num: int, profiles: Dict[str, BoomBustProfile]
) -> List[Player]:
    """Recommend players based on boom/bust profile and draft stage"""
    # Early rounds (1-5): Prefer floor players
    if round_num <= 5:
        floor_players = [
            p for p in players if profiles.get(p.player_id, {}).get("type") == "floor"
        ]
        return sorted(
            floor_players, key=lambda p: profiles.get(p.player_id, {}).get("score", 1)
        )

    # Late rounds (12-15): Prefer boom-bust (lottery tickets)
    if round_num >= 12:
        boom_players = [
            p
            for p in players
            if profiles.get(p.player_id, {}).get("type") == "boom-bust"
        ]
        return sorted(
            boom_players,
            key=lambda p: profiles.get(p.player_id, {}).get("score", 0),
            reverse=True,
        )

    # Middle rounds: Balanced approach
    return players
