"""Sleeper API Client Activities - All API interactions with rate limiting"""

import logging
from typing import Any, Dict, List, Optional

import httpx
from temporalio import activity

from src.utils.config import get_config

logger = logging.getLogger(__name__)

# Sleeper API configuration
SLEEPER_API_BASE = "https://api.sleeper.app/v1"
RATE_LIMIT_PER_MINUTE = 1000  # Stay under 1000 calls per minute


class SleeperAPIClient:
    """Client for Sleeper API with rate limiting"""

    def __init__(self):
        self.config = get_config()
        self.base_url = SLEEPER_API_BASE
        self._client: Optional[httpx.AsyncClient] = None
        # TODO: Implement rate limiting queue
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "sleeper-mock-draft-agent/1.0",
                },
            )
        return self._client

    async def _make_request(self, endpoint: str) -> Any:
        """Make HTTP request to Sleeper API with error handling"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API request failed for {endpoint}: {str(e)}")
            raise


# Global client instance
_client = SleeperAPIClient()


@activity.defn
async def fetch_user(username_or_id: str) -> Dict[str, Any]:
    """
    Fetch user information from Sleeper API.
    
    Args:
        username_or_id: Username or user_id
        
    Returns:
        User data dictionary
    """
    activity.logger.info(f"Fetching user: {username_or_id}")
    
    try:
        user_data = await _client._make_request(f"user/{username_or_id}")
        
        activity.logger.info(f"Successfully fetched user: {user_data.get('user_id')}")
        return user_data
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch user {username_or_id}: {str(e)}")
        raise


@activity.defn
async def fetch_user_leagues(params: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Fetch all leagues for a user in a specific sport and season.
    
    Args:
        params: Dict with user_id, sport, season
        
    Returns:
        List of league dictionaries
    """
    user_id = params["user_id"]
    sport = params["sport"]
    season = params["season"]
    
    activity.logger.info(f"Fetching leagues for user {user_id}, {sport} {season}")
    
    try:
        leagues = await _client._make_request(
            f"user/{user_id}/leagues/{sport}/{season}"
        )
        
        activity.logger.info(f"Found {len(leagues)} leagues")
        return leagues
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch leagues: {str(e)}")
        raise


@activity.defn
async def fetch_league_details(league_id: str) -> Dict[str, Any]:
    """Fetch detailed information about a specific league"""
    activity.logger.info(f"Fetching league details: {league_id}")
    
    try:
        league_data = await asyncio.to_thread(
            _client._make_request,
            f"league/{league_id}"
        )
        
        return league_data
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch league details: {str(e)}")
        raise


@activity.defn
async def fetch_league_rosters(league_id: str) -> List[Dict[str, Any]]:
    """Fetch all rosters in a league"""
    activity.logger.info(f"Fetching rosters for league: {league_id}")
    
    try:
        rosters = await asyncio.to_thread(
            _client._make_request,
            f"league/{league_id}/rosters"
        )
        
        activity.logger.info(f"Found {len(rosters)} rosters")
        return rosters
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch rosters: {str(e)}")
        raise


@activity.defn
async def fetch_league_users(league_id: str) -> List[Dict[str, Any]]:
    """Fetch all users in a league"""
    activity.logger.info(f"Fetching users for league: {league_id}")
    
    try:
        users = await asyncio.to_thread(
            _client._make_request,
            f"league/{league_id}/users"
        )
        
        activity.logger.info(f"Found {len(users)} users")
        return users
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch users: {str(e)}")
        raise


@activity.defn
async def fetch_league_drafts(league_id: str) -> List[Dict[str, Any]]:
    """Fetch all drafts for a league"""
    activity.logger.info(f"Fetching drafts for league: {league_id}")
    
    try:
        drafts = await asyncio.to_thread(
            _client._make_request,
            f"league/{league_id}/drafts"
        )
        
        activity.logger.info(f"Found {len(drafts)} drafts")
        return drafts
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch drafts: {str(e)}")
        raise


@activity.defn
async def fetch_draft_picks(draft_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all picks in a draft.
    
    This is critical for training the mock draft agent.
    """
    activity.logger.info(f"Fetching picks for draft: {draft_id}")
    
    try:
        picks = await asyncio.to_thread(
            _client._make_request,
            f"draft/{draft_id}/picks"
        )
        
        activity.logger.info(f"Found {len(picks)} picks")
        return picks
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch picks: {str(e)}")
        raise


@activity.defn
async def fetch_players_database(sport: str = "nfl") -> Dict[str, Any]:
    """
    Fetch complete player database from Sleeper.
    
    WARNING: Response is ~5MB. Call once per day maximum.
    """
    activity.logger.info(f"Fetching player database for {sport}")
    activity.logger.warning("Large response (~5MB) - ensure this runs infrequently")
    
    try:
        players = await asyncio.to_thread(
            _client._make_request,
            f"players/{sport}"
        )
        
        activity.logger.info(f"Fetched {len(players)} players")
        return players
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch player database: {str(e)}")
        raise


@activity.defn
async def fetch_matchups(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch matchups for a specific week in a league"""
    league_id = params["league_id"]
    week = params["week"]
    
    activity.logger.info(f"Fetching matchups for league {league_id}, week {week}")
    
    try:
        matchups = await asyncio.to_thread(
            _client._make_request,
            f"league/{league_id}/matchups/{week}"
        )
        
        return matchups
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch matchups: {str(e)}")
        raise


@activity.defn
async def fetch_transactions(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch transactions for a specific round/week in a league"""
    league_id = params["league_id"]
    round_num = params["round"]
    
    activity.logger.info(f"Fetching transactions for league {league_id}, round {round_num}")
    
    try:
        transactions = await asyncio.to_thread(
            _client._make_request,
            f"league/{league_id}/transactions/{round_num}"
        )
        
        return transactions
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch transactions: {str(e)}")
        raise


@activity.defn
async def fetch_nfl_state() -> Dict[str, Any]:
    """Fetch current NFL season state"""
    activity.logger.info("Fetching NFL state")
    
    try:
        state = await asyncio.to_thread(
            _client._make_request,
            "state/nfl"
        )
        
        return state
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch NFL state: {str(e)}")
        raise


@activity.defn
async def fetch_trending_players(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch trending players (adds/drops)"""
    sport = params.get("sport", "nfl")
    trend_type = params.get("type", "add")  # add or drop
    lookback_hours = params.get("lookback_hours", 24)
    limit = params.get("limit", 25)
    
    activity.logger.info(f"Fetching trending {trend_type} players")
    
    try:
        trending = await asyncio.to_thread(
            _client._make_request,
            f"players/{sport}/trending/{trend_type}?lookback_hours={lookback_hours}&limit={limit}"
        )
        
        return trending
        
    except Exception as e:
        activity.logger.error(f"Failed to fetch trending players: {str(e)}")
        raise
