import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


class Config:
    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "sleeper_draft_agent")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # Sleeper API
    SLEEPER_BASE_URL = "https://api.sleeper.app/v1"
    SLEEPER_USERNAME = os.getenv("SLEEPER_USERNAME", "")
    SLEEPER_RATE_LIMIT = 1000  # requests per minute

    # League Configuration
    LEAGUE_TEAMS = 10
    LEAGUE_ROUNDS = 15
    LEAGUE_SCORING = "PPR"
    LEAGUE_DRAFT_TYPE = "snake"
    LEAGUE_SEASONS = [2021, 2022, 2023, 2024, 2025]
    TARGET_DRAFT_DATE = datetime(2026, 9, 5)

    # ADP Weights
    ADP_WEIGHTS = {
        "sleeper": 1.2,
        "espn": 1.0,
        "fantasypros": 1.0,
        "yahoo": 1.0,
    }

    # Algorithm Parameters
    POSITION_RUN_THRESHOLD = 3
    VALUE_ALERT_ROUNDS = 1
    VALUE_ALERT_PICKS = 3
    PANIC_PICK_SIGMA = 3
    STALENESS_THRESHOLD_DAYS = 30
    CACHE_DURATION_SECONDS = 10

    SCARCITY_MULTIPLIERS = {
        "RB": 1.3,
        "WR": 1.1,
        "TE": 1.2,
        "QB": 1.0,
    }

    # Success Metrics
    KEEPER_ACCURACY_TARGET = 0.8
    KEEPER_COMBO_ACCURACY_TARGET = 0.7
    PICK_PREDICTION_EXACT_TARGET = 0.6
    PICK_PREDICTION_POSITION_TARGET = 0.85
    VALUE_ALERT_PRECISION_TARGET = 0.75
    PANIC_PICK_DETECTION_TARGET = 0.8
    RESPONSE_TIME_TARGET = 10  # seconds


config = Config()
