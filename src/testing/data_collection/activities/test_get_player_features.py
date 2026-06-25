from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from activities.ml.predictions.predict_player_pick import (
    GetPlayerFeaturesParams,
    get_player_features_from_db,
)
from testing.mocks import DummyPostgresClient


# ---------------------------------------------------------------------------
# Minimal Player stub that mirrors the ORM model's attribute access
# ---------------------------------------------------------------------------

@dataclass
class _FakePlayer:
    player_id: str
    full_name: str
    position: str
    age: int
    years_exp: int
    status: str
    team: str
    injury_status: Optional[str] = None


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_player_features_returns_features_for_known_players(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Features are built for every player returned by the session."""
    dummy_postgres = DummyPostgresClient()

    fake_players = [
        _FakePlayer("player_1", "Patrick Mahomes", "QB", 28, 6, "Active", "KC"),
        _FakePlayer("player_2", "Christian McCaffrey", "RB", 27, 6, "Active", "SF",
                    injury_status="Questionable"),
    ]
    dummy_postgres.session.configure_execute("Player", fake_players)

    monkeypatch.setattr(
        "activities.ml.predictions.predict_player_pick.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = GetPlayerFeaturesParams(player_ids=["player_1", "player_2"])
    result = await get_player_features_from_db(params)

    assert result["num_players"] == 2
    assert result["missing_players"] == 0
    assert len(result["player_features"]) == 2

    feature_map = {f["player_id"]: f for f in result["player_features"]}

    p1 = feature_map["player_1"]
    assert p1["full_name"] == "Patrick Mahomes"
    assert p1["position"] == "QB"
    assert p1["age"] == 28
    assert p1["years_exp"] == 6
    assert p1["injury_status"] is None
    # Default ADP values when no adp_data supplied
    assert p1["adp"] == 999.0
    assert p1["adp_std"] == 0.0
    assert p1["times_drafted"] == 0

    p2 = feature_map["player_2"]
    assert p2["injury_status"] == "Questionable"


@pytest.mark.asyncio
async def test_get_player_features_merges_adp_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADP fields in the feature dict are populated from the supplied adp_data."""
    dummy_postgres = DummyPostgresClient()

    fake_players = [
        _FakePlayer("player_1", "Patrick Mahomes", "QB", 28, 6, "Active", "KC"),
    ]
    dummy_postgres.session.configure_execute("Player", fake_players)

    monkeypatch.setattr(
        "activities.ml.predictions.predict_player_pick.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    adp_data = {
        "player_1": {"adp": 15.5, "std_dev": 2.3, "times_drafted": 8},
    }

    params = GetPlayerFeaturesParams(player_ids=["player_1"], adp_data=adp_data)
    result = await get_player_features_from_db(params)

    feature = result["player_features"][0]
    assert feature["adp"] == pytest.approx(15.5)
    assert feature["adp_std"] == pytest.approx(2.3)
    assert feature["times_drafted"] == 8


@pytest.mark.asyncio
async def test_get_player_features_missing_players_counted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """missing_players reflects the gap between requested and returned player counts."""
    dummy_postgres = DummyPostgresClient()

    # Only one player returned even though two were requested
    fake_players = [
        _FakePlayer("player_1", "Patrick Mahomes", "QB", 28, 6, "Active", "KC"),
    ]
    dummy_postgres.session.configure_execute("Player", fake_players)

    monkeypatch.setattr(
        "activities.ml.predictions.predict_player_pick.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = GetPlayerFeaturesParams(player_ids=["player_1", "player_missing"])
    result = await get_player_features_from_db(params)

    assert result["num_players"] == 1
    assert result["missing_players"] == 1


@pytest.mark.asyncio
async def test_get_player_features_returns_empty_for_no_players(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty player_ids list yields an empty player_features list."""
    dummy_postgres = DummyPostgresClient()
    dummy_postgres.session.configure_execute("Player", [])

    monkeypatch.setattr(
        "activities.ml.predictions.predict_player_pick.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = GetPlayerFeaturesParams(player_ids=[])
    result = await get_player_features_from_db(params)

    assert result["num_players"] == 0
    assert result["missing_players"] == 0
    assert result["player_features"] == []
