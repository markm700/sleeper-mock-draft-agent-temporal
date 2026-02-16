import pytest

from activities.draft.get_draft_picks import (
    GetSpecificDraftPicksParams,
    get_specific_draft_picks,
)
from testing.mocks import DummySleeperClient


@pytest.mark.asyncio
async def test_get_specific_draft_picks_uses_client_and_wraps(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = DummySleeperClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy

    monkeypatch.setattr(
        "src.activities.draft.get_draft_picks.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )

    params = GetSpecificDraftPicksParams(draft_id="draft_123")

    result = await get_specific_draft_picks(params)

    assert "draft_picks" in result
    assert len(result["draft_picks"]) == 2
    assert all(pick["draft_id"] == "draft_123" for pick in result["draft_picks"])
    assert dummy.called_with_draft_ids == ["draft_123"]
