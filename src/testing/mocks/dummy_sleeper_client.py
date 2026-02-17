from typing import Any, Dict, List, Optional

class DummySleeperClient:
    """Stub client for Sleeper API used in tests.

    This dummy mirrors the subset of methods used by Temporal activities
    so tests can validate activity logic without real HTTP calls or
    environment variables.
    """

    def __init__(self) -> None:
        self.called_with_league_ids: List[str] = []
        self.called_with_draft_ids: List[str] = []
        self.called_with_league_names: List[str] = []
        self.called_with_usernames: List[str] = []
        self.called_user_leagues: List[Dict[str, Any]] = []

    # Draft Data
    async def get_league_drafts(self, league_id: str) -> List[Dict[str, Any]]:
        self.called_with_league_ids.append(league_id)
        return [
            {"league_id": league_id, "draft_id": "draft_1"},
            {"league_id": league_id, "draft_id": "draft_2"},
        ]

    async def get_draft_picks(self, draft_id: str) -> List[Dict[str, Any]]:
        self.called_with_draft_ids.append(draft_id)
        # Minimal, stable structure for testing get_specific_draft_picks
        return [
            {
                "draft_id": draft_id,
                "pick_no": 1,
                "player_id": "player_1",
                "roster_id": 1,
            },
            {
                "draft_id": draft_id,
                "pick_no": 2,
                "player_id": "player_2",
                "roster_id": 2,
            },
        ]

    # League Data
    async def get_league(self, league_name: str) -> Dict[str, Any]:
        self.called_with_league_names.append(league_name)
        # Map league_name (or league_id passed positionally) to a deterministic fake league_id
        league_id = f"league-{league_name}"
        return {
            "league_id": league_id,
            "name": league_name,
            "season": "2024",
        }

    async def get_league_users(
        self,
        league_name: Optional[str] = None,
        league_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return fake league users.

        Supports both call styles used by activities:
        - by league_name (historical behavior)
        - by league_id (current activities)
        """
        if league_id is not None:
            self.called_with_league_ids.append(league_id)
            league_key = league_id
        else:
            league_key = league_name or "unknown"
            self.called_with_league_names.append(league_key)

        # Two fake users associated with the league identifier
        return [
            {"user_id": "user_1", "display_name": f"owner_1_{league_key}"},
            {"user_id": "user_2", "display_name": f"owner_2_{league_key}"},
        ]

    async def get_league_rosters(self, league_name: Optional[str] = None, league_id: Optional[str] = None
                                 ) -> List[Dict[str, Any]]:
        # Support both call styles used by activities: by league name or id.
        if league_name is not None:
            self.called_with_league_names.append(league_name)
            league_key = league_name
        else:
            if league_id is not None:
                self.called_with_league_ids.append(league_id)
            league_key = league_id or "unknown"

        return [
            {
                "league_key": league_key,
                "roster_id": 1,
                "owner_id": "user_1",
                "players": ["player_1", "player_2"],
            },
            {
                "league_key": league_key,
                "roster_id": 2,
                "owner_id": "user_2",
                "players": ["player_3", "player_4"],
            },
        ]

    # User/Team Owner Data
    async def get_user(self, username: str) -> Dict[str, Any]:
        self.called_with_usernames.append(username)
        return {
            "user_id": f"user-{username}",
            "username": username,
            "display_name": f"Display {username}",
        }

    async def get_user_leagues(
        self,
        user_id: str,
        sport: str = "nfl",
        league_name: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        # Track calls for assertions if needed
        self.called_user_leagues.append(
            {"user_id": user_id, "sport": sport, "league_name": league_name}
        )

        # Minimal per-season fake league mapping
        seasons = ["2020", "2021", "2022", "2023", "2024"]
        leagues_by_season: Dict[str, List[Dict[str, Any]]] = {}
        for season in seasons:
            league = {
                "league_id": f"{league_name or 'league'}-{season}",
                "name": league_name or "Test League",
                "season": season,
                "sport": sport,
                "user_id": user_id,
            }
            leagues_by_season[season] = [league]
        return leagues_by_season