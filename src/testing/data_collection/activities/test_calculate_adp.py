import math

import pytest

from activities.ml.calculate_adp import CalculateADPFromPicksParams, calculate_adp_from_picks
from testing.mocks import DummyPostgresClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_draft_id_rows(*draft_ids: str):
    """Return query rows as the activity expects them: list of 1-tuples."""
    return [(d,) for d in draft_ids]


def _make_pick_rows(draft_id: str, picks: list):
    """
    Return pick rows in the format:
        (player_id, pick_no, draft_id)
    """
    return [(player_id, pick_no, draft_id) for player_id, pick_no in picks]


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calculate_adp_basic_unweighted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unweighted ADP is the arithmetic mean of pick numbers."""
    dummy_postgres = DummyPostgresClient()

    # Two drafts with player_1 picked at positions 2 and 4 → ADP=3.0
    dummy_postgres.session.configure_query(
        "Draft", _make_draft_id_rows("draft_1", "draft_2")
    )
    draft_picks = _make_pick_rows("draft_1", [("player_1", 2), ("player_2", 5)]) + \
                  _make_pick_rows("draft_2", [("player_1", 4), ("player_2", 6)])
    dummy_postgres.session.configure_query("DraftPick", draft_picks)

    monkeypatch.setattr(
        "activities.ml.calculate_adp.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = CalculateADPFromPicksParams(
        league_id="league-1",
        season=None,
        weighted=False,
        min_times_drafted=1,
    )
    result = await calculate_adp_from_picks(params)

    assert result["league_id"] == "league-1"
    assert result["weighted"] is False
    assert result["num_drafts"] == 2
    assert result["num_picks"] == 4

    adp_data = result["adp_data"]
    assert "player_1" in adp_data
    assert adp_data["player_1"]["times_drafted"] == 2
    assert adp_data["player_1"]["adp"] == pytest.approx(3.0)

    assert "player_2" in adp_data
    assert adp_data["player_2"]["adp"] == pytest.approx(5.5)


@pytest.mark.asyncio
async def test_calculate_adp_weighted_decays_older_drafts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With weighted=True, older drafts contribute less (decay=0.7)."""
    dummy_postgres = DummyPostgresClient()

    # draft_1 is "older" (lexicographically smaller), draft_2 is "newer"
    draft_ids = ["draft_a", "draft_b"]
    dummy_postgres.session.configure_query("Draft", _make_draft_id_rows(*draft_ids))

    pick_rows = (
        _make_pick_rows("draft_a", [("player_1", 10)])  # older, weight=0.7
        + _make_pick_rows("draft_b", [("player_1", 2)])  # newer, weight=1.0
    )
    dummy_postgres.session.configure_query("DraftPick", pick_rows)

    monkeypatch.setattr(
        "activities.ml.calculate_adp.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = CalculateADPFromPicksParams(
        league_id="league-1",
        weighted=True,
        min_times_drafted=1,
    )
    result = await calculate_adp_from_picks(params)

    # Weighted mean: (10*0.7 + 2*1.0) / (0.7 + 1.0) = 9.0 / 1.7
    expected_adp = round((10 * 0.7 + 2 * 1.0) / (0.7 + 1.0), 2)
    assert result["adp_data"]["player_1"]["adp"] == pytest.approx(expected_adp, abs=0.01)


@pytest.mark.asyncio
async def test_calculate_adp_min_times_drafted_filters_players(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Players drafted fewer than min_times_drafted times are excluded from output."""
    dummy_postgres = DummyPostgresClient()

    dummy_postgres.session.configure_query("Draft", _make_draft_id_rows("draft_1"))
    dummy_postgres.session.configure_query(
        "DraftPick",
        _make_pick_rows("draft_1", [("player_1", 1), ("player_2", 2)]),
    )

    monkeypatch.setattr(
        "activities.ml.calculate_adp.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    # Both players are drafted exactly once; min=2 should exclude both
    params = CalculateADPFromPicksParams(
        league_id="league-1",
        weighted=False,
        min_times_drafted=2,
    )
    result = await calculate_adp_from_picks(params)

    assert result["adp_data"] == {}
    assert result["num_players"] == 0


@pytest.mark.asyncio
async def test_calculate_adp_season_filter_is_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Passing a season sets the correct field in the returned result."""
    dummy_postgres = DummyPostgresClient()

    dummy_postgres.session.configure_query("Draft", _make_draft_id_rows("draft_1"))
    dummy_postgres.session.configure_query(
        "DraftPick",
        _make_pick_rows("draft_1", [("player_1", 3)]),
    )

    monkeypatch.setattr(
        "activities.ml.calculate_adp.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = CalculateADPFromPicksParams(league_id="league-1", season="2024")
    result = await calculate_adp_from_picks(params)

    assert result["season"] == "2024"
    assert "player_1" in result["adp_data"]


# ---------------------------------------------------------------------------
# Edge-case / error-path tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calculate_adp_no_drafts_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When no drafts exist for the league the activity returns an empty payload."""
    dummy_postgres = DummyPostgresClient()

    dummy_postgres.session.configure_query("Draft", [])

    monkeypatch.setattr(
        "activities.ml.calculate_adp.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = CalculateADPFromPicksParams(league_id="ghost-league")
    result = await calculate_adp_from_picks(params)

    assert result["adp_data"] == {}
    assert result["num_players"] == 0
    assert result["num_drafts"] == 0
    assert result["num_picks"] == 0


@pytest.mark.asyncio
async def test_calculate_adp_std_dev_is_zero_for_single_pick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A player drafted exactly once in a single draft has std_dev=0.0."""
    dummy_postgres = DummyPostgresClient()

    dummy_postgres.session.configure_query("Draft", _make_draft_id_rows("draft_1"))
    dummy_postgres.session.configure_query(
        "DraftPick",
        _make_pick_rows("draft_1", [("player_1", 7)]),
    )

    monkeypatch.setattr(
        "activities.ml.calculate_adp.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = CalculateADPFromPicksParams(
        league_id="league-1", weighted=False, min_times_drafted=1
    )
    result = await calculate_adp_from_picks(params)

    assert result["adp_data"]["player_1"]["adp"] == pytest.approx(7.0)
    assert result["adp_data"]["player_1"]["std_dev"] == pytest.approx(0.0)
    assert result["adp_data"]["player_1"]["times_drafted"] == 1
