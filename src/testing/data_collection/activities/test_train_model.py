from typing import Any, Dict, List

import pytest

from activities.ml.models.team_owner_model import (
    DRAFT_CONTEXT_DIM,
    OWNER_PROFILE_DIM,
    PLAYER_FEATURE_DIM,
)
from activities.ml.training.train_model import (
    TrainTeamOwnerModelParams,
    train_team_owner_model,
)
from testing.mocks import DummyMLModelManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sample(
    pick_no: int = 1,
    round_: int = 1,
    n_candidates: int = 5,
) -> Dict[str, Any]:
    """Build a minimal training sample with synthetic float feature vectors."""
    candidate_features = [
        [float(i) / 10.0] * PLAYER_FEATURE_DIM for i in range(n_candidates)
    ]
    context = [0.0] * DRAFT_CONTEXT_DIM
    return {
        "pick_no": pick_no,
        "round": round_,
        "candidate_features": candidate_features,
        "context": context,
        "target_idx": 0,
        "draft_id": "draft_1",
    }


def _dummy_owner_profile() -> List[float]:
    return [0.1] * OWNER_PROFILE_DIM


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_train_model_runs_and_returns_metrics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """train_team_owner_model trains and returns result metrics."""
    dummy_ml = DummyMLModelManager()

    monkeypatch.setattr(
        "activities.ml.training.train_model.get_ml_model_manager",
        lambda: dummy_ml,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    samples = [_make_sample(pick_no=i, round_=1) for i in range(1, 6)]

    params = TrainTeamOwnerModelParams(
        model_name="test_train_v1",
        training_samples=samples,
        owner_profile=_dummy_owner_profile(),
        num_boost_round=10,
        learning_rate=0.05,
    )
    result = await train_team_owner_model(params)

    assert result["model_name"] == "test_train_v1"
    assert result["num_boost_round"] == 10
    assert result["num_samples"] == 5
    assert result["num_query_groups"] == 5
    assert "model_path" in result

    # The model must have been saved
    assert len(dummy_ml.save_calls) == 1
    assert dummy_ml.save_calls[0]["model_name"] == "test_train_v1"


@pytest.mark.asyncio
async def test_train_model_zero_samples_returns_early(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """When training_samples is empty, training is skipped."""
    dummy_ml = DummyMLModelManager()

    monkeypatch.setattr(
        "activities.ml.training.train_model.get_ml_model_manager",
        lambda: dummy_ml,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    params = TrainTeamOwnerModelParams(
        model_name="empty_model",
        training_samples=[],
        owner_profile=_dummy_owner_profile(),
        num_boost_round=10,
    )
    result = await train_team_owner_model(params)

    assert result["num_boost_round"] == 0
    assert result["num_samples"] == 0
    assert result["num_query_groups"] == 0
    assert len(dummy_ml.save_calls) == 0
