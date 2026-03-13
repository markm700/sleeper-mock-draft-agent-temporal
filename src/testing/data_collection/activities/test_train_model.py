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
from testing.mocks import DummyPyTorchModelManager


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
    """train_team_owner_model trains for requested epochs and returns a loss metric."""
    dummy_pytorch = DummyPyTorchModelManager()

    monkeypatch.setattr(
        "activities.ml.training.train_model.get_pytorch_model_manager",
        lambda: dummy_pytorch,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    samples = [_make_sample(pick_no=i, round_=1) for i in range(1, 6)]

    params = TrainTeamOwnerModelParams(
        model_name="test_train_v1",
        training_samples=samples,
        owner_profile=_dummy_owner_profile(),
        epochs=2,
        learning_rate=0.01,
    )
    result = await train_team_owner_model(params)

    assert result["model_name"] == "test_train_v1"
    assert result["epochs_trained"] == 2
    assert result["num_samples"] == 5
    assert isinstance(result["final_loss"], float)
    assert isinstance(result["initial_loss"], float)
    assert "model_path" in result

    # The model must have been saved (even if the path is stubbed)
    assert len(dummy_pytorch.save_calls) == 1
    assert dummy_pytorch.save_calls[0]["model_name"] == "test_train_v1"


@pytest.mark.asyncio
async def test_train_model_zero_samples_returns_early(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """When training_samples is empty, training is skipped and epochs_trained=0."""
    dummy_pytorch = DummyPyTorchModelManager()

    monkeypatch.setattr(
        "activities.ml.training.train_model.get_pytorch_model_manager",
        lambda: dummy_pytorch,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    params = TrainTeamOwnerModelParams(
        model_name="empty_model",
        training_samples=[],
        owner_profile=_dummy_owner_profile(),
        epochs=10,
    )
    result = await train_team_owner_model(params)

    assert result["epochs_trained"] == 0
    assert result["num_samples"] == 0
    assert result["final_loss"] == 0.0
    # No training → no save call should have been made
    assert len(dummy_pytorch.save_calls) == 0


@pytest.mark.asyncio
async def test_train_model_uses_existing_model_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """When a model file already exists on disk, train_model loads rather than rebuilds."""
    dummy_pytorch = DummyPyTorchModelManager()

    # Pre-cache a model so load_model() succeeds
    dummy_pytorch.build_team_owner_model(
        player_feature_dim=PLAYER_FEATURE_DIM,
        owner_profile_dim=OWNER_PROFILE_DIM,
        draft_context_dim=DRAFT_CONTEXT_DIM,
        model_name="pretrained_v1",
    )

    monkeypatch.setattr(
        "activities.ml.training.train_model.get_pytorch_model_manager",
        lambda: dummy_pytorch,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    # Write a dummy file so Path(model_path).exists() returns True
    (tmp_path / "pretrained_v1.pt").write_bytes(b"fake")

    samples = [_make_sample()]
    params = TrainTeamOwnerModelParams(
        model_name="pretrained_v1",
        training_samples=samples,
        owner_profile=_dummy_owner_profile(),
        epochs=1,
    )
    result = await train_team_owner_model(params)

    # Should have used load_model, not build_team_owner_model again
    assert len(dummy_pytorch.build_calls) == 1  # only the pre-setup call
    assert len(dummy_pytorch.load_calls) >= 1
    assert result["epochs_trained"] == 1


@pytest.mark.asyncio
async def test_train_model_loss_decreases_over_epochs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """With multiple samples and epochs, final_loss should not exceed initial_loss."""
    dummy_pytorch = DummyPyTorchModelManager()

    monkeypatch.setattr(
        "activities.ml.training.train_model.get_pytorch_model_manager",
        lambda: dummy_pytorch,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    samples = [_make_sample(pick_no=i) for i in range(1, 11)]
    params = TrainTeamOwnerModelParams(
        model_name="converging_model",
        training_samples=samples,
        owner_profile=_dummy_owner_profile(),
        epochs=5,
        learning_rate=0.01,
    )
    result = await train_team_owner_model(params)

    assert result["epochs_trained"] == 5
    # After 5 epochs gradient descent should have made some progress
    # (or at worst stayed the same — allow for equal values)
    assert result["final_loss"] <= result["initial_loss"] + 1e-3
