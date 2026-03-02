import pytest

from activities.team_owner.get_data import (
    GetTeamOwnerDataParams,
    get_team_owner_data,
)
from testing.mocks import DummySleeperClient, DummyPostgresClient


@pytest.mark.asyncio
async def test_get_team_owner_data_uses_user_and_leagues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dummy_sleeper = DummySleeperClient()
    dummy_postgres = DummyPostgresClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_sleeper

    def _fake_get_postgres_client_manager() -> DummyPostgresClient:
        return dummy_postgres

    monkeypatch.setattr(
        "src.activities.team_owner.get_data.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )
    
    monkeypatch.setattr(
        "src.activities.team_owner.get_data.get_postgres_client_manager",
        _fake_get_postgres_client_manager,
    )

    params = GetTeamOwnerDataParams(username="testuser", league_name="my_league")

    result = await get_team_owner_data(params)

    # user_id should come from dummy.get_user
    assert result["user_id"] == "user-testuser"
    assert result["user_data"]["username"] == "testuser"

    # user_leagues should contain seasons with league entries
    user_leagues = result["user_leagues"]
    assert set(user_leagues.keys()) == {"2020", "2021", "2022", "2023", "2024"}
    for season, leagues in user_leagues.items():
        assert len(leagues) == 1
        assert leagues[0]["name"] == "my_league"

    assert dummy_sleeper.called_with_usernames == ["testuser"]
    
    # Verify database upsert was called
    assert dummy_postgres.count_upserts_for_model("User") == 1
    user_data = dummy_postgres.get_upserted_by_model("User")[0]
    assert user_data["username"] == "testuser"
    assert user_data["display_name"] == "Display testuser"
