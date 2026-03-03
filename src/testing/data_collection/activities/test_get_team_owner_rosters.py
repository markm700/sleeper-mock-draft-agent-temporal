import pytest

from activities.team_owner.get_roster import (
    GetLeagueRosterParams,
    get_team_owner_rosters,
)
from testing.mocks import DummySleeperClient


@pytest.mark.asyncio
async def test_get_team_owner_rosters_filters_by_user_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dummy = DummySleeperClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy

    monkeypatch.setattr(
        "activities.team_owner.get_roster.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )

    # Use a league_id that the dummy will echo into league_key
    params = GetLeagueRosterParams(league_id="league_123", user_id="user_1")

    result = await get_team_owner_rosters(params)

    # Activity should filter rosters down to only those for user_1
    roster = result["roster"]
    assert len(roster) == 1
    assert roster[0]["owner_id"] == "user_1"

    # Also verify that when user_id is None, all rosters are returned
    params_all = GetLeagueRosterParams(league_id="league_123", user_id=None)
    result_all = await get_team_owner_rosters(params_all)
    assert len(result_all["rosters"]) == 2  # Note: "rosters" (plural) when user_id=None
