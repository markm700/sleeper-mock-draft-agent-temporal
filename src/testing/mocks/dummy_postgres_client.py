"""
Mock PostgreSQL client for testing Temporal activities.

Provides a stub implementation of PostgresClientManager that records
method calls without requiring a real database connection.
"""

from contextlib import contextmanager
from typing import Any, Dict, Generator, Iterator, List, Optional


# ---------------------------------------------------------------------------
# Session-level mocks for query-based activities
# ---------------------------------------------------------------------------

def _resolve_model_name_from_args(args: tuple) -> str:
    """Infer SQLAlchemy model class name from query() positional args."""
    if not args:
        return ""
    first = args[0]
    # Direct class (e.g. session.query(Draft))
    if isinstance(first, type):
        return first.__name__
    # InstrumentedAttribute (e.g. session.query(Draft.draft_id))
    if hasattr(first, "class_"):
        return first.class_.__name__
    return ""


def _resolve_model_name_from_select(stmt: Any) -> str:
    """Infer model class name from a SQLAlchemy select() statement."""
    _TABLE_TO_MODEL: Dict[str, str] = {
        "players": "Player",
        "drafts": "Draft",
        "draft_picks": "DraftPick",
        "traded_draft_picks": "TradedDraftPick",
        "team_owners": "TeamOwner",
        "users": "User",
        "leagues": "League",
        "rosters": "Roster",
    }
    try:
        # get_final_froms() is the non-deprecated API (SQLAlchemy >= 1.4.23)
        try:
            froms = stmt.get_final_froms()
        except AttributeError:
            froms = stmt.froms  # fallback for older SQLAlchemy
        if froms and hasattr(froms[0], "name"):
            return _TABLE_TO_MODEL.get(froms[0].name, froms[0].name)
    except Exception:
        pass
    return ""


class DummyQueryChain:
    """Chainable mock for SQLAlchemy query objects."""

    def __init__(self, data: List[Any]) -> None:
        self._data = data

    def filter(self, *args: Any, **kwargs: Any) -> "DummyQueryChain":
        return self

    def filter_by(self, **kwargs: Any) -> "DummyQueryChain":
        return self

    def order_by(self, *args: Any) -> "DummyQueryChain":
        return self

    def where(self, *args: Any) -> "DummyQueryChain":
        return self

    def first(self) -> Optional[Any]:
        return self._data[0] if self._data else None

    def all(self) -> List[Any]:
        return self._data


class DummyScalars:
    """Mock for SQLAlchemy ScalarResult."""

    def __init__(self, data: List[Any]) -> None:
        self._data = data

    def all(self) -> List[Any]:
        return self._data


class DummyExecuteResult:
    """Mock for SQLAlchemy CursorResult returned by session.execute()."""

    def __init__(self, data: List[Any]) -> None:
        self._data = data

    def scalars(self) -> DummyScalars:
        return DummyScalars(self._data)


class DummySession:
    """
    Lightweight SQLAlchemy session mock for query-based activity tests.

    Responses are configured per model name before calling the activity::

        session = DummySession()
        session.configure_query("Draft", [("draft_1",), ("draft_2",)])
        session.configure_execute("Player", [mock_player_1, mock_player_2])
    """

    def __init__(self) -> None:
        self._query_responses: Dict[str, List[Any]] = {}
        self._execute_responses: Dict[str, List[Any]] = {}
        self.queries_made: List[str] = []
        self.executes_made: List[str] = []

    def configure_query(self, model_name: str, results: List[Any]) -> None:
        """Pre-configure query() results for a given model name."""
        self._query_responses[model_name] = results

    def configure_execute(self, model_name: str, results: List[Any]) -> None:
        """Pre-configure execute() results for a given model name."""
        self._execute_responses[model_name] = results

    # Context manager protocol (mirrors SQLAlchemy Session behaviour)
    def __enter__(self) -> "DummySession":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def query(self, *args: Any) -> DummyQueryChain:
        model_name = _resolve_model_name_from_args(args)
        self.queries_made.append(model_name)
        data = self._query_responses.get(model_name, [])
        return DummyQueryChain(data)

    def execute(self, stmt: Any) -> DummyExecuteResult:
        model_name = _resolve_model_name_from_select(stmt)
        self.executes_made.append(model_name)
        data = self._execute_responses.get(model_name, [])
        return DummyExecuteResult(data)


