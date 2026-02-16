import pytest

from activities.draft.get_drafts import GetLeagueDraftsParams, get_league_drafts
from testing.mocks import DummySleeperClient


@pytest.mark.asyncio
async def test_get_league_drafts_wraps_client_response(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """get_league_drafts should call the Sleeper client and wrap the
    returned list under the "league_drafts" key.
    """

    dummy_client = DummySleeperClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_client

    # Patch the dependency inside the activity module so no real
    # HTTP requests or environment variables are required.
    monkeypatch.setattr(
        "src.activities.draft.get_drafts.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )

    params = GetLeagueDraftsParams(league_id="league_123")

    result = await get_league_drafts(params)

    assert result == {
        "league_drafts": [
            {"league_id": "league_123", "draft_id": "draft_1"},
            {"league_id": "league_123", "draft_id": "draft_2"},
        ]
    }
    assert dummy_client.called_with_league_ids == ["league_123"]
