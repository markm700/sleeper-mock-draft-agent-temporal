# Mock Clients for Testing Temporal Activities

This directory contains mock implementations of external clients used by Temporal activities, enabling tests to validate activity logic without requiring real API connections or database instances.

## Available Mock Clients

### DummySleeperClient

Mock implementation of the Sleeper API client for testing activities that interact with the Sleeper fantasy football API.

**Features:**
- Returns deterministic, predictable data for all Sleeper API endpoints
- Tracks method calls for assertions (e.g., `called_with_usernames`, `called_with_league_ids`)
- No HTTP requests or environment variables required

**Usage Example:**
```python
from testing.mocks import DummySleeperClient

dummy_sleeper = DummySleeperClient()

# Returns fake user data
user = await dummy_sleeper.get_user("testuser")
# user = {"user_id": "user-testuser", "username": "testuser", ...}

# Verify the client was called
assert "testuser" in dummy_sleeper.called_with_usernames
```

### DummyPostgresClient

Mock implementation of the PostgreSQL client for testing activities that perform database operations.

**Features:**
- Simulates `upsert_record()` and `upsert_records()` without database access
- Tracks all upsert calls for test assertions
- Returns mock primary key values
- Provides helper methods to query tracked operations

**Usage Example:**
```python
from testing.mocks import DummyPostgresClient
from schema.database_models import User

dummy_postgres = DummyPostgresClient()

# Simulate upserting a user
user_id = dummy_postgres.upsert_record(
    model=User,
    data={"user_id": "123", "username": "testuser", "display_name": "Test"}
)

# Verify the upsert was called
assert dummy_postgres.count_upserts_for_model("User") == 1
users = dummy_postgres.get_upserted_by_model("User")
assert users[0]["username"] == "testuser"
```

## Testing Activities with Mock Clients

When testing Temporal activities, use `monkeypatch` to replace real client managers with mocks.

### Complete Test Example

```python
import pytest
from activities.team_owner.get_data import (
    GetTeamOwnerDataParams,
    get_team_owner_data,
)
from testing.mocks import DummySleeperClient, DummyPostgresClient


@pytest.mark.asyncio
async def test_get_team_owner_data(monkeypatch: pytest.MonkeyPatch) -> None:
    # Create mock instances
    dummy_sleeper = DummySleeperClient()
    dummy_postgres = DummyPostgresClient()

    # Define factory functions returning the mocks
    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_sleeper

    def _fake_get_postgres_client_manager() -> DummyPostgresClient:
        return dummy_postgres

    # Patch the client managers in the activity module
    monkeypatch.setattr(
        "src.activities.team_owner.get_data.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )
    monkeypatch.setattr(
        "src.activities.team_owner.get_data.get_postgres_client_manager",
        _fake_get_postgres_client_manager,
    )

    # Execute the activity
    params = GetTeamOwnerDataParams(username="testuser", league_name="my_league")
    result = await get_team_owner_data(params)

    # Assert API behavior
    assert result["user_id"] == "user-testuser"
    assert "testuser" in dummy_sleeper.called_with_usernames

    # Assert database behavior
    assert dummy_postgres.count_upserts_for_model("User") == 1
    user_data = dummy_postgres.get_upserted_by_model("User")[0]
    assert user_data["username"] == "testuser"
```

## DummyPostgresClient API

### Core Methods

- **`upsert_record(model, data, conflict_columns=None, update_columns=None)`**
  - Simulates single record upsert
  - Returns mock primary key value
  - Tracks call in `upserted_records`

- **`upsert_records(model, records, conflict_columns=None, update_columns=None)`**
  - Simulates bulk upsert
  - Returns count of records processed
  - Tracks calls in `upserted_bulk_records`

- **`check_connection()`**
  - Always returns `True`
  - Increments `connection_checks` counter

- **`create_all_tables()` / `drop_all_tables()`**
  - No-op methods that track calls

### Helper Methods for Assertions

- **`get_upserted_by_model(model_name: str) -> List[Dict[str, Any]]`**
  - Returns all data dictionaries upserted for a specific model
  - Example: `dummy_postgres.get_upserted_by_model("User")`

- **`get_bulk_upserted_by_model(model_name: str) -> List[Dict[str, Any]]`**
  - Returns all bulk upserted data for a specific model

- **`count_upserts_for_model(model_name: str) -> int`**
  - Counts total upserts (single + bulk) for a model
  - Example: `assert dummy_postgres.count_upserts_for_model("Draft") == 2`

- **`reset()`**
  - Clears all tracked calls (useful between tests)

## Best Practices

1. **Use Both Mocks**: Most activities interact with both Sleeper API and database - mock both clients
2. **Verify Behavior**: Assert both that the activity returns expected data AND that it called the clients correctly
3. **Test Isolation**: Consider calling `dummy_postgres.reset()` or `dummy_postgres = DummyPostgresClient()` between tests
4. **Full Field Coverage**: The `DummySleeperClient` returns complete field structures matching the real API

## Running Tests

```bash
# Run all activity tests
pytest src/testing/data_collection/activities/

# Run specific test file
pytest src/testing/data_collection/activities/test_get_team_owner_data.py

# Run with verbose output
pytest -v src/testing/data_collection/activities/
```

## Troubleshooting

**Issue**: Test fails with `AttributeError: 'DummyPostgresClient' object has no attribute 'X'`

**Solution**: The mock client only implements the subset of methods used by activities. Add the missing method to `DummyPostgresClient` if needed.

**Issue**: Activity tries to use a field from Sleeper API that doesn't exist in mock response

**Solution**: Update `DummySleeperClient` method to include the missing field with appropriate test data.
