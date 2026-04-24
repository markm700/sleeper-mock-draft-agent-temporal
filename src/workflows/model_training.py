"""Model training workflow for team owner draft prediction models."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.ml.calculate_adp import CalculateADPFromPicksParams, calculate_adp_from_picks
    from activities.ml.models.manage_model import BuildOwnerModelParams, build_owner_model
    from activities.ml.models.team_owner_model import (
        DRAFT_CONTEXT_DIM,
        OWNER_PROFILE_DIM,
        PLAYER_FEATURE_DIM,
    )
    from activities.ml.training.prepare_training_data import (
        PrepareOwnerTrainingDataParams,
        prepare_owner_training_data,
    )
    from activities.ml.training.train_model import (
        TrainTeamOwnerModelParams,
        train_team_owner_model,
    )


@dataclass
class ModelTrainingWorkflowParams:
    """
    Input parameters for ModelTrainingWorkflow.

    Fields:
        league_id: Sleeper league_id used as the scope for ADP and draft pick data.
        user_id: Sleeper user_id of the team owner whose model is being trained.
        model_name: Unique model identifier. If empty, defaults to "owner_{user_id}_{league_id}_v1".
        season: Season year filter for draft picks, e.g. "2025". None includes all seasons.
        player_feature_dim: Per-player feature dimension (default 9).
        owner_profile_dim: Owner historical profile dimension (default 26).
        draft_context_dim: Draft-state context dimension (default 8).
        personality_dim: Personality trait vector dimension (default 8).
        num_boost_round: Number of LightGBM boosting rounds (default 100).
        learning_rate: LightGBM learning rate (default 0.05).
        weighted_adp: Use recency-weighted ADP in feature construction (default True).
        min_picks_required: Minimum historical picks required to attempt training (default 10).
        rebuild_model: If True, force-rebuild the model from scratch (default False).
    """

    league_id: str
    user_id: str
    model_name: str = ""
    season: Optional[str] = None
    player_feature_dim: int = PLAYER_FEATURE_DIM
    owner_profile_dim: int = OWNER_PROFILE_DIM
    draft_context_dim: int = DRAFT_CONTEXT_DIM
    personality_dim: int = 8
    num_boost_round: int = 100
    learning_rate: float = 0.05
    weighted_adp: bool = True
    min_picks_required: int = 10
    rebuild_model: bool = False


def _default_model_name(user_id: str, league_id: str) -> str:
    """
    Build a deterministic default model name from user and league IDs.

    Args:
        user_id: Sleeper user identifier.
        league_id: Sleeper league identifier.

    Returns:
        str: e.g. "owner_abc123_xyz456_v1".
    """
    return f"owner_{user_id}_{league_id}_v1"


@workflow.defn(name="model-training")
class ModelTrainingWorkflow:
    """
    Train a TeamOwnerDraftModel for a specific team owner in a given league.

    Orchestrates four sequential activities:

    1. **calculate_adp_from_picks** — compute per-player ADP from stored
       DraftPick records in the given league (scoped to season when provided).
       ADP is used as a feature when encoding historical picks for both the
       owner profile and the training sample tensors.

    2. **prepare_owner_training_data** — fetch DraftPick, Draft, Player, and
       TeamOwner rows from PostgreSQL, reconstruct the draft context at each
       of the owner's historical picks, encode player features, and compute the
       26-dim owner profile vector. Returns a compact list of encoded training
       samples ready for LightGBM ranking training.

    3. **build_owner_model** — build (or verify) the target TeamOwnerDraftModel
       on disk. Skips re-creation unless rebuild_model=True. This ensures the
       model architecture exists before the training loop begins.

    4. **train_team_owner_model** — load the model, run a listwise cross-entropy
       training loop over the prepared samples, and save the updated checkpoint.

    The workflow exits early (with appropriate logging) if the owner has fewer
    than min_picks_required historical picks.
    """

    @workflow.run
    async def run(self, params: ModelTrainingWorkflowParams) -> Dict[str, Any]:
        """
        Execute the model training workflow.

        Runs four sequential activities: ADP calculation, training data preparation,
        model build/verification, and the training loop. Exits early with skipped=True
        if the owner has fewer than min_picks_required historical picks.

        Args:
            params: ModelTrainingWorkflowParams with owner and training configuration.

        Returns:
            Dict[str, Any]: {
                "model_name": str,
                "model_path": str,
                "skipped": bool,
                "epochs_trained": int,
                "initial_loss": float,
                "final_loss": float,
                "num_samples": int,
                "activity_data": [...],
            }
        """
        wf_hex = workflow.info().run_id[-4:]
        model_name = params.model_name or _default_model_name(
            params.user_id, params.league_id
        )
        print(
            f"ModelTrainingWorkflow starting — user={params.user_id} "
            f"league={params.league_id} model={model_name} season={params.season}"
        )

        activity_retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=5),
            maximum_interval=timedelta(minutes=2),
            backoff_coefficient=2.0,
        )
        workflow_activities = []

        # ------------------------------------------------------------------
        # Step 1: Calculate ADP from stored draft picks
        # ------------------------------------------------------------------
        adp_result = await workflow.execute_activity(
            calculate_adp_from_picks,
            CalculateADPFromPicksParams(
                league_id=params.league_id,
                season=params.season,
                weighted=params.weighted_adp,
            ),
            start_to_close_timeout=timedelta(seconds=60),
            activity_id=(
                f"activity-calculate_adp-{params.league_id}"
                f"-{params.season or 'all'}-{wf_hex}"
            ),
            retry_policy=activity_retry_policy,
        )
        print(
            f"ADP calculated: {adp_result['num_players']} players across "
            f"{adp_result['num_drafts']} drafts ({adp_result['num_picks']} picks)"
        )
        workflow_activities.append({"activity": "calculate_adp_from_picks", "result": {
            "num_players": adp_result["num_players"],
            "num_picks": adp_result["num_picks"],
            "num_drafts": adp_result["num_drafts"],
        }})

        # ------------------------------------------------------------------
        # Step 2: Prepare encoded training samples for this owner
        # ------------------------------------------------------------------
        training_data = await workflow.execute_activity(
            prepare_owner_training_data,
            PrepareOwnerTrainingDataParams(
                league_id=params.league_id,
                user_id=params.user_id,
                season=params.season,
                adp_data=adp_result["adp_data"],
                min_picks_required=params.min_picks_required,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            activity_id=(
                f"activity-prepare_training_data-{params.user_id}"
                f"-{params.league_id}-{wf_hex}"
            ),
            retry_policy=activity_retry_policy,
        )

        num_samples = training_data["num_samples"]
        print(
            f"Training data prepared: {num_samples} samples "
            f"for user {params.user_id}"
        )
        workflow_activities.append({"activity": "prepare_owner_training_data", "result": {
            "num_samples": num_samples,
        }})

        if num_samples == 0:
            print(
                f"Skipping training — no usable samples for user {params.user_id}. "
                "Ensure draft data has been collected first."
            )
            return {
                "model_name": model_name,
                "skipped": True,
                "reason": "insufficient_training_samples",
                "activity_data": workflow_activities,
            }

        # ------------------------------------------------------------------
        # Step 3: Build or verify the model on disk
        # ------------------------------------------------------------------
        build_result = await workflow.execute_activity(
            build_owner_model,
            BuildOwnerModelParams(
                model_name=model_name,
                player_feature_dim=params.player_feature_dim,
                owner_profile_dim=params.owner_profile_dim,
                draft_context_dim=params.draft_context_dim,
                personality_dim=params.personality_dim,
                overwrite=params.rebuild_model,
            ),
            start_to_close_timeout=timedelta(seconds=120),
            activity_id=(
                f"activity-build_owner_model-{model_name}-{wf_hex}"
            ),
            retry_policy=activity_retry_policy,
        )
        print(
            f"Model '{model_name}': created={build_result.get('created')}, "
            f"model_type={build_result.get('model_type')}"
        )
        workflow_activities.append({"activity": "build_owner_model", "result": {
            "model_name": model_name,
            "created": build_result.get("created"),
            "model_type": build_result.get("model_type"),
        }})

        # ------------------------------------------------------------------
        # Step 4: Train the model
        # ------------------------------------------------------------------
        train_result = await workflow.execute_activity(
            train_team_owner_model,
            TrainTeamOwnerModelParams(
                model_name=model_name,
                training_samples=training_data["training_samples"],
                owner_profile=training_data["owner_profile"],
                player_feature_dim=params.player_feature_dim,
                owner_profile_dim=params.owner_profile_dim,
                draft_context_dim=params.draft_context_dim,
                personality_dim=params.personality_dim,
                num_boost_round=params.num_boost_round,
                learning_rate=params.learning_rate,
            ),
            start_to_close_timeout=timedelta(minutes=30),
            activity_id=(
                f"activity-train_team_owner_model-{model_name}-{wf_hex}"
            ),
            retry_policy=activity_retry_policy,
        )
        print(
            f"Training complete: {train_result['num_boost_round']} rounds, "
            f"samples={train_result['num_samples']}, "
            f"query_groups={train_result['num_query_groups']}"
        )
        workflow_activities.append({"activity": "train_team_owner_model", "result": train_result})

        print(f"ModelTrainingWorkflow complete — model saved to {train_result['model_path']}")
        return {
            "model_name": model_name,
            "model_path": train_result["model_path"],
            "skipped": False,
            "num_boost_round": train_result["num_boost_round"],
            "num_samples": train_result["num_samples"],
            "num_query_groups": train_result["num_query_groups"],
            "activity_data": workflow_activities,
        }
