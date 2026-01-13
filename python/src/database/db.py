import psycopg2
from psycopg2 import pool
from typing import Any, List, Tuple, Optional
from src.config import config


class Database:
    """Database connection pool and utilities"""

    def __init__(self):
        self.connection_pool = psycopg2.pool.SimpleConnectionPool(
            1,
            20,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
        )

    def get_connection(self):
        """Get a connection from the pool"""
        return self.connection_pool.getconn()

    def return_connection(self, conn):
        """Return a connection to the pool"""
        self.connection_pool.putconn(conn)

    def execute_query(
        self, query: str, params: Optional[Tuple] = None
    ) -> List[Tuple[Any]]:
        """Execute a SELECT query and return results"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        finally:
            self.return_connection(conn)

    def execute_update(self, query: str, params: Optional[Tuple] = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return rows affected"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.return_connection(conn)

    def close_all_connections(self):
        """Close all connections in the pool"""
        self.connection_pool.closeall()

    def initialize(self):
        """Initialize database tables"""
        # TODO: Run schema.sql or create tables programmatically
        print("Database initialized")


# Global instance
db = Database()
