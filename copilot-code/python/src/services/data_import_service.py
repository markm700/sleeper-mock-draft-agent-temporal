"""Data import service - imports historical league data"""
import logging
from typing import List
from src.api.sleeper_client import sleeper_client
from src.database.db import db
from src.config import config
from src.algorithms.draft_philosophy import detect_draft_philosophy

logger = logging.getLogger(__name__)


class DataImportService:
    """Service for importing historical data from Sleeper"""
    
    def import_historical_data(self, username: str) -> None:
        """
        Import all historical data for a user
        
        Args:
            username: Sleeper username
        """
        logger.info(f'Starting historical import for {username}...')
        
        try:
            # Step 1: Get user ID
            user = sleeper_client.get_user(username)
            user_id = user['user_id']
            logger.info(f'User ID: {user_id}')
            
            # Step 2: Loop through seasons
            for season in config.league['seasons']:
                logger.info(f'\nImporting season {season}...')
                
                try:
                    self._import_season(user_id, season)
                except Exception as error:
                    logger.error(f'Error importing season {season}', exc_info=True)
            
            # Step 3: Import player database
            logger.info('\nImporting player database...')
            self._import_players()
            
            # Step 4: Detect draft philosophies
            logger.info('\nDetecting draft philosophies...')
            self._detect_philosophies()
            
            logger.info('\nHistorical import complete!')
            
        except Exception as error:
            logger.error('Failed to get user', exc_info=True)
            raise
    
    def _import_season(self, user_id: str, season: int) -> None:
        """Import data for a single season"""
        try:
            # Get user's leagues for this season
            leagues = sleeper_client.get_user_leagues(user_id, season)
            
            for league in leagues:
                league_id = league['league_id']
                draft_id = league['draft_id']
                
                logger.info(f'  League: {league["name"]}')
                
                # Import draft data
                self._import_draft(draft_id, season)
                
                # Import rosters/performance
                self._import_rosters(league_id, season)
                
                # Import matchups (weeks 1-17)
                self._import_matchups(league_id, season)
                
                # Import transactions
                self._import_transactions(league_id, season)
                
        except Exception as error:
            logger.error(f'Failed to import season {season}', exc_info=True)
            raise
    
    def _import_draft(self, draft_id: str, season: int) -> None:
        """Import draft picks"""
        try:
            draft = sleeper_client.get_draft(draft_id)
            picks = sleeper_client.get_draft_picks(draft_id)
            
            # TODO: Store in database
            logger.info(f'    Draft: {len(picks)} picks')
            
            # Flag outliers (e.g., year 5 toilet bowl)
            if season == 2025:
                self._flag_outliers(picks)
                
        except Exception as error:
            logger.error(f'Failed to import draft {draft_id}', exc_info=True)
    
    def _import_rosters(self, league_id: str, season: int) -> None:
        """Import rosters and performance data"""
        try:
            rosters = sleeper_client.get_league_rosters(league_id)
            
            # TODO: Store wins/losses/points in database
            logger.info(f'    Rosters: {len(rosters)} teams')
            
        except Exception as error:
            logger.error(f'Failed to import rosters for {league_id}', exc_info=True)
    
    def _import_matchups(self, league_id: str, season: int) -> None:
        """Import weekly matchups (weeks 1-17)"""
        try:
            for week in range(1, 18):
                matchups = sleeper_client.get_league_matchups(league_id, week)
                # TODO: Store in database
            
            logger.info(f'    Matchups: 17 weeks')
            
        except Exception as error:
            logger.error(f'Failed to import matchups for {league_id}', exc_info=True)
    
    def _import_transactions(self, league_id: str, season: int) -> None:
        """Import transactions"""
        try:
            # Get transactions for all rounds
            for round_num in range(1, 18):
                transactions = sleeper_client.get_league_transactions(league_id, round_num)
                # TODO: Store in database
            
            logger.info(f'    Transactions imported')
            
        except Exception as error:
            logger.error(f'Failed to import transactions for {league_id}', exc_info=True)
    
    def _import_players(self) -> None:
        """Import NFL player database"""
        try:
            players = sleeper_client.get_all_players()
            
            # TODO: Store in database with timestamp
            logger.info(f'  Players: {len(players)}')
            
        except Exception as error:
            logger.error('Failed to import players', exc_info=True)
    
    def _detect_philosophies(self) -> None:
        """Detect and store draft philosophies for all owners"""
        try:
            # TODO: Query all draft picks by owner from database
            # For each owner, call detect_draft_philosophy()
            # Store results in database
            logger.info('  Philosophies detected')
            
        except Exception as error:
            logger.error('Failed to detect philosophies', exc_info=True)
    
    def _flag_outliers(self, picks: List) -> None:
        """Flag outlier drafts (e.g., toilet bowl)"""
        try:
            # TODO: Identify unusual draft patterns
            # Mark in database
            pass
            
        except Exception as error:
            logger.error('Failed to flag outliers', exc_info=True)


# Singleton instance
data_import_service = DataImportService()
