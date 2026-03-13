import os
from pathlib import Path
from unittest.mock import patch

import pytest

from activities.ml.models.manage_model import (
    BuildOwnerModelParams,
    GetModelStatusParams,
    build_owner_model,
    get_model_status,
)
from testing.mocks import DummyPyTorchModelManager


# ---------------------------------------------------------------------------
# build_owner_model tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_owner_model_creates_fresh_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """build_owner_model builds and caches a new model when none exists on disk."""
    dummy_pytorch = DummyPyTorchModelManager()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_pytorch_model_manager",
        lambda: dummy_pytorch,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    params = BuildOwnerModelParams(model_name="test_model_v1")
    result = await build_owner_model(params)

    # One build call should have been made
    assert len(dummy_pytorch.build_calls) == 1
    assert dummy_pytorch.build_calls[0]["model_name"] == "test_model_v1"

    # Model should now be cached
    assert "test_model_v1" in dummy_pytorch._models

    # Result must indicate the model was created
    assert result["model_name"] == "test_model_v1"
    assert result["created"] is True
    assert result["total_params"] > 0
    assert result["trainable_params"] > 0
    assert "model_path" in result


@pytest.mark.asyncio
async def test_build_owner_model_skips_existing_when_overwrite_false(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """build_owner_model returns existing info without rebuilding when overwrite=False."""
    dummy_pytorch = DummyPyTorchModelManager()

    # Pre-build the model so it is already cached
    dummy_pytorch.build_team_owner_model(
        player_feature_dim=9,
        owner_profile_dim=26,
        draft_context_dim=8,
        model_name="existing_model",
    )

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_pytorch_model_manager",
        lambda: dummy_pytorch,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    # Create a fake model file so the activity believes it exists on disk
    model_file = tmp_path / "existing_model.pt"
    model_file.write_bytes(b"fake-weights")

    params = BuildOwnerModelParams(model_name="existing_model", overwrite=False)
    result = await build_owner_model(params)

    # No additional build call should have been made (already had 1 from setup above)
    assert len(dummy_pytorch.build_calls) == 1
    assert result["created"] is False


@pytest.mark.asyncio
async def test_build_owner_model_overwrite_rebuilds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """build_owner_model rebuilds when overwrite=True even if the file exists."""
    dummy_pytorch = DummyPyTorchModelManager()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_pytorch_model_manager",
        lambda: dummy_pytorch,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    # Create a fake existing model file
    model_file = tmp_path / "rebuild_model.pt"
    model_file.write_bytes(b"old-weights")

    params = BuildOwnerModelParams(model_name="rebuild_model", overwrite=True)
    result = await build_owner_model(params)

    assert result["created"] is True
    assert len(dummy_pytorch.build_calls) == 1


# ---------------------------------------------------------------------------
# get_model_status tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_model_status_file_not_found(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """get_model_status reports model does not exist when file is absent."""
    dummy_pytorch = DummyPyTorchModelManager()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_pytorch_model_manager",
        lambda: dummy_pytorch,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    params = GetModelStatusParams(model_name="nonexistent_model")
    result = await get_model_status(params)

    assert result["model_name"] == "nonexistent_model"
    assert result["exists_on_disk"] is False
    assert result["size_bytes"] is None
    assert result["cached_in_memory"] is False


@pytest.mark.asyncio
async def test_get_model_status_file_exists_on_disk(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """get_model_status detects an on-disk model file and reports its size."""
    dummy_pytorch = DummyPyTorchModelManager()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_pytorch_model_manager",
        lambda: dummy_pytorch,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    # Write a fake model file so Path.exists() returns True
    model_file = tmp_path / "disk_model.pt"
    model_file.write_bytes(b"x" * 512)

    params = GetModelStatusParams(model_name="disk_model")
    result = await get_model_status(params)

    assert result["exists_on_disk"] is True
    assert result["size_bytes"] == 512
    assert result["cached_in_memory"] is False


@pytest.mark.asyncio
async def test_get_model_status_cached_in_memory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """get_model_status reports cached_in_memory=True when the model is in the cache."""
    dummy_pytorch = DummyPyTorchModelManager()

    # Pre-cache the model (simulates a previous build)
    dummy_pytorch.build_team_owner_model(
        player_feature_dim=9,
        owner_profile_dim=26,
        draft_context_dim=8,
        model_name="cached_model",
    )

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_pytorch_model_manager",
        lambda: dummy_pytorch,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    # Also write a file so exists_on_disk is True
    (tmp_path / "cached_model.pt").write_bytes(b"y" * 256)

    params = GetModelStatusParams(model_name="cached_model")
    result = await get_model_status(params)

    assert result["exists_on_disk"] is True
    assert result["cached_in_memory"] is True
