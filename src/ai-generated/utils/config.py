"""Configuration management using environment variables"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Application configuration"""
    
    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "sleeper-mock-draft"
    
    # Sleeper API
    sleeper_api_base_url: str = "https://api.sleeper.app/v1"
    sleeper_rate_limit: int = 1000  # per minute
    
    # Application
    environment: str = "development"
    log_level: str = "INFO"
    
    # ML/Analysis
    default_simulation_count: int = 1000
    adp_recency_weight: float = 0.7  # Exponential decay factor
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        return cls(
            # Database
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql://localhost:5432/sleeper_mock_draft"
            ),
            database_pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
            database_max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
            
            # Temporal
            temporal_host=os.getenv("TEMPORAL_HOST", "localhost:7233"),
            temporal_namespace=os.getenv("TEMPORAL_NAMESPACE", "default"),
            temporal_task_queue=os.getenv("TEMPORAL_TASK_QUEUE", "sleeper-mock-draft"),
            
            # Application
            environment=os.getenv("ENVIRONMENT", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            
            # ML/Analysis
            default_simulation_count=int(os.getenv("DEFAULT_SIMULATION_COUNT", "1000")),
            adp_recency_weight=float(os.getenv("ADP_RECENCY_WEIGHT", "0.7")),
        )


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get application configuration (singleton)"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
