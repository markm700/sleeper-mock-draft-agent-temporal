import random
import numpy as np
import torch
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.pytorch_client import get_pytorch_model_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import Player
    from schema.constants import get_personality_trait, get_random_personality_trait, get_personality_trait_vector


@dataclass
class GetPlayerFeaturesParams:
    """
    Parameters for fetching player features from PostgreSQL.

    Fields:
        player_ids: List of Sleeper player IDs to fetch.
        adp_data: Optional dict mapping player_id to ADP metrics from calculate_adp_from_picks.
    """
    player_ids: List[str]
    adp_data: Optional[Dict[str, Any]] = None  # Optional ADP data to merge


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
            # Fetch players from database
            query = select(Player).where(Player.player_id.in_(input.player_ids))
            players = session.execute(query).scalars().all()
            
            player_features = []
            
            for player in players:
                # Get ADP data if available
                adp_info = {}
                if input.adp_data:
                    adp_info = input.adp_data.get(player.player_id, {})
                
                # Build feature dictionary
                feature_dict = {
                    "player_id": player.player_id,
                    "full_name": player.full_name,
                    "position": player.position,
                    "age": player.age,
                    "years_exp": player.years_exp,
                    "status": player.status,
                    "team": player.team,
                    "injury_status": player.injury_status,
                    # ADP features
                    "adp": adp_info.get("adp", 999.0),
                    "adp_std": adp_info.get("std_dev", 0.0),
                    "times_drafted": adp_info.get("times_drafted", 0),
                    # Projected points would come from external source
                    "projected_points": 0.0,  # TODO: Integrate projection source
                    "position_rank": 999,      # TODO: Calculate from projections
                }
                
                player_features.append(feature_dict)
        
        print(f"Fetched features for {len(player_features)} players from PostgreSQL")
        
        return {
            "player_features": player_features,
            "num_players": len(player_features),
            "missing_players": len(input.player_ids) - len(player_features)
        }
        
    except Exception as e:
        print(f"Failed to fetch player features: {str(e)}")
        raise

# Team-owner-centric Prediction
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
    player_features: List[Dict[str, Any]]   # Available candidates from get_player_features_from_db
    draft_context: Dict[str, Any]           # Current draft state (roster, pick number, needs)
    owner_profile: Dict[str, Any]           # Owner's historical pick tendencies
    user_id: Optional[str] = None           # Sleeper user_id — if provided, traits are fetched from DB
                                            # (TeamOwner → User → random fallback via get_personality_traits)
    model_name: str = "team_owner_draft_v1"
    # Personality influence: None = randomize per pick (adds natural variance to the simulation)
    personality_influence_scale: Optional[float] = None

