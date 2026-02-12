import logging
import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


class PostgresClientManager:
    #PostgreSQL client manager
    # SQLAlchemy engine/session factory for connecting to the Dockerized PostgreSQL instance 
    # DATABASE_URL env variable

    def __init__(self, database_url: Optional[str] = None, pool_size: int = 10, max_overflow: int = 20) -> None:
        self._database_url = database_url or os.getenv("DATABASE_URL")
        if not self._database_url:
            raise ValueError(
                "Database URL not provided. Set DATABASE_URL environment variable."
            )
        logger.info("Initializing Postgres SQLAlchemy engine")

        self._engine: Engine = create_engine(
            self._database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            future=True,
        )
        self._SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine,
        )

    @property
    def engine(self) -> Engine:
        #Return SQLAlchemy engine
        return self._engine

    def get_session(self) -> Session:
        # Create a new SQLAlchemy session.
        # Responsible for committing/rolling back and closing the session
        return self._SessionLocal()

    def close(self) -> None:
        # Dispose of the engine and its connection pool
        self._engine.dispose()
        logger.info("Disposed Postgres SQLAlchemy engine")


# Single instance for reuse across activities
_postgres_client_instance: Optional[PostgresClientManager] = None
def get_postgres_client_manager(database_url: Optional[str] = None) -> PostgresClientManager:
    # Get or create a single PostgresClientManager instance
    global _postgres_client_instance
    if _postgres_client_instance is None:
        _postgres_client_instance = PostgresClientManager(database_url=database_url)
    return _postgres_client_instance