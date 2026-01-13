import requests
import time
from typing import Dict, List, Any, Callable
from src.config import config


class SleeperClient:
    """
    Sleeper API Client
    Handles all interactions with the Sleeper API
    Rate limit: <1000 requests/minute
    """

    def __init__(self):
        self.base_url = config.SLEEPER_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "sleeper-mock-draft-agent/1.0"})

    def get_user(self, username: str) -> Dict[str, Any]:
        """Get user ID from username"""
        response = self.session.get(f"{self.base_url}/user/{username}")
        response.raise_for_status()
        return response.json()

    def get_user_leagues(self, user_id: str, season: int) -> List[Dict[str, Any]]:
        """Get user's leagues for a specific season"""
        response = self.session.get(
            f"{self.base_url}/user/{user_id}/leagues/nfl/{season}"
        )
        response.raise_for_status()
        return response.json()

    def get_draft(self, draft_id: str) -> Dict[str, Any]:
        """Get draft details"""
        response = self.session.get(f"{self.base_url}/draft/{draft_id}")
        response.raise_for_status()
        return response.json()

    def get_draft_picks(self, draft_id: str) -> List[Dict[str, Any]]:
        """Get all picks from a draft"""
        response = self.session.get(f"{self.base_url}/draft/{draft_id}/picks")
        response.raise_for_status()
        return response.json()

    def get_traded_picks(self, draft_id: str) -> List[Dict[str, Any]]:
        """Get traded picks from a draft"""
        response = self.session.get(f"{self.base_url}/draft/{draft_id}/traded_picks")
        response.raise_for_status()
        return response.json()

    def get_league_rosters(self, league_id: str) -> List[Dict[str, Any]]:
        """Get league rosters"""
        response = self.session.get(f"{self.base_url}/league/{league_id}/rosters")
        response.raise_for_status()
        return response.json()

    def get_matchups(self, league_id: str, week: int) -> List[Dict[str, Any]]:
        """Get matchups for a specific week"""
        response = self.session.get(
            f"{self.base_url}/league/{league_id}/matchups/{week}"
        )
        response.raise_for_status()
        return response.json()

    def get_transactions(self, league_id: str, week: int) -> List[Dict[str, Any]]:
        """Get transactions for a specific week"""
        response = self.session.get(
            f"{self.base_url}/league/{league_id}/transactions/{week}"
        )
        response.raise_for_status()
        return response.json()

    def get_all_players(self) -> Dict[str, Any]:
        """
        Get all NFL players (should be cached daily)
        Returns ~5MB of data
        """
        response = self.session.get(f"{self.base_url}/players/nfl")
        response.raise_for_status()
        return response.json()

    def get_nfl_state(self) -> Dict[str, Any]:
        """Get current NFL state (season, week)"""
        response = self.session.get(f"{self.base_url}/state/nfl")
        response.raise_for_status()
        return response.json()

    def sequential_calls(
        self, calls: List[Callable], delay_ms: int = 60
    ) -> List[Any]:
        """Rate-limited sequential API call helper"""
        results = []
        for call in calls:
            results.append(call())
            time.sleep(delay_ms / 1000)
        return results


# Global instance
sleeper_client = SleeperClient()
