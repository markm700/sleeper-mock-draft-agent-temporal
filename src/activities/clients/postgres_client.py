"""
PostgreSQL client manager for Temporal activities.

Provides SQLAlchemy engine, session factory, and helper methods for
database operations with the Sleeper fantasy football schema.
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.schema.database_models import Base

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
