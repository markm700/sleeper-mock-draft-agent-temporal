"""Configuration module"""
import os
import logging
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class Config:
    """Application configuration"""
    
    # Database
    database = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'name': os.getenv('DB_NAME', 'sleeper_draft_agent'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
    }
    
    # Sleeper API
    sleeper = {
        'base_url': os.getenv('SLEEPER_BASE_URL', 'https://api.sleeper.app/v1'),
        'username': os.getenv('SLEEPER_USERNAME', ''),
    }
    
    # League settings
    league = {
        'seasons': [int(s) for s in os.getenv('LEAGUE_SEASONS', '2021,2022,2023,2024,2025').split(',')],
        'teams': int(os.getenv('LEAGUE_TEAMS', '10')),
        'rounds': int(os.getenv('LEAGUE_ROUNDS', '15')),
        'scoring': os.getenv('LEAGUE_SCORING', 'ppr'),
    }


config = Config()
