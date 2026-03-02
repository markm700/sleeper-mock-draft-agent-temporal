import pytest

from activities.draft.get_draft_picks import (
    GetSpecificDraftPicksParams,
    get_specific_draft_picks,
)
from testing.mocks import DummySleeperClient, DummyPostgresClient


@pytest.mark.asyncio
async def test_get_specific_draft_picks_uses_client_and_wraps(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_sleeper = DummySleeperClient()
    dummy_postgres = DummyPostgresClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_sleeper

    def _fake_get_postgres_client_manager() -> DummyPostgresClient:
        return dummy_postgres

    monkeypatch.setattr(
        "src.activities.draft.get_draft_picks.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )
    
    monkeypatch.setattr(
        "src.activities.draft.get_draft_picks.get_postgres_client_manager",
        _fake_get_postgres_client_manager,
    )

    params = GetSpecificDraftPicksParams(draft_id="draft_123")

    result = await get_specific_draft_picks(params)

    assert "draft_picks" in result
    assert len(result["draft_picks"]) == 2
    assert all(pick["draft_id"] == "draft_123" for pick in result["draft_picks"])
    assert dummy_sleeper.called_with_draft_ids == ["draft_123"]
    
    # Verify database upserts were called for draft picks
    assert dummy_postgres.count_upserts_for_model("DraftPick") == 2
