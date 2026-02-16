import pytest

from activities.league.get_data import GetLeagueDataParams, get_league_data
from testing.mocks import DummySleeperClient


@pytest.mark.asyncio
async def test_get_league_data_aggregates_league_users_and_rosters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dummy = DummySleeperClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy

    monkeypatch.setattr(
        "src.activities.league.get_data.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )

    params = GetLeagueDataParams(league_name="my_league")

    result = await get_league_data(params)

    # league_id should come from dummy.get_league
    assert result["league_id"] == "league-my_league"
    assert result["league_data"]["name"] == "my_league"

    # Users and rosters should be populated with deterministic dummy data
    assert len(result["league_users"]) == 2
    assert len(result["league_rosters"]) == 2

    # Ensure the dummy client recorded the league name usage
    assert "my_league" in dummy.called_with_league_names