class DummyPostgresClient:
    """
    Mock PostgreSQL client for testing activities.
    
    This dummy mirrors the PostgresClientManager interface used by activities
    to validate database operations without requiring a real PostgreSQL instance.
    
    Tracks all upsert calls for test assertions.
    """

    def __init__(self) -> None:
        """Initialize tracking lists for method calls."""
        self.upserted_records: List[Dict[str, Any]] = []
        self.upserted_bulk_records: List[Dict[str, Any]] = []
        self.models_used: List[type] = []
        self.connection_checks: int = 0
        self.table_creations: int = 0
        self.table_drops: int = 0
        self._session = DummySession()

    @property
    def session(self) -> DummySession:
        """Expose the underlying DummySession for query configuration in tests."""
        return self._session

    def get_session(self) -> DummySession:
        """Return the shared DummySession (supports context manager protocol)."""
        return self._session

    @contextmanager
    def session_scope(self) -> Generator[DummySession, None, None]:
        """Yield the shared DummySession within a no-op transaction scope."""
        yield self._session

    def upsert_record(
        self,
        model: type,
        data: Dict[str, Any],
        conflict_columns: Optional[List[str]] = None,
        update_columns: Optional[List[str]] = None,
    ) -> Any:
        """
        Mock upsert_record that tracks calls without database access.
        
        Args:
            model: SQLAlchemy model class
            data: Dictionary of column names to values
            conflict_columns: Columns to check for conflict (unused in mock)
            update_columns: Columns to update on conflict (unused in mock)
        
        Returns:
            Mocked primary key value from data
        """
        self.models_used.append(model)
        self.upserted_records.append({
            "model": model.__name__,
            "data": data.copy(),
            "conflict_columns": conflict_columns,
            "update_columns": update_columns,
        })
        
        # Return a mock primary key value
        # Try common PK field names
        for pk_field in ["user_id", "league_id", "draft_id", "roster_id", "pick_id"]:
            if pk_field in data:
                return data[pk_field]
        
        # Fallback: return first value or a generic mock ID
        if data:
            return list(data.values())[0]
        return "mock_id_123"

    def upsert_records(
        self,
        model: type,
        records: List[Dict[str, Any]],
        conflict_columns: Optional[List[str]] = None,
        update_columns: Optional[List[str]] = None,
    ) -> int:
        """
        Mock bulk upsert that tracks calls without database access.
        
        Args:
            model: SQLAlchemy model class
            records: List of dictionaries containing column names to values
            conflict_columns: Columns to check for conflict (unused in mock)
            update_columns: Columns to update on conflict (unused in mock)
        
        Returns:
            Number of records processed
        """
        if not records:
            return 0
        
        self.models_used.append(model)
        for record in records:
            self.upserted_bulk_records.append({
                "model": model.__name__,
                "data": record.copy(),
                "conflict_columns": conflict_columns,
                "update_columns": update_columns,
            })
        
        return len(records)

    def check_connection(self) -> bool:
        """
        Mock connection check that always succeeds.
        
        Returns:
            True (always successful in mock)
        """
        self.connection_checks += 1
        return True

    def create_all_tables(self) -> None:
        """Mock table creation that tracks calls."""
        self.table_creations += 1

    def drop_all_tables(self) -> None:
        """Mock table drop that tracks calls."""
        self.table_drops += 1

    def close(self) -> None:
        """Mock close operation (no-op in mock)."""
        pass

    # Helper methods for test assertions

    def get_upserted_by_model(self, model_name: str) -> List[Dict[str, Any]]:
        """
        Get all records upserted for a specific model.
        
        Args:
            model_name: Name of the model class (e.g., "User", "League")
        
        Returns:
            List of data dictionaries upserted for that model
        """
        return [
            record["data"]
            for record in self.upserted_records
            if record["model"] == model_name
        ]

    def get_bulk_upserted_by_model(self, model_name: str) -> List[Dict[str, Any]]:
        """
        Get all bulk upserted records for a specific model.
        
        Args:
            model_name: Name of the model class
        
        Returns:
            List of data dictionaries bulk upserted for that model
        """
        return [
            record["data"]
            for record in self.upserted_bulk_records
            if record["model"] == model_name
        ]

    # Alias for compatibility
    def get_batch_upserted_by_model(self, model_name: str) -> List[Dict[str, Any]]:
        """Alias for get_bulk_upserted_by_model for test compatibility."""
        return self.get_bulk_upserted_by_model(model_name)

    def count_upserts_for_model(self, model_name: str) -> int:
        """
        Count total upserts (single + bulk) for a specific model.
        
        Args:
            model_name: Name of the model class
        
        Returns:
            Total number of upsert operations for that model
        """
        single_count = sum(
            1 for record in self.upserted_records if record["model"] == model_name
        )
        bulk_count = sum(
            1 for record in self.upserted_bulk_records if record["model"] == model_name
        )
        return single_count + bulk_count

    def count_batch_upserts_for_model(self, model_name: str) -> int:
        """
        Count number of batch/bulk upsert operations for a specific model.
        
        Note: This counts the number of upsert_records() calls, not individual records.
        
        Args:
            model_name: Name of the model class
        
        Returns:
            Number of batch upsert operations for that model
        """
        # Count unique batch operations by tracking when we added records
        # We need to count how many times upsert_records was called for this model
        batch_operations = 0
        seen_indices = set()
        
        for idx, record in enumerate(self.upserted_bulk_records):
            if record["model"] == model_name and idx not in seen_indices:
                # This is part of a batch operation
                # Count it if it's the first record or if the previous record was a different model
                if idx == 0 or self.upserted_bulk_records[idx - 1]["model"] != model_name:
                    batch_operations += 1
                seen_indices.add(idx)
        
        return batch_operations

    def reset(self) -> None:
        """Clear all tracked calls (useful between tests)."""
        self.upserted_records.clear()
        self.upserted_bulk_records.clear()
        self.models_used.clear()
        self.connection_checks = 0
        self.table_creations = 0
        self.table_drops = 0
        self._session = DummySession()


# Module-level singleton for reuse across tests (mirrors real client pattern)
_dummy_postgres_client_instance: Optional[DummyPostgresClient] = None


def get_dummy_postgres_client(reinitialize: bool = False) -> DummyPostgresClient:
    """
    Get or create a singleton DummyPostgresClient instance.
    
    This mirrors the get_postgres_client_manager() function pattern.
    
    Args:
        reinitialize: If True, create a new instance (useful for test isolation)
    
    Returns:
        Shared DummyPostgresClient instance
    """
    global _dummy_postgres_client_instance
    
    if reinitialize or _dummy_postgres_client_instance is None:
        _dummy_postgres_client_instance = DummyPostgresClient()
    
    return _dummy_postgres_client_instance
