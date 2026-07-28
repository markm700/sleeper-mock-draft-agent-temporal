"""
Team-owner-centric draft prediction model using LightGBM.

Each model instance is trained to represent a specific fantasy football team owner
and predict which player that owner will draft during mock draft simulations.

The model uses a learning-to-rank approach: candidate players are each described by
a feature vector combining player stats, owner historical profile, draft context,
and personality traits. LightGBM scores each candidate independently and the caller
applies softmax over the raw scores to obtain pick probabilities.
"""

import random
from typing import Any, Dict, List, Optional

import lightgbm as lgb
import numpy as np

from activities.ml.models.registry import register_model

# Owner profile feature names — derived from historical draft data.
OWNER_PROFILE_FEATURES: List[str] = [
    "early_qb_rate", "early_rb_rate", "early_wr_rate",
    "early_te_rate", "early_k_rate", "early_def_rate",
    "mid_qb_rate", "mid_rb_rate", "mid_wr_rate",
    "mid_te_rate", "mid_k_rate", "mid_def_rate",
    "late_qb_rate", "late_rb_rate", "late_wr_rate",
    "late_te_rate", "late_k_rate", "late_def_rate",
    "adp_deviation", "sleeper_pick_rate", "handcuff_rate",
    "qb_early_tendency", "te_premium_tendency",
    "rb_heavy_early", "wr_heavy_early", "pick_consistency",
]
OWNER_PROFILE_DIM: int = len(OWNER_PROFILE_FEATURES)

PLAYER_FEATURE_DIM: int = 11
DRAFT_CONTEXT_DIM: int = 8
NUM_POSITIONS: int = 6  # QB, RB, WR, TE, K, DEF


@register_model("TeamOwnerDraftModel")
class TeamOwnerDraftModel:
    """
    Owner-centric draft prediction model backed by LightGBM.

    Each candidate player is represented by a concatenated feature vector:
        [player_features | owner_profile | draft_context | personality_traits]

    The model outputs a raw score per candidate; softmax across candidates yields
    pick probabilities.
    """

    def __init__(
        self,
        player_feature_dim: int = PLAYER_FEATURE_DIM,
        owner_profile_dim: int = OWNER_PROFILE_DIM,
        draft_context_dim: int = DRAFT_CONTEXT_DIM,
        personality_dim: int = 8,
        lgb_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.player_feature_dim = player_feature_dim
        self.owner_profile_dim = owner_profile_dim
        self.draft_context_dim = draft_context_dim
        self.personality_dim = personality_dim
        self.input_dim = player_feature_dim + owner_profile_dim + draft_context_dim + personality_dim

        self.lgb_params: Dict[str, Any] = lgb_params or {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [1, 3],
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_data_in_leaf": 5,
            "verbose": -1,
        }

        self.booster: Optional[lgb.Booster] = None

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Score candidate players.

        Args:
            X: (n_candidates, input_dim) feature matrix.

        Returns:
            np.ndarray: (n_candidates,) raw scores. Apply softmax for probabilities.
        """
        if self.booster is None:
            raise RuntimeError("Model has not been trained or loaded yet")
        return self.booster.predict(X)

    def predict_with_personality(
        self,
        X_base: np.ndarray,
        personality_col_start: int,
        random_personality: bool = True
    ) -> tuple[np.ndarray, float]:
        """
        Predict with a static or randomly scaled personality influence.

        When scaling, the personality feature columns are scaled by a random factor in [0, 1],
        simulating per-pick variance in owner behaviour.

        Args:
            X_base: (n_candidates, input_dim) feature matrix with personality columns.
            personality_col_start: Column index where personality features begin.

        Returns:
            (scores, influence_used)
        """
        influence = 0.3 if not random_personality else random.random() # default behavior is to randomly scale personality influence
        X = X_base.copy()
        X[:, personality_col_start:] *= influence
        scores = self.predict(X)
        return scores, influence

    def get_config(self) -> Dict[str, Any]:
        """Return model configuration for serialisation / re-instantiation."""
        return {
            "model_type": "TeamOwnerDraftModel",
            "player_feature_dim": self.player_feature_dim,
            "owner_profile_dim": self.owner_profile_dim,
            "draft_context_dim": self.draft_context_dim,
            "personality_dim": self.personality_dim,
            "lgb_params": self.lgb_params,
            "trained": self.booster is not None,
        }
