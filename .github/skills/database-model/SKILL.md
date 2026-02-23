---
name: database-model
description: Add new SQLAlchemy database models and migrations. Use when asked to add tables, modify schema, or create new data models.
---

# Adding Database Models

> **Note**: This skill is for future implementation when database persistence is added to the project.

Use this skill to add new SQLAlchemy ORM models following project conventions.

## Steps

1. **Add model to `src/models/database_models.py`**

2. **Define model class** following PostgreSQL conventions

3. **Add relationships** to related models

4. **Create database activities** in `src/activities/database.py`

5. **Generate migration** using Alembic

## Model Template

```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class {ModelName}(Base):
    """
    {ModelName} table - brief description
    
    Stores information about...
    """
    __tablename__ = "{table_name}"
    
    # Primary Key
    # Use VARCHAR(50) for external IDs, Integer for internal IDs
    id = Column(Integer, primary_key=True)  # or
    {external_id} = Column(String(50), primary_key=True)
    
    # Required Fields
    name = Column(String(255), nullable=False)
    status = Column(String(50))
    
    # Optional Fields
    description = Column(String(500))
    count = Column(Integer)
    
    # JSON Fields (for semi-structured data)
    settings = Column(JSONB)
    metadata = Column(JSONB)
    
    # Foreign Keys
    league_id = Column(String(50), ForeignKey("leagues.league_id"), nullable=False)
    
    # Timestamps (required for all tables)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships (use back_populates)
    league = relationship("League", back_populates="{table_name}")
    related_items = relationship("RelatedItem", back_populates="{model_name}")
    
    # Indexes and Constraints
    __table_args__ = (
        UniqueConstraint("league_id", "name", name="uq_{table_name}_league_name"),
        Index("idx_{table_name}_league_id", "league_id"),
        Index("idx_{table_name}_status", "status"),
        Index("idx_{table_name}_created_at", "created_at"),
    )
```

## Key Conventions

### Column Types

- **External IDs** (from APIs): `Column(String(50))`
  - Examples: `league_id`, `draft_id`, `player_id`, `user_id`
  
- **Internal IDs** (auto-increment): `Column(Integer, primary_key=True)`
  - Use SERIAL/Integer for internal IDs

- **Semi-structured data**: `Column(JSONB)`
  - Use for settings, metadata, arrays, nested objects
  - Examples: `scoring_settings`, `roster_positions`, `metadata`

- **Timestamps**: `Column(DateTime, default=datetime.utcnow)`
  - Always include `created_at` and `updated_at`

### Relationships

Always use bidirectional relationships with `back_populates`:

```python
# In Parent model
children = relationship("Child", back_populates="parent")

# In Child model  
parent = relationship("Parent", back_populates="children")
```

### Indexes

Define indexes in `__table_args__` tuple:

```python
__table_args__ = (
    # Unique constraints
    UniqueConstraint("field1", "field2", name="uq_table_field1_field2"),
    
    # Regular indexes
    Index("idx_table_field1", "field1"),
    Index("idx_table_field2", "field2"),
    
    # Composite indexes
    Index("idx_table_field1_field2", "field1", "field2"),
)
```

## Creating Database Activities

After adding the model, create activities in `src/activities/database.py`:

```python
@activity.defn
async def store_{entity}(data: Dict[str, Any]) -> bool:
    """Store {entity} in database."""
    activity.logger.info(f"Storing {entity}: {data.get('id')}")
    
    try:
        # TODO: Implement SQLAlchemy insert/update
        # session = get_db_session()
        # entity = {Entity}(**data)
        # session.merge(entity)
        # session.commit()
        
        activity.logger.info("{Entity} stored successfully")
        return True
    except Exception as e:
        activity.logger.error(f"Failed to store {entity}: {str(e)}")
        raise

@activity.defn
async def fetch_{entity}(entity_id: str) -> Dict[str, Any]:
    """Fetch {entity} from database."""
    activity.logger.info(f"Fetching {entity}: {entity_id}")
    
    try:
        # TODO: Query database
        data = {}
        activity.logger.info("{Entity} fetched successfully")
        return data
    except Exception as e:
        activity.logger.error(f"Failed to fetch {entity}: {str(e)}")
        raise
```

## Creating Alembic Migration

Generate migration for schema changes:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add {table_name} table"

# Review generated migration in alembic/versions/

# Apply migration
alembic upgrade head
```

## Updating Related Models

If adding a relationship to an existing model, update that model:

```python
class ExistingModel(Base):
    # ... existing columns ...
    
    # Add new relationship
    new_relation = relationship("{NewModel}", back_populates="existing_model")
```

## PostgreSQL-Specific Features

This project uses PostgreSQL with:

- **JSONB columns** for semi-structured data (better than JSON)
- **GIN indexes** for JSONB fields (add if needed)
- **Full-text search** capabilities (add if needed)
- **Array types** (use JSONB or PostgreSQL ARRAY type)

Example with GIN index:

```python
from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import JSONB

class MyModel(Base):
    __tablename__ = "my_table"
    
    metadata_field = Column(JSONB)
    
    __table_args__ = (
        Index("idx_my_table_metadata", "metadata_field", postgresql_using="gin"),
    )
```
