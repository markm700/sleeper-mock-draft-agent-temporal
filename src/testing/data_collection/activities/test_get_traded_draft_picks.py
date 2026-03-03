import pytest

from activities.draft.get_traded_draft_picks import (
    GetTradedDraftPicksParams,
    get_traded_draft_picks,
)
from testing.mocks import DummySleeperClient, DummyPostgresClient


@pytest.mark.asyncio
async def test_get_traded_draft_picks_fetches_league_traded_picks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_traded_draft_picks activity filters by default season (2025)."""
    dummy_sleeper = DummySleeperClient()
    dummy_postgres = DummyPostgresClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_sleeper

    def _fake_get_postgres_client_manager() -> DummyPostgresClient:
        return dummy_postgres

    monkeypatch.setattr(
        "activities.draft.get_traded_draft_picks.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )
    
    monkeypatch.setattr(
        "activities.draft.get_traded_draft_picks.get_postgres_client_manager",
        _fake_get_postgres_client_manager,
    )

    # Test with default season (2025)
    params = GetTradedDraftPicksParams(league_id="league-456")

    result = await get_traded_draft_picks(params)

    # Verify result structure - should only return 2025 picks (2 out of 4 total)
    assert "traded_draft_picks" in result
    assert len(result["traded_draft_picks"]) == 2
    
    # Verify all returned picks are for season 2025
    for pick in result["traded_draft_picks"]:
        assert pick["season"] == "2025"
        assert "round" in pick
        assert "roster_id" in pick
        assert "owner_id" in pick
        assert "previous_owner_id" in pick

    # Verify the dummy client was called with correct league_id
    assert "league-456" in dummy_sleeper.called_with_league_ids
    
    # Verify database bulk upserts were called for traded picks (2 picks for 2025)
    assert dummy_postgres.count_upserts_for_model("TradedDraftPick") == 2
    
    # Verify bulk upserted traded pick data structure
    traded_picks = dummy_postgres.get_bulk_upserted_by_model("TradedDraftPick")
    assert len(traded_picks) == 2
    assert all("season" in pick for pick in traded_picks)
    assert all(pick["season"] == "2025" for pick in traded_picks)


@pytest.mark.asyncio
async def test_get_traded_draft_picks_filters_by_custom_season(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_traded_draft_picks can filter by a custom season."""
    dummy_sleeper = DummySleeperClient()
    dummy_postgres = DummyPostgresClient()

    def _fake_get_sleeper_client_manager() -> DummySleeperClient:
        return dummy_sleeper

    def _fake_get_postgres_client_manager() -> DummyPostgresClient:
        return dummy_postgres

    monkeypatch.setattr(
        "activities.draft.get_traded_draft_picks.get_sleeper_client_manager",
        _fake_get_sleeper_client_manager,
    )
    
    monkeypatch.setattr(
        "activities.draft.get_traded_draft_picks.get_postgres_client_manager",
        _fake_get_postgres_client_manager,
    )

    # Test with season 2024 - should return 1 pick
    params_2024 = GetTradedDraftPicksParams(league_id="league-789", season="2024")
    result_2024 = await get_traded_draft_picks(params_2024)

    assert len(result_2024["traded_draft_picks"]) == 1
    assert all(pick["season"] == "2024" for pick in result_2024["traded_draft_picks"])

    # Test with season 2026 - should return 1 pick
    params_2026 = GetTradedDraftPicksParams(league_id="league-789", season="2026")
    result_2026 = await get_traded_draft_picks(params_2026)

    assert len(result_2026["traded_draft_picks"]) == 1
    assert all(pick["season"] == "2026" for pick in result_2026["traded_draft_picks"])
    
    # Verify database bulk upserts were called (1 for 2024 + 1 for 2026 = 2 total)
    assert dummy_postgres.count_upserts_for_model("TradedDraftPick") == 2
