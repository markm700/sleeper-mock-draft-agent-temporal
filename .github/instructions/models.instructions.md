---
applyTo: "src/models/**/*.py"
---

# Data Model Instructions

> **Note**: This directory and these patterns are for future implementation when database storage is added.

## Database Models (`database_models.py`)

When working with SQLAlchemy ORM models:

### Core Patterns

- Inherit from `declarative_base()`
- Use VARCHAR(50) for external IDs (league_id, draft_id, player_id)
- Use SERIAL/Integer for internal auto-increment IDs
- Include `created_at`, `updated_at` with default `datetime.utcnow`

### PostgreSQL Features

- Use JSONB columns for semi-structured data (settings, metadata, roster_positions)
- Define indexes using `__table_args__` tuple with `Index()` and `UniqueConstraint()`
- Define relationships with `relationship()` and `back_populates`

### Example Structure

```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class League(Base):
    """League table"""
    __tablename__ = "leagues"
    
    league_id = Column(String(50), primary_key=True)
    name = Column(String(255))
    season = Column(String(10))
    scoring_settings = Column(JSONB)
    roster_positions = Column(JSONB)
    settings = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    drafts = relationship("Draft", back_populates="league")
    
    # Indexes
    __table_args__ = (
        Index("idx_leagues_season", "season"),
    )
```

## API Models (`api_models.py`)

When working with API response models:

### Core Patterns

- Use `@dataclass` decorator with frozen=True and kw_only=True
- Naming pattern: `{Resource}Response` (e.g., `UserResponse`, `LeagueResponse`)
- Required fields first, optional fields last with `= None`
- Use `Optional[T]` for nullable fields
- Use `Dict[str, Any]` for JSON-like objects from API
- Use `List[str]` for arrays

### Example Structure

```python
from pydantic.dataclasses import dataclass
from typing import Optional, Dict, List, Any

@dataclass(frozen=True, kw_only=True)
class LeagueResponse:
    """Sleeper API league response"""
    league_id: str
    name: str
    season: str
    status: str
    draft_id: Optional[str] = None
    total_rosters: Optional[int] = None
    roster_positions: Optional[List[str]] = None
    scoring_settings: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
```

## Schema Changes

When adding new models:
1. Add model to `src/models/database_models.py`
2. Create corresponding activities in `src/activities/database.py`
3. Create Alembic migration: `alembic revision --autogenerate -m "Add {table_name} table"`
4. Add relationships to related models with `back_populates`
