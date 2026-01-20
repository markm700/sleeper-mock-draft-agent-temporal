"""Sleeper API client"""
import logging
import requests
from typing import Dict, List, Optional, Any
from src.config import config

logger = logging.getLogger(__name__)


class SleeperClient:
    """Client for Sleeper API"""
    
    def __init__(self):
        self.base_url = config.sleeper['base_url']
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def _make_request(self, endpoint: str) -> Any:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            logger.error(f'API request failed: {url}', exc_info=True)
            raise
    
    # User endpoints
    def get_user(self, username: str) -> Dict:
        """Get user ID from username"""
        try:
            return self._make_request(f'/user/{username}')
        except Exception as error:
            logger.error(f'Failed to get user {username}', exc_info=True)
            raise
    
    # League endpoints
    def get_user_leagues(self, user_id: str, season: int) -> List[Dict]:
        """Get all leagues for a user in a season"""
        try:
            return self._make_request(f'/user/{user_id}/leagues/nfl/{season}')
        except Exception as error:
            logger.error(f'Failed to get leagues for user {user_id}, season {season}', exc_info=True)
            raise
    
    def get_league(self, league_id: str) -> Dict:
        """Get league details"""
        try:
            return self._make_request(f'/league/{league_id}')
        except Exception as error:
            logger.error(f'Failed to get league {league_id}', exc_info=True)
            raise
    
    def get_league_rosters(self, league_id: str) -> List[Dict]:
        """Get all rosters in a league"""
        try:
            return self._make_request(f'/league/{league_id}/rosters')
        except Exception as error:
            logger.error(f'Failed to get rosters for league {league_id}', exc_info=True)
            raise
    
    def get_league_users(self, league_id: str) -> List[Dict]:
        """Get all users in a league"""
        try:
            return self._make_request(f'/league/{league_id}/users')
        except Exception as error:
            logger.error(f'Failed to get users for league {league_id}', exc_info=True)
            raise
    
    def get_league_matchups(self, league_id: str, week: int) -> List[Dict]:
        """Get matchups for a specific week"""
        try:
            return self._make_request(f'/league/{league_id}/matchups/{week}')
        except Exception as error:
            logger.error(f'Failed to get matchups for league {league_id}, week {week}', exc_info=True)
            raise
    
    def get_league_transactions(self, league_id: str, round_num: int) -> List[Dict]:
        """Get transactions for a league"""
        try:
            return self._make_request(f'/league/{league_id}/transactions/{round_num}')
        except Exception as error:
            logger.error(f'Failed to get transactions for league {league_id}', exc_info=True)
            raise
    
    # Draft endpoints
    def get_draft(self, draft_id: str) -> Dict:
        """Get draft details"""
        try:
            return self._make_request(f'/draft/{draft_id}')
        except Exception as error:
            logger.error(f'Failed to get draft {draft_id}', exc_info=True)
            raise
    
    def get_draft_picks(self, draft_id: str) -> List[Dict]:
        """Get all picks from a draft"""
        try:
            return self._make_request(f'/draft/{draft_id}/picks')
        except Exception as error:
            logger.error(f'Failed to get picks for draft {draft_id}', exc_info=True)
            raise
    
    def get_traded_picks(self, draft_id: str) -> List[Dict]:
        """Get traded draft picks"""
        try:
            return self._make_request(f'/draft/{draft_id}/traded_picks')
        except Exception as error:
            logger.error(f'Failed to get traded picks for draft {draft_id}', exc_info=True)
            raise
    
    # Player endpoints
    def get_all_players(self) -> Dict[str, Dict]:
        """Get all NFL players (~5MB, should be cached)"""
        try:
            logger.info('Fetching all NFL players (~5MB)...')
            players = self._make_request('/players/nfl')
            logger.info(f'Fetched {len(players)} players')
            return players
        except Exception as error:
            logger.error('Failed to fetch players', exc_info=True)
            raise


# Singleton instance
sleeper_client = SleeperClient()
