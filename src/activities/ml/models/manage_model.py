"""
Activities for building and managing team owner draft prediction models.

Wraps MLModelManager (joblib) to provide Temporal-compatible activities for
model lifecycle management: building, querying status, and cache eviction.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.ml_client import get_ml_model_manager
    from activities.ml.models.model_interface import DraftModel
    from activities.ml.models.team_owner_model import (
        DRAFT_CONTEXT_DIM,
        OWNER_PROFILE_DIM,
        PLAYER_FEATURE_DIM,
        TeamOwnerDraftModel,
    )


@dataclass
class BuildOwnerModelParams:
    """
    Parameters for building a new team owner draft prediction model.

    Args:
        model_name: Unique model identifier, e.g. "owner_{user_id}_{league_id}_v1".
        player_feature_dim: Per-player feature dimension (default 9).
        owner_profile_dim: Owner historical profile dimension (default 26).
        draft_context_dim: Draft-state context dimension (default 8).
        personality_dim: Personality trait vector dimension (default 8).
        overwrite: Force rebuild even if model exists on disk (default False).
    """

    model_name: str
    player_feature_dim: int = PLAYER_FEATURE_DIM
    owner_profile_dim: int = OWNER_PROFILE_DIM
    draft_context_dim: int = DRAFT_CONTEXT_DIM
    personality_dim: int = 8
    overwrite: bool = False


def _ensure_conforms(model: Any, model_name: str) -> None:
    """
    Verify a model satisfies the DraftModel structural interface.

    Guards the model-management workflow against a backend that is missing a
    required attribute or method. This is a lightweight presence check (the
    runtime_checkable Protocol does not validate signatures).

    Args:
        model: The model object to check.
        model_name: Model identifier, used in the error message.

    Raises:
        TypeError: If the model does not conform to DraftModel.
    """
    if not isinstance(model, DraftModel):
        raise TypeError(
            f"Model '{model_name}' ({type(model).__name__}) does not satisfy the "
            "DraftModel interface"
        )


@activity.defn(name="build_owner_model")
async def build_owner_model(input: BuildOwnerModelParams) -> Dict[str, Any]:
    """
    Build and save a new TeamOwnerDraftModel (untrained scaffold).

    Creates a fresh model instance with the specified architecture dimensions
    and persists it to MODEL_PATH via joblib. If a model already exists on disk
    and overwrite=False, returns the existing model info without rebuilding.

    Args:
        input: BuildOwnerModelParams with model_name, architecture dims, and overwrite flag.

    Returns:
        Dict[str, Any]: {"model_name": str, "model_path": str, "created": bool, ...}
    """
    ml_manager = get_ml_model_manager()
    base_path = os.getenv("MODEL_PATH", "/app/models")
    model_path = str(Path(base_path) / f"{input.model_name}.joblib")

    try:
        if Path(model_path).exists() and not input.overwrite:
            activity.logger.info(f"Model already exists at {model_path}, skipping build (overwrite=False)")
            model: DraftModel = ml_manager.load_model(input.model_name, model_path=model_path)
            _ensure_conforms(model, input.model_name)
            return {
                "model_name": input.model_name,
                "model_path": model_path,
                "model_type": type(model).__name__,
                "config": model.get_config(),
                "created": False,
            }

        model = TeamOwnerDraftModel(
            player_feature_dim=input.player_feature_dim,
            owner_profile_dim=input.owner_profile_dim,
            draft_context_dim=input.draft_context_dim,
            personality_dim=input.personality_dim,
        )
        _ensure_conforms(model, input.model_name)

        saved_path = ml_manager.save_model(model, input.model_name, save_path=model_path)
        activity.logger.info(f"Built and saved model '{input.model_name}' → {saved_path}")
        return {
            "model_name": input.model_name,
            "model_path": saved_path,
            "model_type": type(model).__name__,
            "config": model.get_config(),
            "created": True,
        }

    except Exception as e:
        activity.logger.error(f"Failed to build model '{input.model_name}': {str(e)}")
        raise


@dataclass
class GetModelStatusParams:
    """
    Parameters for querying model on-disk and in-memory status.

    Args:
        model_name: Unique model identifier to query.
    """

    model_name: str


@activity.defn(name="get_model_status")
async def get_model_status(input: GetModelStatusParams) -> Dict[str, Any]:
    """
    Query the on-disk and in-memory status of a model without loading it.

    Args:
        input: GetModelStatusParams with model_name.

    Returns:
        Dict[str, Any]: {"model_name": str, "exists_on_disk": bool, "model_path": str, "size_bytes": int | None, "cached_in_memory": bool}
    """
    ml_manager = get_ml_model_manager()
    base_path = os.getenv("MODEL_PATH", "/app/models")
    model_path = str(Path(base_path) / f"{input.model_name}.joblib")

    try:
        path_obj = Path(model_path)
        exists = path_obj.exists()
        size_bytes = path_obj.stat().st_size if exists else None
        cached = input.model_name in ml_manager._models

        activity.logger.info(
            f"Model '{input.model_name}': exists_on_disk={exists}, "
            f"size_bytes={size_bytes}, cached_in_memory={cached}"
        )
        return {
            "model_name": input.model_name,
            "exists_on_disk": exists,
            "model_path": model_path,
            "size_bytes": size_bytes,
            "cached_in_memory": cached,
        }

    except Exception as e:
        activity.logger.error(f"Failed to query model status for '{input.model_name}': {str(e)}")
        raise


@activity.defn(name="list_models")
async def list_models() -> Dict[str, Any]:
    """
    List all models on disk and their cache status.

    Scans MODEL_PATH for .joblib files and reports which are cached in memory.

    Returns:
        Dict[str, Any]: {"models": [{"model_name": str, "model_path": str, "size_bytes": int, "cached_in_memory": bool}, ...], "num_models": int}
    """
    ml_manager = get_ml_model_manager()
    base_path = os.getenv("MODEL_PATH", "/app/models")

    try:
        models_dir = Path(base_path)
        models_dir.mkdir(parents=True, exist_ok=True)
        model_files = sorted(models_dir.glob("*.joblib"))

        models = []
        for model_file in model_files:
            model_name = model_file.stem
            models.append({
                "model_name": model_name,
                "model_path": str(model_file),
                "size_bytes": model_file.stat().st_size,
                "cached_in_memory": model_name in ml_manager._models,
            })

        activity.logger.info(f"Listed {len(models)} models from {base_path}")
        return {"models": models, "num_models": len(models)}

    except Exception as e:
        activity.logger.error(f"Failed to list models: {str(e)}")
        raise


@dataclass
class DeleteModelParams:
    """
    Parameters for deleting a model from disk and cache.

    Args:
        model_name: Unique model identifier to delete.
    """

    model_name: str


@activity.defn(name="delete_model")
async def delete_model(input: DeleteModelParams) -> Dict[str, Any]:
    """
    Delete a model from disk and evict it from the in-memory cache.

    Args:
        input: DeleteModelParams with model_name.

    Returns:
        Dict[str, Any]: {"model_name": str, "deleted_from_disk": bool, "evicted_from_cache": bool}
    """
    ml_manager = get_ml_model_manager()
    base_path = os.getenv("MODEL_PATH", "/app/models")
    model_path = Path(base_path) / f"{input.model_name}.joblib"

    try:
        deleted_from_disk = False
        if model_path.exists():
            model_path.unlink()
            deleted_from_disk = True
            activity.logger.info(f"Deleted model file: {model_path}")

        evicted_from_cache = input.model_name in ml_manager._models
        if evicted_from_cache:
            ml_manager.unload_model(input.model_name)

        activity.logger.info(
            f"Model '{input.model_name}': deleted_from_disk={deleted_from_disk}, "
            f"evicted_from_cache={evicted_from_cache}"
        )
        return {
            "model_name": input.model_name,
            "deleted_from_disk": deleted_from_disk,
            "evicted_from_cache": evicted_from_cache,
        }

    except Exception as e:
        activity.logger.error(f"Failed to delete model '{input.model_name}': {str(e)}")
        raise
