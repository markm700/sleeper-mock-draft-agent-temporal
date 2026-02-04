---
applyTo: "src/utils/**/*.py"
---

# Utility Module Instructions

## Configuration (`config.py`)

### Core Patterns

- Use `@dataclass` for `Config` class
- Group fields with comments (Database, Temporal, Application, ML/Analysis)
- Provide sensible defaults via `os.getenv()` second parameter
- Load `.env` file with `load_dotenv()` at module level
- Use `@classmethod` `from_env()` constructor
- Singleton pattern: `get_config()` function returns global instance
- All type hints explicit

### Example Structure

```python
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """Application configuration"""
    
    # Database
    database_url: str
    database_pool_size: int = 10
    
    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    
    # Application
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        return cls(
            database_url=os.getenv("DATABASE_URL", "postgresql://localhost:5432/db"),
            database_pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
            temporal_host=os.getenv("TEMPORAL_HOST", "localhost:7233"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

_config: Optional[Config] = None

def get_config() -> Config:
    """Get application configuration (singleton)"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
```

## Logging (`logging.py`)

### Core Patterns

- Centralized `setup_logging()` function
- Structured format: `timestamp | level | name | message`
- Use `StreamHandler` for stdout (no file logging)
- Configure via `LOG_LEVEL` environment variable
- Set Temporal SDK logs to INFO to reduce noise

### Usage

- Use `logging.getLogger(__name__)` in regular modules
- Use `workflow.logger` in workflows
- Use `activity.logger` in activities
