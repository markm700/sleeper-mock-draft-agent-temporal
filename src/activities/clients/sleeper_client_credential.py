import os
import httpx
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SleeperCredentialManager:
    # Sleeper API client manager
    # httpx.AsyncClient for native async support
    # Sleeper API is a read-only HTTP API that requires no auth
    # Rate limit: Stay under 1000 API calls per minute
    
    SLEEPER_BASE_URL = "https://api.sleeper.app/v1"
    REQUEST_TIMEOUT = 30.0  # seconds
    
    def __init__(self, user: Optional[str] = None, league: Optional[str] = None):
        # Initialize Sleeper API client with 
        username = user or os.getenv("SLEEPER_USERNAME")
        if not username:
            raise ValueError("Sleeper username not provided. Set SLEEPER_USERNAME environment variable.")
        else:
            # user data
            logger.info(f"SleeperCredentialManager initialized for user: {username}")
            self._user = username
            self._user_id = None  # Will be set when fetching user data
        league_name = league or os.getenv("SLEEPER_LEAGUE_NAME")
        if not league_name:
            raise ValueError("Sleeper league not provided. Set SLEEPER_LEAGUE_NAME environment variable.")
        else:
            logger.info(f"SleeperCredentialManager initialized with league: {league_name}")
            self._league = league_name
            self._league_id = None  # Will be set when fetching league data
        # connection pooling via httpx.AsyncClient
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        #  Get or create httpx.AsyncClient for connection pooling
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.REQUEST_TIMEOUT,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "sleeper-mock-draft-agent/1.0",
                },
            )
            logger.info("Initialized Sleeper API client")
        return self._client
    
    async def _get_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        # Make HTTP GET request to Sleeper API.
        # endpoint: API endpoint path without base URL (e.g. "user/12345")

        url = f"{self.SLEEPER_BASE_URL}/{endpoint}"
        logger.debug(f"Making request to {url}")
        
        response = await self.client.get(
            url,
            params=params,
        )
        
        response.raise_for_status()
        return response.json()
    
    async def get_user(self, username: Optional[str] = None) -> Dict[str, Any]:
        # Get user data by username/user_id
        user_to_get = username or self._user
        user_data = await self._get_request(f"user/{user_to_get}")
        self._user_id = user_data.get("user_id")
        return user_data
    
    async def get_user_leagues(
        self, user_id: str, sport: str = "nfl", league_name: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        # Get all leagues for a user across multiple seasons, optionally filter by league_name
        import datetime
        current_year = datetime.datetime.now().year
        results = {}
        for year in range(current_year - 6, current_year + 1):
            try:
                leagues = await self.get_user_league_season(user_id=user_id, season=str(year), sport=sport)
                if league_name:
                    filtered_leagues = [l for l in leagues if l.get("name") == league_name]
                    results[str(year)] = filtered_leagues
                else:
                    results[str(year)] = leagues
            except Exception as e:
                logger.error(f"Error fetching leagues for season {year}: {str(e)}")
                results[str(year)] = []
        return results
    
    async def get_user_league_season(self, user_id: str, season: str, sport: str = "nfl") -> List[Dict[str, Any]]:
        # Get all leagues for a user in a specific season (sport filter - nfl only supported by Sleeper API for now) 
        # league_id
        return await self._get_request(f"user/{user_id}/leagues/{sport}/{season}")
    
    async def get_league(self, league_id: str) -> Dict[str, Any]:
        # Get specific league data by league_id
        return await self._get_request(f"league/{league_id}")
    
    async def get_league_users(self, league_id: str) -> List[Dict[str, Any]]:
        # Get all league users (team owners)
        # user_id
        return await self._get_request(f"league/{league_id}/users")
                                       
    async def get_league_rosters(self, league_id: str) -> List[Dict[str, Any]]:
        # Get all league rosters (teams)
        return await self._get_request(f"league/{league_id}/rosters")
    
    async def get_traded_draft_picks(self, league_id: str) -> List[Dict[str, Any]]:
        #Get all traded draft picks from a specific draft
        return await self._get_request(f"league/{league_id}/traded_picks")
    
    async def get_league_drafts(self, league_id: str) -> List[Dict[str, Any]]:
        # Get all league drafts by league_id
        # draft_id
        return await self._get_request(f"league/{league_id}/drafts")
    
    async def get_draft(self, draft_id: str) -> Dict[str, Any]:
        # Get speciufic draft data by draft_id
        return await self._get_request(f"draft/{draft_id}")
    
    async def get_draft_picks(self, draft_id: str) -> List[Dict[str, Any]]:
        #Get all draft picks from a specific draft
        return await self._get_request(f"draft/{draft_id}/picks")
    
    async def get_nfl_players(self) -> Dict[str, Dict[str, Any]]:
        # Get all NFL players
        return await self._get_request("players/nfl")

    async def close(self):
        # Close the Sleeper API httpx.AsyncClient connection
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Closed Sleeper API client")


# Single instance for reuse across activities
_sleeper_client_instance: Optional[SleeperCredentialManager] = None
def get_sleeper_client_manager(user: Optional[str] = None) -> SleeperCredentialManager:
    # Get or create single Sleeper API client manager instance
    global _sleeper_client_instance
    if _sleeper_client_instance is None:
        if user is None:
            _sleeper_client_instance = SleeperCredentialManager()
        else:
            _sleeper_client_instance = SleeperCredentialManager(user=user)
    return _sleeper_client_instance