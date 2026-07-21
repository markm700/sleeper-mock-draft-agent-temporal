"""Model management workflow for building and inspecting team owner draft models."""

from pydantic.dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.ml.models.manage_model import (
        BuildOwnerModelParams,
        DeleteModelParams,
        GetModelStatusParams,
        build_owner_model,
        delete_model,
        get_model_status,
        list_models,
    )
    from activities.ml.models.team_owner_model import (
        DRAFT_CONTEXT_DIM,
        OWNER_PROFILE_DIM,
        PLAYER_FEATURE_DIM,
    )


VALID_ACTIONS = ("build", "rebuild", "status", "list", "delete")

    
@dataclass(frozen=True, kw_only=True)
class ModelManagementWorkflowParams:
    """
    Input parameters for ModelManagementWorkflow.

    Fields:
        model_name: Unique model identifier, e.g. "owner_{user_id}_{league_id}_v1".
        action: Lifecycle action — "build", "rebuild", "status", "list", or "delete".
        player_feature_dim: Per-player feature dimension (default 9).
        owner_profile_dim: Owner historical profile dimension (default 26).
        draft_context_dim: Draft-state context dimension (default 8).
        personality_dim: Personality trait vector dimension (default 8).
    """

    model_name: str
    action: str = "status"
    player_feature_dim: int = PLAYER_FEATURE_DIM
    owner_profile_dim: int = OWNER_PROFILE_DIM
    draft_context_dim: int = DRAFT_CONTEXT_DIM
    personality_dim: int = 8


@workflow.defn(name="model-management")
class ModelManagementWorkflow:
    """
    Manage the lifecycle of a team owner draft prediction model.

    Supports three actions:

    * **build** — build the model only if it does not already exist on disk.
      Returns existing model info without touching weights if already present.

    * **rebuild** — force-build a fresh model with randomised weights and
      overwrite the existing checkpoint. Useful after architecture changes or
      hyperparameter updates.

    * **status** — query on-disk file metadata and in-memory cache state
      without loading or modifying the model.

    * **list** — list all models on disk with file size and cache state.

    * **delete** — remove a model from disk and evict from in-memory cache.
    """

    @workflow.run
    async def run(self, params: ModelManagementWorkflowParams) -> Dict[str, Any]:
        """
        Run the model lifecycle action specified in params.

        Args:
            params: ModelManagementWorkflowParams with model_name and action.

        Returns:
            Dict[str, Any]: {"activity_data": [{"activity": str, "result": {...}}, ...]}
        """
        wf_hex = workflow.info().run_id[-4:]
        workflow.logger.info(
            f"ModelManagementWorkflow starting — action={params.action} "
            f"model={params.model_name}"
        )

        activity_retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=2),
            maximum_interval=timedelta(seconds=30),
            backoff_coefficient=2.0,
        )

        action = str(params.action).lower()
        workflow_activities = []

        if action == "status":
            # Query model disk/cache state only
            status_result = await workflow.execute_activity(
                get_model_status,
                GetModelStatusParams(model_name=params.model_name),
                start_to_close_timeout=timedelta(seconds=30),
                activity_id=f"activity-get_model_status-{params.model_name}-{wf_hex}",
                retry_policy=activity_retry_policy,
            )
            workflow.logger.info(
                f"Model status: exists_on_disk={status_result['exists_on_disk']}, "
                f"cached_in_memory={status_result['cached_in_memory']}"
            )
            workflow_activities.append({"activity": "get_model_status", "result": status_result})

        elif action in ("build", "rebuild"):
            overwrite = action == "rebuild"

            build_result = await workflow.execute_activity(
                build_owner_model,
                BuildOwnerModelParams(
                    model_name=params.model_name,
                    player_feature_dim=params.player_feature_dim,
                    owner_profile_dim=params.owner_profile_dim,
                    draft_context_dim=params.draft_context_dim,
                    personality_dim=params.personality_dim,
                    overwrite=overwrite,
                ),
                start_to_close_timeout=timedelta(seconds=120),
                activity_id=f"activity-build_owner_model-{params.model_name}-{wf_hex}",
                retry_policy=activity_retry_policy,
            )
            created = build_result.get("created", False)
            model_type = build_result.get("model_type", "?")
            workflow.logger.info(
                f"Model '{params.model_name}': created={created}, "
                f"model_type={model_type}"
            )
            workflow_activities.append({"activity": "build_owner_model", "result": build_result})

        elif action == "list":
            # List all models on disk
            list_result = await workflow.execute_activity(
                list_models,
                start_to_close_timeout=timedelta(seconds=30),
                activity_id=f"activity-list_models-{wf_hex}",
                retry_policy=activity_retry_policy,
            )
            workflow.logger.info(f"Listed {list_result['num_models']} models on disk")
            workflow_activities.append({"activity": "list_models", "result": list_result})

        elif action == "delete":
            # Delete model from disk and cache
            delete_result = await workflow.execute_activity(
                delete_model,
                DeleteModelParams(model_name=params.model_name),
                start_to_close_timeout=timedelta(seconds=30),
                activity_id=f"activity-delete_model-{params.model_name}-{wf_hex}",
                retry_policy=activity_retry_policy,
            )
            workflow.logger.info(
                f"Model '{params.model_name}': deleted_from_disk="
                f"{delete_result['deleted_from_disk']}, "
                f"evicted_from_cache={delete_result['evicted_from_cache']}"
            )
            workflow_activities.append({"activity": "delete_model", "result": delete_result})

        else:
            raise ValueError(
                f"Unknown action '{params.action}'. "
                "Valid actions: 'build', 'rebuild', 'status', 'list', 'delete'."
            )

        workflow.logger.info(f"ModelManagementWorkflow complete — action={params.action}")
        return {"activity_data": workflow_activities}
