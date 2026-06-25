"""
Activities for team-owner-centric draft pick prediction.

Scores candidate players using a trained TeamOwnerDraftModel (LightGBM) and
returns ranked predictions with pick probabilities.
"""

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy import select
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.ml_client import get_ml_model_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import Player
    from schema.constants import (
        get_personality_trait,
        get_random_personality_trait,
        get_personality_trait_vector,
    )


@dataclass
class GetPlayerFeaturesParams:
    """
    Parameters for fetching player features from PostgreSQL.

    Fields:
        player_ids: List of Sleeper player IDs to fetch.
        adp_data: Optional dict mapping player_id to ADP metrics from calculate_adp_from_picks.
    """

    player_ids: List[str]
    adp_data: Optional[Dict[str, Any]] = None


@activity.defn(name="get_player_features_from_db")
async def get_player_features_from_db(input: GetPlayerFeaturesParams) -> Dict[str, Any]:
    """
    Fetch player features from PostgreSQL and optionally enrich with ADP data.

    Args:
        input: GetPlayerFeaturesParams with player_ids and optional adp_data.

    Returns:
        Dict[str, Any]: {"player_features": [...], "num_players": int, "missing_players": int}
    """
    try:
        postgres = get_postgres_client_manager()

        with postgres.get_session() as session:
            query = select(Player).where(Player.player_id.in_(input.player_ids))
            players = session.execute(query).scalars().all()

            player_features = []
            for player in players:
                adp_info = {}
                if input.adp_data:
                    adp_info = input.adp_data.get(player.player_id, {})

                feature_dict = {
                    "player_id": player.player_id,
                    "full_name": player.full_name,
                    "position": player.position,
                    "age": player.age,
                    "years_exp": player.years_exp,
                    "status": player.status,
                    "team": player.team,
                    "injury_status": player.injury_status,
                    "adp": adp_info.get("adp", 999.0),
                    "adp_std": adp_info.get("std_dev", 0.0),
                    "times_drafted": adp_info.get("times_drafted", 0),
                    "projected_points": 0.0,
                    "position_rank": 999,
                }
                player_features.append(feature_dict)

        print(f"Fetched features for {len(player_features)} players from PostgreSQL")
        return {
            "player_features": player_features,
            "num_players": len(player_features),
            "missing_players": len(input.player_ids) - len(player_features),
        }

    except Exception as e:
        print(f"Failed to fetch player features: {str(e)}")
        raise


# ──────────────────────────────────────────────────────────────────────────────
# Team-owner-centric prediction
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class PredictOwnerDraftPickParams:
    """
    Parameters for team-owner-centric draft pick prediction.

    Fields:
        player_features: Available candidate players from get_player_features_from_db.
        draft_context: Current draft state (roster composition, pick number, needs).
        owner_profile: Owner's historical pick tendencies (26-dim profile dict).
        user_id: Sleeper user_id for DB personality lookup. None uses random fallback.
        model_name: Model identifier to load for scoring.
        personality_influence_scale: Personality weight 0.0–1.0. None randomizes per pick.
    """

    player_features: List[Dict[str, Any]]
    draft_context: Dict[str, Any]
    owner_profile: Dict[str, Any]
    user_id: Optional[str] = None
    model_name: str = "team_owner_draft_v1"
    personality_influence_scale: Optional[float] = None


@activity.defn(name="predict_owner_draft_pick")
async def predict_owner_draft_pick(input: PredictOwnerDraftPickParams) -> Dict[str, Any]:
    """
    Predict the next draft pick from a specific team owner's perspective.

    Scores all candidate players using the owner's trained LightGBM model,
    personality traits, and current draft context.

    Args:
        input: PredictOwnerDraftPickParams with player candidates, owner context, and model.

    Returns:
        Dict[str, Any]: {
            "predictions": {...},
            "model_name": str,
            "personality_influence_used": float,
            "num_candidates": int,
        }
    """
    try:
        model_manager = get_ml_model_manager()
        model = model_manager.load_model(input.model_name)

        n = len(input.player_features)
        if n == 0:
            raise ValueError("player_features must not be empty")

        # Resolve personality traits
        try:
            pg = get_postgres_client_manager()
            with pg.session_scope() as session:
                resolved_trait = get_personality_trait(session, input.user_id)
            print(f"Resolved personality traits for user '{input.user_id}' from DB")
        except Exception as e:
            print(f"Failed to resolve personality traits for user '{input.user_id}': {str(e)}")
            resolved_trait = get_random_personality_trait()

        # Build feature matrix
        player_array = _prepare_player_features_only(input.player_features)
        context_array = _prepare_draft_context_features(input.draft_context)
        profile_array = _prepare_owner_profile_features(input.owner_profile)
        personality_array = _prepare_personality_features(resolved_trait)

        context_tiled = np.tile(context_array, (n, 1))
        profile_tiled = np.tile(profile_array, (n, 1))
        personality_tiled = np.tile(personality_array, (n, 1))

        X = np.hstack([player_array, profile_tiled, context_tiled, personality_tiled])

        # Determine personality influence
        personality_col_start = (
            model.player_feature_dim + model.owner_profile_dim + model.draft_context_dim
        )
        if input.personality_influence_scale is not None:
            influence = float(input.personality_influence_scale)
            X_scored = X.copy()
            X_scored[:, personality_col_start:] *= influence
            pick_scores_np = model.predict(X_scored)
        else:
            pick_scores_np, influence = model.predict_with_random_personality(
                X, personality_col_start
            )

        print(f"Scoring {n} candidate players for owner model '{input.model_name}'")

        # Softmax across candidates
        exp_scores = np.exp(pick_scores_np - np.max(pick_scores_np))
        pick_probs_np = exp_scores / exp_scores.sum()

        results = _postprocess_owner_predictions(
            pick_probs_np, pick_scores_np, input.player_features
        )

        print(
            f"Owner prediction: top={results['top_prediction']['player_id']} "
            f"p={results['top_prediction']['confidence']:.3f} "
            f"personality_influence={influence:.2f}"
        )

        return {
            "predictions": results,
            "top_3_predictions": results["top_3_predictions"],
            "model_name": input.model_name,
            "personality_influence_used": influence,
            "num_candidates": n,
        }

    except Exception as e:
        print(f"Owner draft pick prediction failed: {str(e)}")
        raise


