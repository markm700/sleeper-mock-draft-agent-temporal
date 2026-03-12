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
    """Parameters for fetching player features from PostgreSQL."""
    player_ids: List[str]
    adp_data: Optional[Dict[str, Any]] = None  # Optional ADP data to merge


@activity.defn(name="get_player_features_from_db")
async def get_player_features_from_db(input: GetPlayerFeaturesParams) -> Dict[str, Any]:
    """
    Fetch player features from PostgreSQL database for ML model inference.
    
    Retrieves comprehensive player data from Player table and optionally enriches with
    pre-calculated ADP metrics. Output is structured for conversion to feature vectors
    by predict_draft_pick activity.
    
    Data Sources:
    1. Player table (PostgreSQL):
       - Static attributes: position, age, years_exp, team
       - Dynamic status: status, injury_status
       - Identification: player_id, full_name
    
    2. ADP data (optional, from calculate_adp_from_picks):
       - adp: Average draft position
       - std_dev: Draft position volatility
       - times_drafted: Pick frequency
    
    Args:
        input: GetPlayerFeaturesParams containing:
            - player_ids: List of Sleeper player IDs to fetch (e.g., ["8150", "7553"])
            - adp_data: Optional dict mapping player_id to ADP metrics
                       If None, fills with default values (adp=999, std=0, times=0)
    
    Returns:
        Dict[str, Any] with structure:
        {
            "player_features": [
                {
                    "player_id": str,
                    "full_name": str,
                    "position": str,           # QB, RB, WR, TE, K, DEF
                    "age": int,
                    "years_exp": int,
                    "status": str,             # Active, Inactive, Reserve, etc.
                    "team": str,               # NFL team abbreviation
                    "injury_status": str,      # Current injury or None
                    # ADP features
                    "adp": float,
                    "adp_std": float,
                    "times_drafted": int,
                    # Placeholder features (TODO: integrate external data)
                    "projected_points": float, # Always 0.0 currently
                    "position_rank": int       # Always 999 currently
                },
                ...
            ],
            "num_players": int,            # Successfully fetched count
            "missing_players": int         # player_ids not found in DB
        }
    
    Example:
        # Fetch features with ADP data
        adp = await calculate_adp_from_picks(CalculateADPParams(league_id="123"))
        features = await get_player_features_from_db(
            GetPlayerFeaturesParams(
                player_ids=["8150", "7553", "4866"],  # CMC, Bijan, Breece
                adp_data=adp["adp_data"]
            )
        )
        
        # Access specific player
        cmc = features["player_features"][0]
        print(f"{cmc['full_name']}: ADP {cmc['adp']:.1f}")
    
    Database Access:
        - Single bulk query: SELECT * FROM players WHERE player_id IN (...)
        - Optimized with player_id index
        - Typical: <100ms for 10-50 players
    
    Performance:
        - Query time: 50-200ms depending on player count
        - Memory: Minimal (<1MB for 100 players)
        - Network: PostgreSQL connection pooled by postgres_client
    
    Missing Data Handling:
        - Player not in DB: Exclude from results, increment missing_players
        - Missing ADP: Fill with defaults (adp=999, std=0, times=0)
        - Missing optional fields: Fill with None or sensible defaults
    
    TODO Integration Points:
        - projected_points: Integrate with external projection APIs (FantasyPros, ESPN)
        - position_rank: Calculate from projected_points within position group
        - injury_status: Real-time injury updates from NFL feed
    
    Related Activities:
        - predict_draft_pick: Consumes this output for inference (next step)
        - calculate_adp_from_picks: Provides adp_data input
        - enrich_training_samples: Similar enrichment for training pipeline
    
    Next Step:
        Pass player_features to predict_draft_pick along with draft_context for
        model inference.
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

    Combines per-player features with owner-specific context (historical
    tendencies + personality) to predict which player this owner will draft.
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
    Predict next draft pick from a specific team owner's perspective.

    Uses a TeamOwnerDraftModel trained on the owner's historical picks and
    driven by their personality traits. Each model represents an individual
    decision-maker — the goal is to simulate how *this* owner drafts, not
    the optimal pick.

    Personality influence
    ---------------------
    When personality_influence_scale is None (default), the scale is randomly
    sampled [0, 1] per pick. This creates natural variation: some picks look
    purely stat-driven; others reflect the owner's quirks (reaching for a name,
    avoiding rookies, etc.). Pass a fixed value (0.0–1.0) to hold it constant.

    Model inputs (all candidate players scored in a single batch)
    -------------------------------------------------------------
    - player_features:   (n_candidates, 9)  per-player stats / ADP / position
    - owner_profile:     (n_candidates, 26) owner history tiled across candidates
    - draft_context:     (n_candidates, 8)  current roster state tiled across candidates
    - personality_traits:(n_candidates, 8)  owner personality tiled across candidates

    Args:
        input: PredictOwnerDraftPickParams containing all required context.

    Returns:
        Dict[str, Any] with structure:
        {
            "predictions": {
                "top_prediction": {
                    "player_id": str,
                    "confidence": float,       # pick probability after softmax
                    "affinity_score": float,   # raw model score before softmax
                    "rank": int                # always 1
                },
                "all_predictions": [
                    {
                        "player_id": str,
                        "confidence": float,
                        "affinity_score": float,
                        "rank": int
                    },
                    ...   # sorted by confidence descending
                ],
                "position_priority": {
                    "QB": float, "RB": float, "WR": float,
                    "TE": float, "K": float, "DEF": float
                },
                "mean_confidence": float
            },
            "model_name": str,
            "personality_influence_used": float,   # scale applied for this pick
            "num_candidates": int
        }

    Example:
        result = await predict_owner_draft_pick(
            PredictOwnerDraftPickParams(
                player_features=available_players,
                draft_context={
                    "roster_needs_score": 0.9,
                    "draft_position": 12,
                    "picks_remaining": 168,
                    "round": 1,
                    "qb_need": 1,
                    "rb_slots_remaining": 2,
                    "wr_slots_remaining": 3,
                    "flex_need": 0.5,
                },
                owner_profile={
                    "early_rb_rate": 0.6, "early_wr_rate": 0.3,
                    "adp_deviation": 0.55,  # slight reach tendency
                    ...
                },
                personality_traits={
                    "upside_seeking": 0.8,
                    "contrarian": 0.2,
                    ...
                },
                model_name="owner_123456789_v1",
            )
        )
        top = result["predictions"]["top_prediction"]
        influence = result["personality_influence_used"]
        print(f"Owner picks {top['player_id']} (p={top['confidence']:.3f}, "
              f"personality_influence={influence:.2f})")
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

    Features (9):
        0  position_encoded       integer 0–5 (QB=0, RB=1, WR=2, TE=3, K=4, DEF=5)
        1  status_encoded         0.0–1.0
        2  age_normalized         age / 100
        3  years_exp_normalized   years_exp / 20
        4  adp_inverse            1 / (adp + 1)   — higher = earlier pick = more valuable
        5  projected_pts_norm     projected_points / 400
        6  position_rank_inverse  1 / (position_rank + 1)
        7  has_team               1 if on an NFL team else 0
        8  is_injured             1 if injury_status set else 0

    Args:
        player_features: List of player feature dicts from get_player_features_from_db.

    Returns:
        np.ndarray of shape (n_players, 9).
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

    Features (8):
        0  roster_needs_score     0–1 (urgency of filling a position need)
        1  draft_position_norm    draft_position / 200
        2  picks_remaining_norm   picks_remaining / 200
        3  round_norm             round / 18
        4  qb_need                1 if QB still needed for starting roster else 0
        5  rb_slots_norm          rb_slots_remaining / 4
        6  wr_slots_norm          wr_slots_remaining / 5
        7  flex_need              0–1 flex spot urgency

    Args:
        draft_context: Dict with current draft state.

    Returns:
        np.ndarray of shape (8,).
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

    Features (26) — all clipped to [0, 1]:
        0–5   early_*_rate   position pick rates in rounds 1–4 (QB, RB, WR, TE, K, DEF)
        6–11  mid_*_rate     position pick rates in rounds 5–8
        12–17 late_*_rate    position pick rates in rounds 9+
        18    adp_deviation        0=always waits, 0.5=neutral, 1=always reaches
        19    sleeper_pick_rate    fraction of picks below consensus value
        20    handcuff_rate        fraction of picks that were handcuffs
        21    qb_early_tendency   how often QB drafted before round 8
        22    te_premium_tendency how often TE1 drafted before round 5
        23    rb_heavy_early      fraction of rounds 1–4 on RBs
        24    wr_heavy_early      fraction of rounds 1–4 on WRs
        25    pick_consistency    consistency vs. consensus rank order

    Args:
        owner_profile: Dict with historical tendencies. Missing keys default to 0.0
                       (neutral/no tendency — model treats owner as typical).

    Returns:
        np.ndarray of shape (26,).
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
    Build the 8-dimensional personality trait feature vector from a single trait name.

    Maps the resolved trait name to its canonical slot (index 0–7 per
    RANDOM_PERSONALITY_TRAITS) and sets that slot to 0.5 (active/moderate
    expression). All other slots are set to 0.0 (trait not expressed).

    Slot order (matches RANDOM_PERSONALITY_TRAITS keys 0–7):
        0  upside_seeking          0=floor preference, 1=ceiling/boom-bust preference
        1  floor_preference        0=ignores floor, 1=always targets safe picks
        2  adp_reach_tendency      0=always waits, 0.5=neutral, 1=always reaches
        3  injury_tolerance        0=avoids any risk, 1=ignores injury status
        4  rookie_bias             0=avoids rookies, 0.5=neutral, 1=actively targets
        5  name_recognition        0=pure stats, 1=drafts by name / reputation
        6  contrarian              0=follows consensus, 1=goes against the board
        7  positional_stubbornness 0=BPA flexible, 1=sticks to positional strategy

    Example:
        _prepare_personality_features("contrarian")
        # → [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7, 0.0]

    Args:
        personality_trait: Single trait name string resolved from DB or random
                           fallback (e.g. "contrarian", "upside_seeking").
`
    Returns:
        np.ndarray of shape (9,) or (8,) with the matched trait slot set to 0.7,
        all others random for model variance.
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
        pick_probs:        (n,) softmax probabilities over candidates
        pick_scores:       (n,) raw affinity scores (before softmax)
        position_priority: (6,) positional preference vector
        player_features:   original player feature dicts (for player_id lookup)

    Returns:
        Structured prediction dict with top_prediction, all_predictions,
        position_priority, and mean_confidence.
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

    Scores all candidate players for a single owner in one forward pass per
    batch chunk. Intended for training validation (replay historical draft
    picks and score each pick scenario) and full-draft simulation.
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

    Functionally equivalent to calling predict_owner_draft_pick once, but processes
    large candidate sets in configurable chunk sizes for memory efficiency. The owner
    context (profile, draft state, personality) is tiled across every candidate in
    each chunk, matching the TeamOwnerDraftModel's four-stream input contract.

    Primary use cases:
    - Training validation: replay historical draft picks — for each pick in the
      owner's draft history, score all available players at that draft position
      to measure rank loss (was the actual pick top-ranked?).
    - Full-draft simulation: score all remaining players for each team when
      simulating an entire 200-pick draft without making individual activity calls.

    Args:
        input: BatchPredictOwnerParams with player candidates, owner context,
               model name, and optional batch_size / personality_influence_scale.

    Returns:
        Dict[str, Any]::

            {
                "predictions": [
                    {
                        "player_id": str,
                        "confidence": float,   # softmax probability
                        "affinity_score": float,
                        "rank": int
                    },
                    ...  # sorted by confidence descending
                ],
                "position_priority": {"QB": float, "RB": float, ...},
                "personality_influence_used": float,
                "model_name": str,
                "num_candidates": int,
                "num_batches": int
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