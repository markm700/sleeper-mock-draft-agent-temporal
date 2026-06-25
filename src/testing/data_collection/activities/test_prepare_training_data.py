from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from activities.ml.training.prepare_training_data import (
    OWNER_PROFILE_DIM,
    PrepareOwnerTrainingDataParams,
    prepare_owner_training_data,
)
from testing.mocks import DummyPostgresClient


# ---------------------------------------------------------------------------
# Lightweight ORM stubs
# ---------------------------------------------------------------------------

@dataclass
class _FakeTeamOwner:
    user_id: str
    league_id: str
    display_name: str = "Owner 1"


@dataclass
class _FakeDraft:
    draft_id: str
    league_id: str
    season: str = "2024"


@dataclass
class _FakeDraftPick:
    draft_id: str
    pick_no: int
    round: int
    draft_slot: int = 1
    picked_by: Optional[str] = None
    player_id: Optional[str] = None
    roster_id: Optional[int] = None


@dataclass
class _FakePlayer:
    player_id: str
    full_name: str
    position: str
    age: int = 25
    years_exp: int = 3
    status: str = "Active"
    team: str = "KC"
    injury_status: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers to pre-seed the DummyPostgresClient session
# ---------------------------------------------------------------------------

def _seeded_postgres(
    *,
    team_owner: Optional[_FakeTeamOwner],
    drafts: List[_FakeDraft],
    all_picks: List[_FakeDraftPick],
    players: List[_FakePlayer],
) -> DummyPostgresClient:
    dummy = DummyPostgresClient()
    dummy.session.configure_query(
        "TeamOwner", [team_owner] if team_owner else []
    )
    dummy.session.configure_query("Draft", drafts)
    dummy.session.configure_query("DraftPick", all_picks)
    dummy.session.configure_execute("Player", players)
    return dummy


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prepare_training_data_returns_samples_and_owner_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: produces training samples and a 26-dim owner profile."""
    owner = _FakeTeamOwner(user_id="user_1", league_id="league-1")
    draft = _FakeDraft(draft_id="draft_1", league_id="league-1")
    # Simulate owner picking player_1 at pick 1, then others picking player_2..5
    picks = [
        _FakeDraftPick("draft_1", 1, 1, 1, picked_by="user_1", player_id="player_1"),
        _FakeDraftPick("draft_1", 2, 1, 2, picked_by="user_2", player_id="player_2"),
        _FakeDraftPick("draft_1", 3, 1, 3, picked_by="user_2", player_id="player_3"),
        _FakeDraftPick("draft_1", 4, 1, 4, picked_by="user_2", player_id="player_4"),
        _FakeDraftPick("draft_1", 5, 1, 5, picked_by="user_2", player_id="player_5"),
        _FakeDraftPick("draft_1", 6, 1, 6, picked_by="user_2", player_id="player_6"),
        _FakeDraftPick("draft_1", 7, 1, 7, picked_by="user_2", player_id="player_7"),
        _FakeDraftPick("draft_1", 8, 1, 8, picked_by="user_2", player_id="player_8"),
        _FakeDraftPick("draft_1", 9, 1, 9, picked_by="user_2", player_id="player_9"),
        _FakeDraftPick("draft_1", 10, 1, 10, picked_by="user_2", player_id="player_10"),
        _FakeDraftPick("draft_1", 11, 2, 1, picked_by="user_1", player_id="player_11"),
        _FakeDraftPick("draft_1", 12, 2, 2, picked_by="user_2", player_id="player_12"),
    ]
    players = [
        _FakePlayer(f"player_{i}", f"Player {i}", "WR") for i in range(1, 13)
    ]

    dummy_postgres = _seeded_postgres(
        team_owner=owner, drafts=[draft], all_picks=picks, players=players
    )
    monkeypatch.setattr(
        "activities.ml.training.prepare_training_data.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = PrepareOwnerTrainingDataParams(
        league_id="league-1",
        user_id="user_1",
        min_picks_required=1,
    )
    result = await prepare_owner_training_data(params)

    assert result["user_id"] == "user_1"
    assert result["league_id"] == "league-1"
    assert result["num_samples"] == 2  # user_1 made 2 picks

    # owner_profile must be a list of exactly OWNER_PROFILE_DIM floats
    assert isinstance(result["owner_profile"], list)
    assert len(result["owner_profile"]) == OWNER_PROFILE_DIM
    assert all(isinstance(v, float) for v in result["owner_profile"])

    # Each training sample must have the expected keys
    for sample in result["training_samples"]:
        assert "pick_no" in sample
        assert "round" in sample
        assert "candidate_features" in sample
        assert "context" in sample
        assert "target_idx" in sample
        assert sample["target_idx"] == 0  # positive is always first


@pytest.mark.asyncio
async def test_prepare_training_data_insufficient_picks_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Activity returns empty result when owner has fewer picks than min_picks_required."""
    owner = _FakeTeamOwner(user_id="user_1", league_id="league-1")
    draft = _FakeDraft(draft_id="draft_1", league_id="league-1")
    # Owner makes only 1 pick; require at least 5
    picks = [
        _FakeDraftPick("draft_1", 1, 1, 1, picked_by="user_1", player_id="player_1"),
        _FakeDraftPick("draft_1", 2, 1, 2, picked_by="user_2", player_id="player_2"),
    ]
    players = [
        _FakePlayer("player_1", "Player 1", "QB"),
        _FakePlayer("player_2", "Player 2", "RB"),
    ]

    dummy_postgres = _seeded_postgres(
        team_owner=owner, drafts=[draft], all_picks=picks, players=players
    )
    monkeypatch.setattr(
        "activities.ml.training.prepare_training_data.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = PrepareOwnerTrainingDataParams(
        league_id="league-1",
        user_id="user_1",
        min_picks_required=5,
    )
    result = await prepare_owner_training_data(params)

    assert result["num_samples"] == 0
    assert result["training_samples"] == []
    assert len(result["owner_profile"]) == OWNER_PROFILE_DIM