@activity.defn(name="predict_owner_draft_pick")
async def predict_owner_draft_pick(input: PredictOwnerDraftPickParams) -> Dict[str, Any]:
    """
    Predict the next draft pick from a specific team owner's perspective.

    Scores all candidate players using the owner's trained model, personality traits,
    and current draft context. Personality influence is randomized per pick when
    personality_influence_scale is None.

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
        model_manager = get_pytorch_model_manager()
        model = model_manager.load_model(input.model_name)
        device = model_manager.get_device()

        model = model.to(device)
        model.eval()

        n = len(input.player_features)
        if n == 0:
            raise ValueError("player_features must not be empty")

        # Resolve personality traits: DB lookup (TeamOwner → User → random) or use provided dict
        try:
            pg = get_postgres_client_manager()
            with pg.session_scope() as session:
                resolved_trait = get_personality_trait(session, input.user_id)
            print(f"Resolved personality traits for user '{input.user_id}' from DB")
        except Exception as e:
            print(f"Failed to resolve personality traits for user '{input.user_id}': {str(e)}")
            resolved_trait = get_random_personality_trait()

        # Build per-player tensors
        player_array = _prepare_player_features_only(input.player_features)     # (n, 9)
        context_array = _prepare_draft_context_features(input.draft_context)    # (8,)
        profile_array = _prepare_owner_profile_features(input.owner_profile)    # (26,)
        personality_array = _prepare_personality_features(resolved_trait)       # (9,) or (8,) depending on if personality trait in DB

        # Tile owner/context/personality across all candidates
        context_tiled = np.tile(context_array, (n, 1))      # (n, 8)
        profile_tiled = np.tile(profile_array, (n, 1))      # (n, 26)
        personality_tiled = np.tile(personality_array, (n, 1))  # (n, 8) or (n, 9)

        player_t = torch.tensor(player_array, dtype=torch.float32).to(device)
        profile_t = torch.tensor(profile_tiled, dtype=torch.float32).to(device)
        context_t = torch.tensor(context_tiled, dtype=torch.float32).to(device)
        personality_t = torch.tensor(personality_tiled, dtype=torch.float32).to(device)

        # Determine personality influence for this pick
        if input.personality_influence_scale is not None:
            influence = float(input.personality_influence_scale)

        print(f"Scoring {n} candidate players for owner model '{input.model_name}'")

        with torch.no_grad():
            if input.personality_influence_scale is None:
                # Randomize: use model's built-in random personality
                pick_scores, position_priority, influence = (
                    model.predict_with_random_personality(
                        player_t, profile_t, context_t, personality_t
                    )
                )
            else:
                pick_scores, position_priority = model(
                    player_t, profile_t, context_t, personality_t,
                    personality_influence_scale=influence,
                )

        # pick_scores: (n, 1) → apply softmax across candidates → pick probabilities
        pick_scores_np = pick_scores.squeeze(1).cpu().numpy()           # (n,)
        pick_probs_np = np.exp(pick_scores_np) / np.exp(pick_scores_np).sum()  # softmax
        position_priority_np = position_priority[0].cpu().numpy()       # (6,) — same for all

        results = _postprocess_owner_predictions(
            pick_probs_np, pick_scores_np, position_priority_np,
            input.player_features
        )

        print(
            f"Owner prediction: top={results['top_prediction']['player_id']} "
            f"p={results['top_prediction']['confidence']:.3f} "
            f"personality_influence={influence:.2f}"
        )

        return {
            "predictions": results,
            "model_name": input.model_name,
            "personality_influence_used": influence,
            "num_candidates": n,
        }

    except Exception as e:
        print(f"Owner draft pick prediction failed: {str(e)}")
        raise

# Private helper functions
def _prepare_player_features_only(player_features: List[Dict[str, Any]]) -> np.ndarray:
    """
    Build the 9-dimensional per-player feature vector for TeamOwnerDraftModel.

    Args:
        player_features: Player feature dicts from get_player_features_from_db.

    Returns:
        np.ndarray: Shape (n_players, 9) — position, status, age, exp, ADP, pts, rank, team, injury.
    """
    position_map = {"QB": 0, "RB": 1, "WR": 2, "TE": 3, "K": 4, "DEF": 5}
    status_map = {
        "Active": 1.0, "Inactive": 0.0, "Reserve": 0.5, "PUP": 0.3, "Suspended": 0.2
    }

    vectors = []
    for p in player_features:
        vectors.append([
            float(position_map.get(p.get("position", ""), -1)),
            status_map.get(p.get("status", "Active"), 0.5),
            p.get("age", 25) / 100.0,
            p.get("years_exp", 0) / 20.0,
            1.0 / (p.get("adp", 999) + 1),
            p.get("projected_points", 0.0) / 400.0,
            1.0 / (p.get("position_rank", 999) + 1),
            1.0 if p.get("team") else 0.0,
            1.0 if p.get("injury_status") else 0.0,
        ])
    return np.array(vectors, dtype=np.float32)

def _prepare_draft_context_features(draft_context: Dict[str, Any]) -> np.ndarray:
    """
    Build the 8-dimensional draft-context feature vector for TeamOwnerDraftModel.

    Args:
        draft_context: Dict with current draft state keys: roster_needs_score, draft_position,
            picks_remaining, round, qb_need, rb_slots_remaining, wr_slots_remaining, flex_need.

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
        np.ndarray: Shape (26,) — position pick rates per tier plus 8 behavioural tendencies.
    """
    g = owner_profile.get
    return np.array([
        g("early_qb_rate", 0.0),
        g("early_rb_rate", 0.0),
        g("early_wr_rate", 0.0),
        g("early_te_rate", 0.0),
        g("early_k_rate", 0.0),
        g("early_def_rate", 0.0),
        g("mid_qb_rate", 0.0),
        g("mid_rb_rate", 0.0),
        g("mid_wr_rate", 0.0),
        g("mid_te_rate", 0.0),
        g("mid_k_rate", 0.0),
        g("mid_def_rate", 0.0),
        g("late_qb_rate", 0.0),
        g("late_rb_rate", 0.0),
        g("late_wr_rate", 0.0),
        g("late_te_rate", 0.0),
        g("late_k_rate", 0.0),
        g("late_def_rate", 0.0),
        g("adp_deviation", 0.5),
        g("sleeper_pick_rate", 0.0),
        g("handcuff_rate", 0.0),
        g("qb_early_tendency", 0.0),
        g("te_premium_tendency", 0.0),
        g("rb_heavy_early", 0.0),
        g("wr_heavy_early", 0.0),
        g("pick_consistency", 0.5),
    ], dtype=np.float32)

def _prepare_personality_features(personality_trait: str) -> np.ndarray:
    """
    Build the personality trait feature vector from a single trait name.

    Sets the matched trait slot to 0.7 and all others to random values for variance.

    Args:
        personality_trait: Trait name resolved from DB or random fallback,
            e.g. "contrarian" or "upside_seeking".

    Returns:
        np.ndarray: Shape (8,) or (9,) depending on get_personality_trait_vector output.
    """
    return np.array(
        [get_personality_trait_vector(personality_trait)],
        dtype=np.float32,
    )

def _postprocess_owner_predictions(
    pick_probs: np.ndarray,
    pick_scores: np.ndarray,
    position_priority: np.ndarray,
    player_features: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Convert TeamOwnerDraftModel output to structured predictions.

    Args:
        pick_probs: (n,) softmax probabilities over candidates.
        pick_scores: (n,) raw affinity scores before softmax.
        position_priority: (6,) positional preference vector.
        player_features: Original player feature dicts for player_id lookup.

    Returns:
        Dict[str, Any]: {
            "top_prediction": {...},
            "all_predictions": [...],
            "position_priority": {...},
            "mean_confidence": float,
        }
    """
    positions = ["QB", "RB", "WR", "TE", "K", "DEF"]

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

    return {
        "top_prediction": all_predictions[0],
        "all_predictions": all_predictions,
        "position_priority": {
            pos: float(position_priority[idx]) for idx, pos in enumerate(positions)
        },
        "mean_confidence": float(np.mean(pick_probs)),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Batch owner-centric prediction (training validation / simulation)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BatchPredictOwnerParams:
    """
    Parameters for batch owner-centric draft pick scoring.

    Fields:
        player_features: All candidate players from get_player_features_from_db.
        draft_context: Current draft state (same schema as PredictOwnerDraftPickParams).
        owner_profile: Owner historical tendencies (same schema).
        user_id: Sleeper user_id for DB personality lookup.
        model_name: Model identifier to load for scoring.
        batch_size: Candidates per forward pass (default 64).
        personality_influence_scale: None randomizes once per activity call.
    """
    player_features: List[Dict[str, Any]]   # All candidate players from get_player_features_from_db
    draft_context: Dict[str, Any]           # Current draft state (same schema as PredictOwnerDraftPickParams)
    owner_profile: Dict[str, Any]           # Owner historical tendencies (same schema)
    user_id: Optional[str] = None           # Sleeper user_id for DB personality lookup
    model_name: str = "team_owner_draft_v1"
    batch_size: int = 64                    # Tune: 32-64 CPU, 64-128 GPU
    personality_influence_scale: Optional[float] = None  # None = randomize per batch


@activity.defn(name="batch_predict_owner")
async def batch_predict_owner(input: BatchPredictOwnerParams) -> Dict[str, Any]:
    """
    Score all candidate players for a team owner across configurable batch chunks.

    Processes large candidate sets in configurable chunks for memory efficiency.
    Used for training validation and full-draft simulation.

    Args:
        input: BatchPredictOwnerParams with player candidates, owner context, and batch config.

    Returns:
        Dict[str, Any]: {
            "predictions": [...],
            "position_priority": {...},
            "personality_influence_used": float,
            "model_name": str,
            "num_candidates": int,
            "num_batches": int,
        }
    """
    try:
        model_manager = get_pytorch_model_manager()
        model = model_manager.load_model(input.model_name)
        device = model_manager.get_device()

        model = model.to(device)
        model.eval()

        n = len(input.player_features)
        if n == 0:
            raise ValueError("player_features must not be empty")

        # Resolve personality trait once for the whole batch
        try:
            pg = get_postgres_client_manager()
            with pg.session_scope() as session:
                resolved_trait = get_personality_trait(session, input.user_id)
        except Exception as e:
            print(f"Failed to resolve personality trait for user '{input.user_id}': {str(e)}")
            resolved_trait = get_random_personality_trait()

        # Build fixed context/profile/personality arrays once, tile per chunk
        context_array = _prepare_draft_context_features(input.draft_context)     # (8,)
        profile_array = _prepare_owner_profile_features(input.owner_profile)     # (26,)
        personality_array = _prepare_personality_features(resolved_trait)        # (8,)

        # Determine personality influence — randomize once per activity call for consistency
        if input.personality_influence_scale is not None:
            influence = float(input.personality_influence_scale)
        else:
            influence = float(np.random.uniform(0.0, 1.0))

        all_scores_np: List[float] = []
        all_affinities_np: List[float] = []
        position_priority_np: Optional[np.ndarray] = None

        num_batches = (n + input.batch_size - 1) // input.batch_size
        print(f"batch_predict_owner: {n} candidates, {num_batches} batches, model='{input.model_name}'")

        with torch.no_grad():
            for start in range(0, n, input.batch_size):
                chunk_features = input.player_features[start:start + input.batch_size]
                chunk_n = len(chunk_features)

                player_array = _prepare_player_features_only(chunk_features)           # (chunk_n, 9)
                context_tiled = np.tile(context_array, (chunk_n, 1))                  # (chunk_n, 8)
                profile_tiled = np.tile(profile_array, (chunk_n, 1))                  # (chunk_n, 26)
                personality_tiled = np.tile(personality_array, (chunk_n, 1))          # (chunk_n, 8)

                player_t = torch.tensor(player_array, dtype=torch.float32).to(device)
                profile_t = torch.tensor(profile_tiled, dtype=torch.float32).to(device)
                context_t = torch.tensor(context_tiled, dtype=torch.float32).to(device)
                personality_t = torch.tensor(personality_tiled, dtype=torch.float32).to(device)

                pick_scores, position_priority, _ = model(
                    player_t, profile_t, context_t, personality_t,
                    personality_influence_scale=influence,
                )

                all_affinities_np.extend(pick_scores.squeeze(1).cpu().numpy().tolist())

                if position_priority_np is None:
                    position_priority_np = position_priority[0].cpu().numpy()  # (6,) — same for all

        # Apply softmax across all candidates globally
        affinities = np.array(all_affinities_np, dtype=np.float32)
        confidences = np.exp(affinities) / np.exp(affinities).sum()

        results = _postprocess_owner_predictions(
            confidences, affinities, position_priority_np, input.player_features
        )

        print(
            f"batch_predict_owner complete: top={results['top_prediction']['player_id']} "
            f"p={results['top_prediction']['confidence']:.3f}"
        )

        return {
            "predictions": results["all_predictions"],
            "position_priority": results["position_priority"],
            "personality_influence_used": influence,
            "model_name": input.model_name,
            "num_candidates": n,
            "num_batches": num_batches,
        }

    except Exception as e:
        print(f"batch_predict_owner failed: {str(e)}")
        raise