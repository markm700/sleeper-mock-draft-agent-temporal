import pytest

from activities.draft.get_drafts import GetLeagueDraftsParams, get_league_drafts
from testing.mocks import DummySleeperClient, DummyPostgresClient


@pytest.mark.asyncio
async def test_get_league_drafts_wraps_client_response(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """get_league_drafts should call the Sleeper client and wrap the
    returned list under the "league_drafts" key.
    """

    dummy_sleeper = DummySleeperClient()
    dummy_postgres = DummyPostgresClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_sleeper

    def _fake_get_postgres_client_manager() -> DummyPostgresClient:
        return dummy_postgres

    # Patch the dependency inside the activity module so no real
    # HTTP requests or environment variables are required.
    monkeypatch.setattr(
        "src.activities.draft.get_drafts.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )
    
    monkeypatch.setattr(
        "src.activities.draft.get_drafts.get_postgres_client_manager",
        _fake_get_postgres_client_manager,
    )

    params = GetLeagueDraftsParams(league_id="league_123")

    result = await get_league_drafts(params)

    # Verify league_drafts returned from API
    assert "league_drafts" in result
    assert len(result["league_drafts"]) == 2
    assert all(draft["league_id"] == "league_123" for draft in result["league_drafts"])
    assert dummy_sleeper.called_with_league_ids == ["league_123"]
    
    # Verify database bulk upserts were called for drafts
    assert dummy_postgres.count_upserts_for_model("Draft") == 2
    
    # Verify bulk upserted draft data structure
    drafts = dummy_postgres.get_bulk_upserted_by_model("Draft")
    assert len(drafts) == 2
    assert all("draft_id" in draft for draft in drafts)
    assert all("league_id" in draft for draft in drafts)
    assert all(draft["league_id"] == "league_123" for draft in drafts)
