import pytest

from activities.league.get_data import GetLeagueDataParams, get_league_data
from testing.mocks import DummySleeperClient, DummyPostgresClient


@pytest.mark.asyncio
async def test_get_league_data_aggregates_league_users_and_rosters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dummy_sleeper = DummySleeperClient()
    dummy_postgres = DummyPostgresClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_sleeper

    def _fake_get_postgres_client_manager() -> DummyPostgresClient:
        return dummy_postgres

    monkeypatch.setattr(
        "activities.league.get_data.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )
    
    monkeypatch.setattr(
        "activities.league.get_data.get_postgres_client_manager",
        _fake_get_postgres_client_manager,
    )

    params = GetLeagueDataParams(league_id="league-123")

    result = await get_league_data(params)

    # The activity should return league metadata, users, and rosters
    assert "league_data" in result
    assert "league_users" in result
    assert "league_rosters" in result

    # Users and rosters should be populated with deterministic dummy data
    assert len(result["league_users"]) == 2
    assert len(result["league_rosters"]) == 2

    # Ensure the dummy client recorded the league_id usage
    assert "league-123" in dummy_sleeper.called_with_league_ids
    
    # Verify database upserts were called (single upsert for League, bulk for User/TeamOwner/Roster)
    assert dummy_postgres.count_upserts_for_model("League") == 1
    assert dummy_postgres.count_upserts_for_model("User") == 2
    assert dummy_postgres.count_upserts_for_model("TeamOwner") == 2
    assert dummy_postgres.count_upserts_for_model("Roster") == 2
    
    # Verify bulk upserted data structure
    users = dummy_postgres.get_bulk_upserted_by_model("User")
    assert len(users) == 2
    assert all("user_id" in user for user in users)
    assert all("username" in user for user in users)

@pytest.mark.asyncio
async def test_get_league_data_skips_users_with_missing_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_league_data handles missing required fields gracefully."""
    dummy_sleeper = DummySleeperClient(incomplete_data=True)
    dummy_postgres = DummyPostgresClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_sleeper

    def _fake_get_postgres_client_manager() -> DummyPostgresClient:
        return dummy_postgres

    monkeypatch.setattr(
        "activities.league.get_data.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )
    
    monkeypatch.setattr(
        "activities.league.get_data.get_postgres_client_manager",
        _fake_get_postgres_client_manager,
    )

    params = GetLeagueDataParams(league_id="league-456")

    result = await get_league_data(params)

    # The activity should return all 3 users from API (including incomplete one)
    assert "league_users" in result
    assert len(result["league_users"]) == 3

    # But only 2 valid users should be upserted (skipping the one without user_id)
    assert dummy_postgres.count_upserts_for_model("User") == 2
    assert dummy_postgres.count_upserts_for_model("TeamOwner") == 2
    
    # Verify the users that were upserted have required fields
    users = dummy_postgres.get_bulk_upserted_by_model("User")
    assert len(users) == 2
    assert all(user["user_id"] for user in users)  # All have user_id
    assert all(user.get("username") or user.get("display_name") for user in users)  # All have username or display_name
