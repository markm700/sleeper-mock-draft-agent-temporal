---
applyTo: "src/utils/**/*.py"
---

# Utility Module Instructions

> **Note**: This directory and these patterns are for future implementation.

## Configuration (`config.py`)

### Core Patterns

- Use `@dataclass` from pydantic.dataclasses for `Config` class
- Group fields with comments (Database, Temporal, Application, ML/Analysis)
- Provide sensible defaults via `os.getenv()` second parameter
- Load `.env` file with `load_dotenv()` at module level
- Use `@classmethod` `from_env()` constructor
- Singleton pattern: `get_config()` function returns global instance
- All type hints explicit

### Example Structure

```python
import os
from pydantic.dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True, kw_only=True)
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
            log_level=log_level,
        )

_config: Optional[Config] = None

def get_config() -> Config:
    """Get application configuration (singleton)"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
```

## Logging Patterns

### Current Practice

- **In workflows**: Use `workflow.logger` — it is replay-aware and injects workflow context (`workflow.logger` is **NOT** deprecated)
- **In activities**: Use `activity.logger` — it injects activity context
- **In regular modules** (clients, helpers): Use Python's standard `logging.getLogger(__name__)`

### Future Implementation (`logging.py`)

When centralized logging configuration is needed:

```python
import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for application."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Reduce Temporal SDK noise
    logging.getLogger("temporalio").setLevel(logging.INFO)
```
