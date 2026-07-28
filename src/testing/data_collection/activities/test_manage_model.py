import os
from pathlib import Path

import pytest

from activities.ml.models.manage_model import (
    BuildOwnerModelParams,
    GetModelStatusParams,
    build_owner_model,
    get_model_status,
)
from testing.mocks import DummyMLModelManager


# ---------------------------------------------------------------------------
# build_owner_model tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_owner_model_creates_fresh_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """build_owner_model builds and caches a new model when none exists on disk."""
    dummy_ml = DummyMLModelManager()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_ml_model_manager",
        lambda: dummy_ml,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    params = BuildOwnerModelParams(model_name="test_model_v1")
    result = await build_owner_model(params)

    assert result["model_name"] == "test_model_v1"
    assert result["created"] is True
    assert "model_path" in result

    # Model should now be cached
    assert "test_model_v1" in dummy_ml._models


@pytest.mark.asyncio
async def test_build_owner_model_skips_existing_when_overwrite_false(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """build_owner_model returns existing info without rebuilding when overwrite=False."""
    dummy_ml = DummyMLModelManager()

    # Pre-cache a model
    from activities.ml.models.team_owner_model import TeamOwnerDraftModel
    dummy_ml._models["existing_model"] = TeamOwnerDraftModel()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_ml_model_manager",
        lambda: dummy_ml,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    # Create a fake model file so the activity believes it exists on disk
    model_file = tmp_path / "existing_model.joblib"
    model_file.write_bytes(b"fake-weights")

    params = BuildOwnerModelParams(model_name="existing_model", overwrite=False)
    result = await build_owner_model(params)

    assert result["created"] is False


@pytest.mark.asyncio
async def test_build_owner_model_overwrite_rebuilds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """build_owner_model rebuilds when overwrite=True even if the file exists."""
    dummy_ml = DummyMLModelManager()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_ml_model_manager",
        lambda: dummy_ml,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    model_file = tmp_path / "rebuild_model.joblib"
    model_file.write_bytes(b"old-weights")

    params = BuildOwnerModelParams(model_name="rebuild_model", overwrite=True)
    result = await build_owner_model(params)

    assert result["created"] is True


@pytest.mark.asyncio
async def test_build_owner_model_defaults_to_team_owner_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """The default model_type builds a TeamOwnerDraftModel via the registry factory."""
    dummy_ml = DummyMLModelManager()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_ml_model_manager",
        lambda: dummy_ml,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    params = BuildOwnerModelParams(model_name="default_type_model")
    result = await build_owner_model(params)

    assert result["created"] is True
    assert result["model_type"] == "TeamOwnerDraftModel"
    assert type(dummy_ml._models["default_type_model"]).__name__ == "TeamOwnerDraftModel"


@pytest.mark.asyncio
async def test_build_owner_model_explicit_model_type(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """An explicit registered model_type is honoured by the factory."""
    dummy_ml = DummyMLModelManager()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_ml_model_manager",
        lambda: dummy_ml,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    params = BuildOwnerModelParams(
        model_name="explicit_type_model",
        model_type="TeamOwnerDraftModel",
    )
    result = await build_owner_model(params)

    assert result["created"] is True
    assert result["model_type"] == "TeamOwnerDraftModel"


@pytest.mark.asyncio
async def test_build_owner_model_unknown_model_type_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """An unregistered model_type surfaces the registry's ValueError."""
    dummy_ml = DummyMLModelManager()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_ml_model_manager",
        lambda: dummy_ml,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    params = BuildOwnerModelParams(
        model_name="bad_type_model",
        model_type="NoSuchBackend",
    )

    with pytest.raises(ValueError, match="NoSuchBackend"):
        await build_owner_model(params)


# ---------------------------------------------------------------------------
# get_model_status tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_model_status_file_not_found(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """get_model_status reports model does not exist when file is absent."""
    dummy_ml = DummyMLModelManager()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_ml_model_manager",
        lambda: dummy_ml,
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
    dummy_ml = DummyMLModelManager()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_ml_model_manager",
        lambda: dummy_ml,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    model_file = tmp_path / "disk_model.joblib"
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
    dummy_ml = DummyMLModelManager()

    from activities.ml.models.team_owner_model import TeamOwnerDraftModel
    dummy_ml._models["cached_model"] = TeamOwnerDraftModel()

    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_ml_model_manager",
        lambda: dummy_ml,
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path))

    (tmp_path / "cached_model.joblib").write_bytes(b"y" * 256)

    params = GetModelStatusParams(model_name="cached_model")
    result = await get_model_status(params)

    assert result["exists_on_disk"] is True
    assert result["cached_in_memory"] is True