# ──────────────────────────────────────────────────────────────────────────────
# Batch owner-centric prediction
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class BatchPredictOwnerParams:
    """
    Parameters for batch owner-centric draft pick scoring.

    Fields:
        player_features: All candidate players from get_player_features_from_db.
        draft_context: Current draft state.
        owner_profile: Owner historical tendencies.
        user_id: Sleeper user_id for DB personality lookup.
        model_name: Model identifier to load for scoring.
        personality_influence_scale: None randomizes once per activity call.
    """

    player_features: List[Dict[str, Any]]
    draft_context: Dict[str, Any]
    owner_profile: Dict[str, Any]
    user_id: Optional[str] = None
    model_name: str = "team_owner_draft_v1"
    personality_influence_scale: Optional[float] = None


@activity.defn(name="batch_predict_owner")
async def batch_predict_owner(input: BatchPredictOwnerParams) -> Dict[str, Any]:
    """
    Score all candidate players for a team owner in a single pass.

    Args:
        input: BatchPredictOwnerParams with player candidates, owner context, and model.

    Returns:
        Dict[str, Any]: {
            "predictions": [...],
            "personality_influence_used": float,
            "model_name": str,
            "num_candidates": int,
        }
    """
    try:
        model_manager = get_ml_model_manager()
        model = model_manager.load_model(input.model_name)

        n = len(input.player_features)
        if n == 0:
            raise ValueError("player_features must not be empty")

        # Resolve personality trait once
        try:
            pg = get_postgres_client_manager()
            with pg.session_scope() as session:
                resolved_trait = get_personality_trait(session, input.user_id)
        except Exception as e:
            print(f"Failed to resolve personality trait for user '{input.user_id}': {str(e)}")
            resolved_trait = get_random_personality_trait()

        context_array = _prepare_draft_context_features(input.draft_context)
        profile_array = _prepare_owner_profile_features(input.owner_profile)
        personality_array = _prepare_personality_features(resolved_trait)
        player_array = _prepare_player_features_only(input.player_features)

        context_tiled = np.tile(context_array, (n, 1))
        profile_tiled = np.tile(profile_array, (n, 1))
        personality_tiled = np.tile(personality_array, (n, 1))

        X = np.hstack([player_array, profile_tiled, context_tiled, personality_tiled])

        personality_col_start = (
            model.player_feature_dim + model.owner_profile_dim + model.draft_context_dim
        )
        if input.personality_influence_scale is not None:
            influence = float(input.personality_influence_scale)
            X_scored = X.copy()
            X_scored[:, personality_col_start:] *= influence
            affinities = model.predict(X_scored)
        else:
            influence = float(np.random.uniform(0.0, 1.0))
            X_scored = X.copy()
            X_scored[:, personality_col_start:] *= influence
            affinities = model.predict(X_scored)

        exp_scores = np.exp(affinities - np.max(affinities))
        confidences = exp_scores / exp_scores.sum()

        results = _postprocess_owner_predictions(
            confidences, affinities, input.player_features
        )

        print(
            f"batch_predict_owner complete: top={results['top_prediction']['player_id']} "
            f"p={results['top_prediction']['confidence']:.3f}"
        )

        return {
            "predictions": results["all_predictions"],
            "top_3_predictions": results["top_3_predictions"],
            "personality_influence_used": influence,
            "model_name": input.model_name,
            "num_candidates": n,
        }

    except Exception as e:
        print(f"batch_predict_owner failed: {str(e)}")
        raise


# ──────────────────────────────────────────────────────────────────────────────
# Private helper functions
# ──────────────────────────────────────────────────────────────────────────────


