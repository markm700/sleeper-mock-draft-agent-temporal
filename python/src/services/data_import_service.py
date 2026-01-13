from typing import List
from src.api.sleeper_client import sleeper_client
from src.database.db import db
from src.config import config
from src.algorithms.draft_philosophy import detect_draft_philosophy


class DataImportService:
    """Service for importing historical draft data from Sleeper API"""

    async def import_historical_data(self, username: str) -> None:
        """Import all historical data for a user (2021-2025)"""
        print(f"Starting historical import for {username}...")

        # Step 1: Get user ID
        user = sleeper_client.get_user(username)
        user_id = user["user_id"]
        print(f"User ID: {user_id}")

        # Step 2: Loop through seasons
        for season in config.LEAGUE_SEASONS:
            print(f"\nImporting season {season}...")

            try:
                await self._import_season(user_id, season)
            except Exception as error:
                print(f"Error importing season {season}: {error}")

        # Step 3: Get player database
        print("\nImporting player database...")
        await self._import_players()

        # Step 4: Detect draft philosophies
        print("\nDetecting draft philosophies...")
        await self._detect_philosophies()

        print("\nHistorical import complete!")

    async def _import_season(self, user_id: str, season: int) -> None:
        """Import data for a single season"""
        leagues = sleeper_client.get_user_leagues(user_id, season)

        for league in leagues:
            league_id = league["league_id"]
            draft_id = league.get("draft_id")

            print(f"  League: {league['name']}")

            # Import draft data
            if draft_id:
                await self._import_draft(draft_id, season)

            # Import rosters and performance
            await self._import_rosters(league_id, season)

            # Import matchups (weeks 1-18)
            await self._import_matchups(league_id, season)

            # Import transactions (weeks 1-18)
            await self._import_transactions(league_id, season)

    async def _import_draft(self, draft_id: str, season: int) -> None:
        """Import draft data"""
        draft = sleeper_client.get_draft(draft_id)
        picks = sleeper_client.get_draft_picks(draft_id)
        traded_picks = sleeper_client.get_traded_picks(draft_id)

        # TODO: Store in database
        print(f"    Draft: {len(picks)} picks")

        # Flag outliers (e.g., year 5 toilet bowl)
        if season == 2025:
            await self._flag_outliers(picks)

    async def _import_rosters(self, league_id: str, season: int) -> None:
        """Import rosters and performance data"""
        rosters = sleeper_client.get_league_rosters(league_id)

        # TODO: Store wins/losses/points in database
        print(f"    Rosters: {len(rosters)} teams")

    async def _import_matchups(self, league_id: str, season: int) -> None:
        """Import matchups for all weeks"""
        import time

        for week in range(1, 19):
            try:
                matchups = sleeper_client.get_matchups(league_id, week)
                # TODO: Store in database
            except Exception:
                # Some weeks may not exist
                break

            # Rate limiting delay
            time.sleep(0.06)  # 60ms

    async def _import_transactions(self, league_id: str, season: int) -> None:
        """Import transactions for all weeks"""
        import time

        for week in range(1, 19):
            try:
                transactions = sleeper_client.get_transactions(league_id, week)
                # TODO: Store in database
            except Exception:
                # Some weeks may not exist
                break

            # Rate limiting delay
            time.sleep(0.06)  # 60ms

    async def _import_players(self) -> None:
        """Import player database"""
        players = sleeper_client.get_all_players()
        nfl_state = sleeper_client.get_nfl_state()

        # TODO: Store in database with timestamp
        print(f"  Players: {len(players)}")

        # Check for staleness
        await self._check_player_staleness(players)

    async def _check_player_staleness(self, players: dict) -> None:
        """Check if player data is stale (>30 days old)"""
        # TODO: Implement staleness check
        pass

    async def _flag_outliers(self, picks: List[dict]) -> None:
        """Flag outliers in draft data"""
        # TODO: Implement outlier detection
        # e.g., year 5 toilet bowl picks
        pass

    async def _detect_philosophies(self) -> None:
        """Detect draft philosophies for all owners"""
        # TODO: Query all owner picks and detect their philosophy
        # Store in users table
        pass


# Global instance
data_import_service = DataImportService()
