"""Database connection and utilities"""
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from src.config import config

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL database manager"""
    
    def __init__(self):
        """Initialize connection pool"""
        try:
            self.pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=config.database['host'],
                port=config.database['port'],
                database=config.database['name'],
                user=config.database['user'],
                password=config.database['password'],
            )
            logger.info('Database connection pool initialized')
        except Exception as error:
            logger.error('Failed to create connection pool', exc_info=True)
            raise
    
    @contextmanager
    def get_cursor(self, dict_cursor: bool = False):
        """Context manager for database cursor"""
        conn = self.pool.getconn()
        try:
            cursor_factory = RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            yield cursor
            conn.commit()
        except Exception as error:
            conn.rollback()
            logger.error('Database operation failed', exc_info=True)
            raise
        finally:
            cursor.close()
            self.pool.putconn(conn)
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> None:
        """Execute a query without returning results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
    
    def execute_dict_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute query and return results as list of dicts"""
        with self.get_cursor(dict_cursor=True) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def initialize(self) -> None:
        """Initialize database (test connection)"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute('SELECT 1')
            logger.info('Database connection verified')
        except Exception as error:
            logger.error('Database initialization failed', exc_info=True)
            raise
    
    def close(self) -> None:
        """Close all connections in pool"""
        if self.pool:
            self.pool.closeall()
            logger.info('Database connections closed')


# Singleton instance
db = Database()
