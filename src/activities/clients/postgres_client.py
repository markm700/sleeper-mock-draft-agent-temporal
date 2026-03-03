"""
PostgreSQL client manager for Temporal activities.

Provides SQLAlchemy engine, session factory, and helper methods for
database operations with the Sleeper fantasy football schema.
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from schema.database_models import Base

logger = logging.getLogger(__name__)


class PostgresClientManager:
    """
    PostgreSQL client manager for database operations.
    
    SQLAlchemy engine/session factory for connecting to the PostgreSQL instance.
    Requires DATABASE_URL environment variable.
    
    Example DATABASE_URL:
        postgresql://user:password@localhost:5432/sleeper_db
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
        echo: bool = False,
    ) -> None:
        """
        Initialize PostgreSQL client manager.
        
        Args:
            database_url: PostgreSQL connection string. If None, reads from DATABASE_URL env var.
            pool_size: Number of connections to maintain in the pool.
            max_overflow: Maximum number of connections to create beyond pool_size.
            echo: If True, log all SQL statements (useful for debugging).
        """
        self._database_url = database_url or os.getenv("DATABASE_URL")
        if not self._database_url:
            raise ValueError(
                "Database URL not provided. Set DATABASE_URL environment variable "
                "or pass database_url parameter. "
                "Example: postgresql://user:password@localhost:5432/sleeper_db"
            )
        
        logger.info("Initializing PostgreSQL SQLAlchemy engine")

        self._engine: Engine = create_engine(
            self._database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=echo,
            future=True,
        )
        self._SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine,
        )

    @property
    def engine(self) -> Engine:
        """Return SQLAlchemy engine instance."""
        return self._engine

    def get_session(self) -> Session:
        """
        Create a new SQLAlchemy session.
        
        Caller is responsible for committing/rolling back and closing the session.
        Consider using session_scope() context manager instead for automatic cleanup.
        
        Returns:
            SQLAlchemy Session object.
        
        Example:
            session = pg_client.get_session()
            try:
                session.add(user)
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        """
        return self._SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        
        Automatically commits on success, rolls back on exception, and closes session.
        
        Yields:
            SQLAlchemy Session object.
        
        Example:
            with pg_client.session_scope() as session:
                user = User(user_id="123", username="test")
                session.add(user)
                # Automatically commits here if no exception
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_all_tables(self) -> None:
        """
        Create all tables defined in the database models.
        
        This uses Base.metadata.create_all() to create tables for:
        - users
        - leagues
        - team_owners
        - rosters
        - drafts
        - draft_picks
        - traded_draft_picks
        - players
        
        Note: This is idempotent - tables that already exist will not be modified.
        For production, use Alembic migrations instead.
        """
        logger.info("Creating all database tables from schema models")
        Base.metadata.create_all(self._engine)
        logger.info("Successfully created all database tables")

    def drop_all_tables(self) -> None:
        """
        Drop all tables defined in the database models.
        
        WARNING: This will delete all data. Use with caution.
        Only intended for development/testing environments.
        """
        logger.warning("Dropping all database tables - ALL DATA WILL BE LOST")
        Base.metadata.drop_all(self._engine)
        logger.info("Successfully dropped all database tables")

    def check_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def upsert_record(
        self,
        model: type,
        data: Dict[str, Any],
        conflict_columns: Optional[List[str]] = None,
        update_columns: Optional[List[str]] = None,
    ) -> Any:
        """
        Upsert a single record with auto-commit (INSERT ... ON CONFLICT DO UPDATE).
        
        This is the recommended way to save data from activities - it's idempotent
        and handles both inserts and updates automatically.
        
        Args:
            model: SQLAlchemy model class (e.g., User, League, Roster)
            data: Dictionary of column names to values
            conflict_columns: Columns to check for conflict (default: primary key)
            update_columns: Columns to update on conflict (default: all except PK)
        
        Returns:
            Primary key value(s) of the upserted record
        
        Raises:
            Exception: If upsert fails
        
        Example:
            from schema.database_models import User
            
            user_id = pg_client.upsert_record(
                model=User,
                data={
                    "user_id": "123",
                    "username": "markm700",
                    "display_name": "Mark M",
                    "is_bot": False,
                    "api_metadata": {...}
                }
            )
            # Returns: "123" (the user_id primary key)
        """
        with self.session_scope() as session:
            # Get primary key columns if not specified
            if conflict_columns is None:
                mapper = inspect(model)
                conflict_columns = [col.name for col in mapper.primary_key]
            
            # Build the insert statement
            stmt = insert(model).values(**data)
            
            # Determine which columns to update on conflict
            if update_columns is None:
                # Update all columns except the conflict columns
                update_columns = [k for k in data.keys() if k not in conflict_columns]
            
            # Build update dict using excluded.column syntax (values from the INSERT attempt)
            update_dict = {col: stmt.excluded[col] for col in update_columns if col in data}
            if hasattr(model, "updated_at") and "updated_at" not in update_dict:
                update_dict["updated_at"] = datetime.now(timezone.utc)
            
            # Add ON CONFLICT DO UPDATE
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns,
                set_=update_dict,
            )
            
            # Execute and auto-commit via session_scope
            session.execute(stmt)
            
            # Return primary key value(s)
            pk_values = [data.get(col) for col in conflict_columns]
            return pk_values[0] if len(pk_values) == 1 else tuple(pk_values)

    def upsert_records(
        self,
        model: type,
        records: List[Dict[str, Any]],
        conflict_columns: Optional[List[str]] = None,
        update_columns: Optional[List[str]] = None,
    ) -> int:
        """
        Bulk upsert multiple records with auto-commit.
        
        More efficient than calling upsert_record() multiple times.
        
        Args:
            model: SQLAlchemy model class
            records: List of dictionaries, each containing column names to values
            conflict_columns: Columns to check for conflict (default: primary key)
            update_columns: Columns to update on conflict (default: all except PK)
        
        Returns:
            Number of records processed
        
        Raises:
            Exception: If bulk upsert fails
        
        Example:
            from schema.database_models import TeamOwner
            
            count = pg_client.upsert_records(
                model=TeamOwner,
                records=[
                    {"league_id": "L1", "user_id": "U1", "display_name": "User 1"},
                    {"league_id": "L1", "user_id": "U2", "display_name": "User 2"},
                ]
            )
            # Returns: 2
        """
        if not records:
            return 0
        
        with self.session_scope() as session:
            # Get primary key columns if not specified
            if conflict_columns is None:
                mapper = inspect(model)
                conflict_columns = [col.name for col in mapper.primary_key]
            
            # Determine which columns to update on conflict
            if update_columns is None:
                # Update all columns except conflict columns
                sample_record = records[0]
                update_columns = [k for k in sample_record.keys() if k not in conflict_columns]
            
            # Add updated_at to all records if the model has it
            if hasattr(model, "updated_at"):
                for record in records:
                    if "updated_at" not in record:
                        record["updated_at"] = datetime.now(timezone.utc)
            
            # Build update dict template (uses excluded.column syntax for bulk)
            stmt = insert(model)
            update_dict = {col: stmt.excluded[col] for col in update_columns}
            
            # Add ON CONFLICT DO UPDATE
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns,
                set_=update_dict,
            )
            
            # Execute bulk upsert
            session.execute(stmt, records)
            
            # Auto-commit via session_scope
        
        logger.info(f"Bulk upserted {len(records)} records to {model.__tablename__}")
        return len(records)

    def close(self) -> None:
        """
        Dispose of the engine and its connection pool.
        
        Call this when shutting down the application to cleanly close all connections.
        """
        self._engine.dispose()
        logger.info("Disposed PostgreSQL SQLAlchemy engine and connection pool")


# Module-level singleton instance for reuse across activities
_postgres_client_instance: Optional[PostgresClientManager] = None


def get_postgres_client_manager(
    database_url: Optional[str] = None,
    reinitialize: bool = False,
) -> PostgresClientManager:
    """
    Get or create a singleton PostgresClientManager instance.
    
    This ensures all activities share the same connection pool for efficiency.
    
    Args:
        database_url: PostgreSQL connection string. Only used on first call or if reinitialize=True.
        reinitialize: If True, dispose existing instance and create a new one.
    
    Returns:
        Shared PostgresClientManager instance.
    
    Example:
        # In activity
        pg_client = get_postgres_client_manager()
        with pg_client.session_scope() as session:
            user = session.query(User).filter_by(username="markm700").first()
    """
    global _postgres_client_instance
    
    if reinitialize and _postgres_client_instance is not None:
        logger.info("Reinitializing PostgreSQL client manager")
        _postgres_client_instance.close()
        _postgres_client_instance = None
    
    if _postgres_client_instance is None:
        _postgres_client_instance = PostgresClientManager(database_url=database_url)
    
    return _postgres_client_instance