@pytest.mark.asyncio
async def test_prepare_training_data_no_drafts_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Activity returns empty result when no drafts exist for the league."""
    owner = _FakeTeamOwner(user_id="user_1", league_id="league-1")

    dummy_postgres = _seeded_postgres(
        team_owner=owner, drafts=[], all_picks=[], players=[]
    )
    monkeypatch.setattr(
        "activities.ml.training.prepare_training_data.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = PrepareOwnerTrainingDataParams(league_id="league-1", user_id="user_1")
    result = await prepare_owner_training_data(params)

    assert result["num_samples"] == 0
    assert result["training_samples"] == []


@pytest.mark.asyncio
async def test_prepare_training_data_team_owner_not_found_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Activity raises ValueError when the TeamOwner record does not exist."""
    dummy_postgres = _seeded_postgres(
        team_owner=None, drafts=[], all_picks=[], players=[]
    )
    monkeypatch.setattr(
        "activities.ml.training.prepare_training_data.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = PrepareOwnerTrainingDataParams(league_id="league-1", user_id="ghost_user")

    with pytest.raises(ValueError, match="TeamOwner not found"):
        await prepare_owner_training_data(params)


@pytest.mark.asyncio
async def test_prepare_training_data_candidate_features_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each candidate_features entry is a list of lists with the expected inner dimension."""
    owner = _FakeTeamOwner(user_id="user_1", league_id="league-1")
    draft = _FakeDraft(draft_id="draft_1", league_id="league-1")
    picks = [
        _FakeDraftPick("draft_1", 1, 1, 1, picked_by="user_1", player_id="player_1"),
        _FakeDraftPick("draft_1", 2, 1, 2, picked_by="user_2", player_id="player_2"),
        _FakeDraftPick("draft_1", 3, 1, 3, picked_by="user_2", player_id="player_3"),
    ]
    players = [
        _FakePlayer("player_1", "Player 1", "QB"),
        _FakePlayer("player_2", "Player 2", "RB"),
        _FakePlayer("player_3", "Player 3", "WR"),
    ]

    dummy_postgres = _seeded_postgres(
        team_owner=owner, drafts=[draft], all_picks=picks, players=players
    )
    monkeypatch.setattr(
        "activities.ml.training.prepare_training_data.get_postgres_client_manager",
        lambda: dummy_postgres,
    )

    params = PrepareOwnerTrainingDataParams(
        league_id="league-1", user_id="user_1", min_picks_required=1
    )
    result = await prepare_owner_training_data(params)

    assert result["num_samples"] == 1
    sample = result["training_samples"][0]
    candidates = sample["candidate_features"]

    # Each candidate feature vector should be 9-dimensional (PLAYER_FEATURE_DIM)
    for feat_vec in candidates:
        assert isinstance(feat_vec, list)
        assert len(feat_vec) == 9
