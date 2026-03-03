from typing import Any, Dict, List, Optional

class DummySleeperClient:
    """Stub client for Sleeper API used in tests.

    This dummy mirrors the subset of methods used by Temporal activities
    so tests can validate activity logic without real HTTP calls or
    environment variables.
    """

    def __init__(self, incomplete_data: bool = False) -> None:
        self.called_with_league_ids: List[str] = []
        self.called_with_draft_ids: List[str] = []
        self.called_with_league_names: List[str] = []
        self.called_with_usernames: List[str] = []
        self.called_user_leagues: List[Dict[str, Any]] = []
        self.incomplete_data = incomplete_data  # For testing safe dictionary access

    # Draft Data
    async def get_league_drafts(self, league_id: str) -> List[Dict[str, Any]]:
        self.called_with_league_ids.append(league_id)
        return [
            {
                "league_id": league_id,
                "draft_id": "draft_1",
                "type": "snake",
                "status": "complete",
                "season": "2024",
                "season_type": "regular",
                "draft_order": {"1": 1, "2": 2},
                "settings": {"rounds": 15},
                "metadata": {"name": "Draft 1"},
                "creator": "user_1",
                "created": 1609459200000,
            },
            {
                "league_id": league_id,
                "draft_id": "draft_2",
                "type": "auction",
                "status": "pre_draft",
                "season": "2024",
                "season_type": "regular",
                "draft_order": None,
                "settings": {"rounds": 16},
                "metadata": {},
                "creator": "user_2",
                "created": 1609545600000,
            },
        ]

    async def get_draft_picks(self, draft_id: str) -> List[Dict[str, Any]]:
        self.called_with_draft_ids.append(draft_id)
        # Complete structure for testing get_specific_draft_picks with DB upsert
        return [
            {
                "draft_id": draft_id,
                "pick_id": f"{draft_id}_pick_1",
                "pick_no": 1,
                "round": 1,
                "draft_slot": 1,
                "player_id": "player_1",
                "roster_id": 1,
                "picked_by": "user_1",
            },
            {
                "draft_id": draft_id,
                "pick_id": f"{draft_id}_pick_2",
                "pick_no": 2,
                "round": 1,
                "draft_slot": 2,
                "player_id": "player_2",
                "roster_id": 2,
                "picked_by": "user_2",
            },
        ]

    async def get_traded_draft_picks(self, league_id: str) -> List[Dict[str, Any]]:
        self.called_with_league_ids.append(league_id)
        # Return traded picks from multiple seasons to test filtering
        return [
            {
                "pick_id": "traded_pick_1",
                "season": "2024",
                "round": 1,
                "roster_id": 2,
                "previous_owner_id": "1",
                "owner_id": "2",
            },
            {
                "pick_id": "traded_pick_2",
                "season": "2025",
                "round": 2,
                "roster_id": 1,
                "previous_owner_id": "2",
                "owner_id": "1",
            },
            {
                "pick_id": "traded_pick_3",
                "season": "2025",
                "round": 3,
                "roster_id": 2,
                "previous_owner_id": "1",
                "owner_id": "2",
            },
            {
                "pick_id": "traded_pick_4",
                "season": "2026",
                "round": 1,
                "roster_id": 1,
                "previous_owner_id": "2",
                "owner_id": "1",
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
            "season_type": "regular",
            "previous_league_id": None,
            "draft_id": "draft_123",
            "shard": 1,
            "roster_positions": ["QB", "RB", "WR", "TE", "FLEX", "K", "DEF"],
            "total_rosters": 2,
            "settings": {"num_teams": 2},
            "scoring_settings": {"pass_td": 4},
            "metadata": {"custom": "data"},
            "status": "in_season",
            "bracket_id": None,
            "loser_bracket_id": None,
            "bracket_overrides_id": None,
            "loser_bracket_overrides_id": None,
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

        # Return users with missing fields if incomplete_data flag is set
        if self.incomplete_data:
            return [
                {
                    "user_id": "user_1",
                    "username": "testuser1",
                    "display_name": f"owner_1_{league_key}",
                    "real_name": None,
                    "is_bot": False,
                },
                {
                    # Missing user_id to test safe access and record skipping
                    "username": "testuser_missing_id",
                    "display_name": f"owner_missing_{league_key}",
                    "is_bot": False,
                },
                {
                    "user_id": "user_2",
                    # Missing username to test fallback to display_name
                    "display_name": f"owner_2_{league_key}",
                    "real_name": "Real User 2",
                    "is_bot": False,
                },
            ]

        # Two fake users associated with the league identifier
        return [
            {
                "user_id": "user_1",
                "username": "testuser1",
                "display_name": f"owner_1_{league_key}",
                "real_name": None,
                "is_bot": False,
            },
            {
                "user_id": "user_2",
                "username": "testuser2",
                "display_name": f"owner_2_{league_key}",
                "real_name": "Real User 2",
                "is_bot": False,
            },
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
                "starters": ["player_1"],
                "keepers": [],
                "roster_settings": {},
                "reserve": [],
                "taxi": [],
                "co_owners": None,
                "metadata": {},
            },
            {
                "league_key": league_key,
                "roster_id": 2,
                "owner_id": "user_2",
                "players": ["player_3", "player_4"],
                "starters": ["player_3"],
                "keepers": ["player_3"],
                "roster_settings": {"wins": 5},
                "reserve": [],
                "taxi": [],
                "co_owners": None,
                "metadata": {"streak": "2W"},
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