import pytest

from activities.team_owner.get_data import (
    GetTeamOwnerDataParams,
    get_team_owner_data,
)
from testing.mocks import DummySleeperClient


@pytest.mark.asyncio
async def test_get_team_owner_data_uses_user_and_leagues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dummy = DummySleeperClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy

    monkeypatch.setattr(
        "src.activities.team_owner.get_data.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
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

    assert dummy.called_with_usernames == ["testuser"]
