"""Model prediction workflow for team owner draft pick inference."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.ml.predictions.predict_player_pick import (
        BatchPredictOwnerParams,
        GetPlayerFeaturesParams,
        PredictOwnerDraftPickParams,
        batch_predict_owner,
        get_player_features_from_db,
        predict_owner_draft_pick,
    )


@dataclass
class ModelPredictionWorkflowParams:
    """
    Input parameters for ModelPredictionWorkflow.

    Fields:
        model_name: Trained model identifier to use for scoring.
        user_id: Sleeper user_id of the team owner making the pick.
        player_ids: Candidate player IDs to score.
        draft_context: Current draft state (roster composition, pick number, needs).
        owner_profile: Owner's historical pick tendencies (26-dim profile dict).
        adp_data: Optional ADP data to enrich player features.
        personality_influence_scale: Personality weight 0.0–1.0. None randomizes per pick.
        batch_mode: If True, use batch scoring activity (default False).
    """

    model_name: str
    user_id: str
    player_ids: List[str]
    draft_context: Dict[str, Any]
    owner_profile: Dict[str, Any]
    adp_data: Optional[Dict[str, Any]] = None
    personality_influence_scale: Optional[float] = None
    batch_mode: bool = False


@workflow.defn(name="model-prediction")
class ModelPredictionWorkflow:
    """
    Run draft pick prediction for a team owner using a trained model.

    Orchestrates two sequential activities:

    1. **get_player_features_from_db** — fetch and encode player feature vectors
       from PostgreSQL for the given candidate player IDs.

    2. **predict_owner_draft_pick** (or **batch_predict_owner**) — score all
       candidates using the owner's trained LightGBM model and return ranked
       predictions with pick probabilities.
    """

    @workflow.run
    async def run(self, params: ModelPredictionWorkflowParams) -> Dict[str, Any]:
        """
        Execute the prediction workflow.

        Args:
            params: ModelPredictionWorkflowParams with model, owner, and candidate info.

        Returns:
            Dict[str, Any]: {
                "predictions": {...},
                "model_name": str,
                "num_candidates": int,
                "activity_data": [...],
            }
        """
        wf_hex = workflow.info().run_id[-4:]
        print(
            f"ModelPredictionWorkflow starting — model={params.model_name} "
            f"user={params.user_id} candidates={len(params.player_ids)}"
        )

        activity_retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=2),
            maximum_interval=timedelta(seconds=30),
            backoff_coefficient=2.0,
        )
        workflow_activities = []

        # ------------------------------------------------------------------
        # Step 1: Fetch player features from PostgreSQL
        # ------------------------------------------------------------------
        features_result = await workflow.execute_activity(
            get_player_features_from_db,
            GetPlayerFeaturesParams(
                player_ids=params.player_ids,
                adp_data=params.adp_data,
            ),
            start_to_close_timeout=timedelta(seconds=60),
            activity_id=f"activity-get_player_features-{wf_hex}",
            retry_policy=activity_retry_policy,
        )
        print(
            f"Fetched features for {features_result['num_players']} players "
            f"(missing={features_result['missing_players']})"
        )
        workflow_activities.append({
            "activity": "get_player_features_from_db",
            "result": {
                "num_players": features_result["num_players"],
                "missing_players": features_result["missing_players"],
            },
        })

        player_features = features_result["player_features"]
        if not player_features:
            print("No player features found — cannot predict.")
            return {
                "predictions": {},
                "model_name": params.model_name,
                "num_candidates": 0,
                "skipped": True,
                "reason": "no_player_features",
                "activity_data": workflow_activities,
            }

        # ------------------------------------------------------------------
        # Step 2: Run prediction
        # ------------------------------------------------------------------
        if params.batch_mode:
            prediction_result = await workflow.execute_activity(
                batch_predict_owner,
                BatchPredictOwnerParams(
                    player_features=player_features,
                    draft_context=params.draft_context,
                    owner_profile=params.owner_profile,
                    user_id=params.user_id,
                    model_name=params.model_name,
                    personality_influence_scale=params.personality_influence_scale,
                ),
                start_to_close_timeout=timedelta(seconds=120),
                activity_id=f"activity-batch_predict_owner-{params.model_name}-{wf_hex}",
                retry_policy=activity_retry_policy,
            )
        else:
            prediction_result = await workflow.execute_activity(
                predict_owner_draft_pick,
                PredictOwnerDraftPickParams(
                    player_features=player_features,
                    draft_context=params.draft_context,
                    owner_profile=params.owner_profile,
                    user_id=params.user_id,
                    model_name=params.model_name,
                    personality_influence_scale=params.personality_influence_scale,
                ),
                start_to_close_timeout=timedelta(seconds=120),
                activity_id=f"activity-predict_owner_draft_pick-{params.model_name}-{wf_hex}",
                retry_policy=activity_retry_policy,
            )

        print(
            f"Prediction complete: model={params.model_name} "
            f"candidates={prediction_result['num_candidates']}"
        )
        workflow_activities.append({
            "activity": "predict_owner_draft_pick",
            "result": {
                "num_candidates": prediction_result["num_candidates"],
                "model_name": prediction_result["model_name"],
                "personality_influence_used": prediction_result["personality_influence_used"],
            },
        })

        print(f"ModelPredictionWorkflow complete — model={params.model_name}")
        return {
            "predictions": prediction_result["predictions"],
            "top_3_predictions": prediction_result.get("top_3_predictions", []),
            "model_name": params.model_name,
            "num_candidates": prediction_result["num_candidates"],
            "personality_influence_used": prediction_result["personality_influence_used"],
            "activity_data": workflow_activities,
        }
