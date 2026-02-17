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
    assert "league-123" in dummy.called_with_league_ids