def _prepare_player_features_only(player_features: List[Dict[str, Any]]) -> np.ndarray:
    """
    Build the 11-dimensional per-player feature vector.

    Args:
        player_features: Player feature dicts from get_player_features_from_db.

    Returns:
        np.ndarray: Shape (n_players, 11).
    """
    position_map = {"QB": 0, "RB": 1, "WR": 2, "TE": 3, "K": 4, "DEF": 5}
    status_map = {
        "Active": 1.0, "Inactive": 0.0, "Reserve": 0.5, "PUP": 0.3, "Suspended": 0.2,
    }

    vectors = []
    for p in player_features:
        vectors.append([
            float(position_map.get(p.get("position") or "", -1)),
            status_map.get(p.get("status") or "Active", 0.5),
            (p.get("age") or 25) / 100.0,
            (p.get("years_exp") or 0) / 20.0,
            1.0 / ((p.get("adp") or 999) + 1),                     # lower ADP = higher value
            1.0 / ((p.get("adp_std") or 999) + 1),                 # tight consensus = higher value
            min((p.get("times_drafted") or 0) / 100.0, 1.0),       # draft popularity, capped at 100
            (p.get("projected_points") or 0.0) / 400.0,
            1.0 / ((p.get("position_rank") or 999) + 1),
            1.0 if p.get("team") else 0.0,
            1.0 if p.get("injury_status") else 0.0,
        ])
    return np.array(vectors, dtype=np.float32)


def _prepare_draft_context_features(draft_context: Dict[str, Any]) -> np.ndarray:
    """
    Build the 8-dimensional draft-context feature vector.

    Args:
        draft_context: Dict with current draft state keys.

    Returns:
        np.ndarray: Shape (8,).
    """
    return np.array([
        draft_context.get("roster_needs_score", 0.5),
        draft_context.get("draft_position", 1) / 200.0,
        draft_context.get("picks_remaining", 100) / 200.0,
        draft_context.get("round", 1) / 18.0,
        float(draft_context.get("qb_need", 0)),
        draft_context.get("rb_slots_remaining", 2) / 4.0,
        draft_context.get("wr_slots_remaining", 3) / 5.0,
        draft_context.get("flex_need", 0.5),
    ], dtype=np.float32)


def _prepare_owner_profile_features(owner_profile: Dict[str, Any]) -> np.ndarray:
    """
    Build the 26-dimensional owner historical profile feature vector.

    Args:
        owner_profile: Dict with historical tendencies. Missing keys default to 0.0.

    Returns:
        np.ndarray: Shape (26,).
    """
    g = owner_profile.get
    return np.array([
        g("early_qb_rate", 0.0), g("early_rb_rate", 0.0), g("early_wr_rate", 0.0),
        g("early_te_rate", 0.0), g("early_k_rate", 0.0), g("early_def_rate", 0.0),
        g("mid_qb_rate", 0.0), g("mid_rb_rate", 0.0), g("mid_wr_rate", 0.0),
        g("mid_te_rate", 0.0), g("mid_k_rate", 0.0), g("mid_def_rate", 0.0),
        g("late_qb_rate", 0.0), g("late_rb_rate", 0.0), g("late_wr_rate", 0.0),
        g("late_te_rate", 0.0), g("late_k_rate", 0.0), g("late_def_rate", 0.0),
        g("adp_deviation", 0.5), g("sleeper_pick_rate", 0.0), g("handcuff_rate", 0.0),
        g("qb_early_tendency", 0.0), g("te_premium_tendency", 0.0),
        g("rb_heavy_early", 0.0), g("wr_heavy_early", 0.0), g("pick_consistency", 0.5),
    ], dtype=np.float32)


def _prepare_personality_features(personality_trait: str) -> np.ndarray:
    """
    Build the personality trait feature vector from a single trait name.

    Args:
        personality_trait: Trait name resolved from DB or random fallback.

    Returns:
        np.ndarray: Shape (1, personality_dim).
    """
    vec = get_personality_trait_vector(personality_trait)
    return np.array([list(vec.values())], dtype=np.float32)


def _postprocess_owner_predictions(
    pick_probs: np.ndarray,
    pick_scores: np.ndarray,
    player_features: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Convert model output to structured predictions.

    Args:
        pick_probs: (n,) softmax probabilities over candidates.
        pick_scores: (n,) raw affinity scores before softmax.
        player_features: Original player feature dicts for player_id lookup.

    Returns:
        Dict[str, Any]: {
            "top_prediction": {...},
            "all_predictions": [...],
            "mean_confidence": float,
        }
    """
    ranked_indices = np.argsort(pick_probs)[::-1]
    all_predictions = [
        {
            "player_id": player_features[i]["player_id"],
            "confidence": float(pick_probs[i]),
            "affinity_score": float(pick_scores[i]),
            "rank": rank + 1,
        }
        for rank, i in enumerate(ranked_indices)
    ]

    top_3 = all_predictions[:3]

    return {
        "top_prediction": all_predictions[0],
        "top_3_predictions": top_3,
        "all_predictions": all_predictions,
        "mean_confidence": float(np.mean(pick_probs)),
    }
