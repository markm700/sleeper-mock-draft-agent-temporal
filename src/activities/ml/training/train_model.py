"""
Activity to train a TeamOwnerDraftModel on historical draft pick data.

Accepts pre-encoded training samples from prepare_owner_training_data and
trains a LightGBM ranking model where the picked player (target_idx=0) is
the relevant document among MAX_NEGATIVES + 1 candidates per query group.
"""

import os
from pydantic.dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import lightgbm as lgb
import numpy as np
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.ml_client import get_ml_model_manager
    from activities.clients.langfuse_client import get_langfuse_client_manager
    from activities.ml.models.team_owner_model import (
        DRAFT_CONTEXT_DIM,
        OWNER_PROFILE_DIM,
        PLAYER_FEATURE_DIM,
        TeamOwnerDraftModel,
    )
    from schema.constants import get_personality_trait_vector, get_random_personality_trait


@dataclass(frozen=True, kw_only=True)
class TrainTeamOwnerModelParams:
    """
    Parameters for training a team owner draft prediction model.

    Args:
        model_name: Name/path key for the model (e.g. "owner_abc123_v1").
        training_samples: Encoded training samples from prepare_owner_training_data.
            Each sample contains "candidate_features", "context", and "target_idx".
        owner_profile: 26-dim owner profile float vector (OWNER_PROFILE_FEATURES).
        player_feature_dim: Per-player feature dimension (default 9).
        owner_profile_dim: Owner history profile dimension (default 26).
        draft_context_dim: Draft context dimension (default 8).
        personality_dim: Personality trait dimension (default 8).
        num_boost_round: Number of boosting rounds (default 100).
        learning_rate: LightGBM learning rate (default 0.05).
    """

    model_name: str
    training_samples: List[Dict[str, Any]]
    owner_profile: List[float]
    personality_trait: str = ""
    player_feature_dim: int = PLAYER_FEATURE_DIM
    owner_profile_dim: int = OWNER_PROFILE_DIM
    draft_context_dim: int = DRAFT_CONTEXT_DIM
    personality_dim: int = 8
    num_boost_round: int = 100
    learning_rate: float = 0.05

langfuse_client = get_langfuse_client_manager()

@activity.defn(name="train_team_owner_model")
@langfuse_client.traced_activity(name="training-train_team_owner_model")
async def train_team_owner_model(input: TrainTeamOwnerModelParams) -> Dict[str, Any]:
    """
    Train a TeamOwnerDraftModel (LightGBM) on historical draft picks.

    Constructs a learning-to-rank dataset where each query group is a single
    draft pick: the picked player has relevance 1 and the negatives have
    relevance 0. LightGBM's lambdarank objective optimises NDCG.

    Args:
        input: TrainTeamOwnerModelParams with model_name, training samples, and hyperparameters.

    Returns:
        Dict[str, Any]: {"model_name": str, "model_path": str, "num_boost_round": int,
            "num_samples": int, "num_query_groups": int}
    """
    ml_manager = get_ml_model_manager()
    base_path = os.getenv("MODEL_PATH", "/app/models")
    model_path = str(Path(base_path) / f"{input.model_name}.joblib")

    samples = [s for s in input.training_samples if s.get("candidate_features")]
    num_samples = len(samples)

    if num_samples == 0:
        print(f"No usable training samples for '{input.model_name}'; skipping training.")
        return {
            "model_name": input.model_name,
            "model_path": model_path,
            "num_boost_round": 0,
            "num_samples": 0,
            "num_query_groups": 0,
        }

    try:
        owner_profile = np.array(input.owner_profile, dtype=np.float32)

        trait = input.personality_trait or get_random_personality_trait()
        personality_vec = np.array(
            list(get_personality_trait_vector(trait).values()), dtype=np.float32
        )

        all_features: List[np.ndarray] = []
        all_labels: List[int] = []
        group_sizes: List[int] = []

        for sample in samples:
            candidate_features: List[List[float]] = sample["candidate_features"]
            context_vec: List[float] = sample["context"]
            target_idx: int = sample["target_idx"]
            n = len(candidate_features)

            if n == 0:
                continue

            player_array = np.array(candidate_features, dtype=np.float32)
            context_tiled = np.tile(
                np.array(context_vec, dtype=np.float32), (n, 1)
            )
            profile_tiled = np.tile(owner_profile, (n, 1))
            personality_tiled = np.tile(personality_vec, (n, 1))

            X_group = np.hstack([
                player_array, profile_tiled, context_tiled, personality_tiled
            ])
            all_features.append(X_group)

            labels = [0] * n
            labels[target_idx] = 1
            all_labels.extend(labels)
            group_sizes.append(n)

        X_train = np.vstack(all_features)
        y_train = np.array(all_labels, dtype=np.float32)

        print(
            f"Training LightGBM ranker for '{input.model_name}': "
            f"{X_train.shape[0]} rows, {len(group_sizes)} query groups"
        )

        train_data = lgb.Dataset(
            X_train,
            label=y_train,
            group=group_sizes,
        )

        params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [1, 3],
            "learning_rate": input.learning_rate,
            "num_leaves": 31,
            "min_data_in_leaf": max(1, min(5, num_samples // 3)),
            "verbose": -1,
        }

        booster = lgb.train(
            params,
            train_data,
            num_boost_round=input.num_boost_round,
        )

        # Wrap in TeamOwnerDraftModel and persist
        model = TeamOwnerDraftModel(
            player_feature_dim=input.player_feature_dim,
            owner_profile_dim=input.owner_profile_dim,
            draft_context_dim=input.draft_context_dim,
            personality_dim=input.personality_dim,
            lgb_params=params,
        )
        model.booster = booster

        saved_path = ml_manager.save_model(model, input.model_name, save_path=model_path)
        print(f"Saved trained model '{input.model_name}' → {saved_path}")

        return {
            "model_name": input.model_name,
            "model_path": saved_path,
            "num_boost_round": input.num_boost_round,
            "num_samples": num_samples,
            "num_query_groups": len(group_sizes),
        }

    except Exception as e:
        print(f"Failed to train model '{input.model_name}': {str(e)}")
        raise
