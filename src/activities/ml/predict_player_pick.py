import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import torch
    from sqlalchemy import select
    from activities.clients.pytorch_client import get_pytorch_model_manager
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import Player


@dataclass
class GetPlayerFeaturesParams:
    """Parameters for fetching player features from PostgreSQL."""
    player_ids: List[str]
    adp_data: Optional[Dict[str, Any]] = None  # Optional ADP data to merge


@activity.defn(name="get_player_features_from_d b")
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


@dataclass
class PredictDraftPickParams:
    """Parameters for draft pick prediction."""
    player_features: List[Dict[str, Any]]  # Player stats, ADP, position, etc.
    draft_context: Dict[str, Any]          # Current draft state, roster needs
    model_name: str = "draft_predictor_v1"


@activity.defn(name="predict_draft_pick")
async def predict_draft_pick(input: PredictDraftPickParams) -> Dict[str, Any]:
    """
    Predict next draft pick using trained owner-specific PyTorch model.
    
    Core inference activity that scores available players and predicts which player
    an owner is most likely to select given current draft state. Uses personalized
    model trained on owner's historical picks.
    
    Prediction Pipeline:
    1. Load trained model from pytorch_client (cached for efficiency)
    2. Convert player features + draft context to feature tensors
    3. Run batch inference on all available players with model.eval() and torch.no_grad()
    4. Rank players by prediction score (0-1 probability)
    5. Return top prediction and full ranked list
    
    Feature Vector (15 dimensions):
    - Position encoded (0-5)
    - Status encoded (0-1)
    - Age normalized (0-1)
    - Years experience normalized (0-1)
    - ADP inverse normalized (higher = earlier pick = higher value)
    - Projected points normalized (0-1)
    - Position rank inverse normalized
    - Has team binary (0 or 1)
    - Roster needs score (0-1 from draft context)
    - Draft position normalized (0-1)
    - Picks remaining normalized (0-1)
    - Injury flag (0 or 1)
    
    Args:
        input: PredictDraftPickParams containing:
            - player_features: List of player dicts from get_player_features_from_db
                              Each must have: position, age, years_exp, status, team,
                              injury_status, adp, projected_points, position_rank
            - draft_context: Dict with current draft state:
                * roster_needs_score: How urgently position needed (0-1)
                * draft_position: Current overall pick number (1-200+)
                * picks_remaining: Picks left in draft
                * (optional) current_roster: Positions already filled
            - model_name: Trained model identifier (e.g., "owner_123456789_v1")
                         Must exist in {MODEL_PATH}/ directory
    
    Returns:
        Dict[str, Any] with structure:
        {
            "predictions": {
                "top_prediction": {
                    "player_id": str,       # Most likely pick
                    "confidence": float,    # Model score 0-1
                    "rank": int             # Always 1
                },
                "all_predictions": [
                    {"player_id": str, "confidence": float, "rank": int},
                    ...  # Sorted by confidence descending
                ],
                "mean_confidence": float    # Average score across all players
            },
            "model_name": str,
            "num_candidates": int           # Number of players scored
        }
    
    Example:
        # Predict next pick for owner
        draft_context = {
            "roster_needs_score": 0.8,  # Really needs RB
            "draft_position": 24,        # Pick 24 overall
            "picks_remaining": 156
        }
        
        result = await predict_draft_pick(
            PredictDraftPickParams(
                player_features=available_players,  # From get_player_features_from_db
                draft_context=draft_context,
                model_name="owner_123456789_v1"
            )
        )
        
        top = result["predictions"]["top_prediction"]
        print(f"Predicted pick: {top['player_id']} (confidence: {top['confidence']:.3f})")
        
        # Show top 5
        for pred in result["predictions"]["all_predictions"][:5]:
            print(f"{pred['rank']}. Player {pred['player_id']}: {pred['confidence']:.3f}")
    
    Confidence Score Interpretation:
        - 0.8-1.0: Very confident prediction (strong historical pattern match)
        - 0.6-0.8: Confident prediction (good pattern match)
        - 0.4-0.6: Uncertain (multiple viable options)
        - 0.2-0.4: Unlikely pick
        - 0.0-0.2: Very unlikely pick
    
    Model Loading:
        - Uses pytorch_client singleton for caching
        - First call loads model (200-500ms)
        - Subsequent calls reuse cached model (<10ms)
        - Models automatically unloaded if memory pressure
        - Automatically detects and uses GPU if available
    
    Performance:
        - Inference time: 10-50ms for 10 players (after model loaded)
        - Scales linearly with player count
        - Batch size: All players processed in single forward pass
        - Memory: Model size (5-20MB) + inference batch (<1MB)
    
    Draft Context Usage:
        roster_needs_score calculation (in workflow/application):
        ```python
        position_counts = {"QB": 1, "RB": 1, "WR": 2, "TE": 0}
        roster_targets = {"QB": 2, "RB": 2, "WR": 3, "TE": 1}
        
        # For player being evaluated
        need = 1.0 - (position_counts[player_pos] / roster_targets[player_pos])
        roster_needs_score = max(0, min(1, need))
        ```
    
    Related Activities:
        - get_player_features_from_db: Fetches player_features input (required first step)
        - train_owner_model: Creates model being used for prediction
        - evaluate_owner_model: Validates model quality
        - batch_predict: Efficient alternative for scoring many scenarios
    
    Use Cases:
        - Live draft assistance: Predict opponent picks
        - Mock draft simulation: Simulate full draft with all owner models
        - Draft strategy analysis: Identify unexpected picks (actual vs predicted)
        - Auto-draft: Automate picks for absent owners
    
    Error Handling:
        - Model not found: Raises exception (ensure model_name correct)
        - Empty player_features: Returns error in predictions
        - Invalid draft_context: Uses default values (may reduce accuracy)
    
    Next Steps:
        1. Compare prediction to actual pick (for monitoring)
        2. Update roster state after pick
        3. Repeat for next pick with updated context
        4. Retrain model periodically with new pick data
    """
    try:
        # Get model manager and load model
        model_manager = get_pytorch_model_manager()
        model = model_manager.load_model(input.model_name)
        device = model_manager.get_device()
        
        # Ensure model is on correct device and in eval mode
        model = model.to(device)
        model.eval()
        
        # Preprocess features to model input format
        feature_array = _prepare_features(input.player_features, input.draft_context)
        
        # Convert to PyTorch tensor
        feature_tensor = torch.tensor(feature_array, dtype=torch.float32).to(device)
        
        # Run inference with no gradient computation
        print(f"Running inference on {len(input.player_features)} players")
        with torch.no_grad():
            predictions_tensor = model(feature_tensor)
        
        # Convert back to numpy for post-processing
        predictions = predictions_tensor.cpu().numpy()
        
        # Post-process predictions
        results = _postprocess_predictions(
            predictions, 
            input.player_features
        )
        
        print(f"Prediction complete. Top pick: {results['top_prediction']['player_id']}")
        
        return {
            "predictions": results,
            "model_name": input.model_name,
            "num_candidates": len(input.player_features)
        }
        
    except Exception as e:
        print(f"Prediction failed: {str(e)}")
        raise


def _prepare_features(
    player_features: List[Dict[str, Any]], 
    draft_context: Dict[str, Any]
) -> np.ndarray:
    """
    Convert player features to model input format.
    
    Extracts and normalizes features from Player data including:
    - Position encoding (QB, RB, WR, TE, K, DEF)
    - Player status (Active, Inactive, etc.)
    - Age and experience
    - Draft metrics (ADP, projected points, position rank)
    - Team context
    - Roster needs
    
    Args:
        player_features: List of player feature dictionaries with Player model fields
        draft_context: Current draft state (roster needs, pick position, etc.)
    
    Returns:
        NumPy array ready for model input [num_players, num_features]
    """
    # Position encoding map
    position_map = {
        "QB": 0, "RB": 1, "WR": 2, "TE": 3, "K": 4, "DEF": 5
    }
    
    # Status encoding map
    status_map = {
        "Active": 1.0, "Inactive": 0.0, "Reserve": 0.5, "PUP": 0.3, "Suspended": 0.2
    }
    
    feature_vectors = []
    
    for player in player_features:
        # Position encoding (one-hot alternative: use position index)
        position = player.get("position", "")
        position_encoded = position_map.get(position, -1)
        
        # Player status encoding
        status = player.get("status", "Active")
        status_encoded = status_map.get(status, 0.5)
        
        # Player attributes (with defaults)
        age = player.get("age", 25)  # Default median age
        years_exp = player.get("years_exp", 0)
        
        # Draft/Fantasy metrics
        adp = player.get("adp", 999)  # Average Draft Position
        projected_points = player.get("projected_points", 0.0)
        position_rank = player.get("position_rank", 999)
        
        # Team context (1 if on good team, 0 otherwise - could be enhanced with team rankings)
        team = player.get("team", "")
        has_team = 1.0 if team else 0.0
        
        # Draft context features
        roster_needs_score = draft_context.get("roster_needs_score", 0.5)
        draft_position = draft_context.get("draft_position", 1)
        picks_remaining = draft_context.get("picks_remaining", 100)
        
        # Injury status
        injury_status = player.get("injury_status")
        is_injured = 1.0 if injury_status else 0.0
        
        # Build feature vector
        vector = [
            position_encoded,           # 0: Position (0-5)
            status_encoded,             # 1: Status (0-1)
            age / 100.0,                # 2: Age (normalized)
            years_exp / 20.0,           # 3: Years exp (normalized)
            1.0 / (adp + 1),            # 4: ADP (inverse, higher = better)
            projected_points / 400.0,   # 5: Projected points (normalized)
            1.0 / (position_rank + 1),  # 6: Position rank (inverse)
            has_team,                   # 7: Has team (0 or 1)
            roster_needs_score,         # 8: Roster needs fit (0-1)
            draft_position / 200.0,     # 9: Draft position (normalized)
            picks_remaining / 200.0,    # 10: Picks remaining (normalized)
            is_injured,                 # 11: Injury flag (0 or 1)
        ]
        
        feature_vectors.append(vector)
    
    return np.array(feature_vectors, dtype=np.float32)


def _postprocess_predictions(
    predictions: np.ndarray,
    player_features: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convert model output to structured predictions.
    
    Args:
        predictions: Raw model output
        player_features: Original player data
    
    Returns:
        Structured prediction results
    """
    # Get top prediction
    top_idx = int(np.argmax(predictions))
    confidence_scores = predictions.flatten().tolist()
    
    # Combine with player IDs
    ranked_predictions = [
        {
            "player_id": player_features[i]["player_id"],
            "confidence": float(confidence_scores[i]),
            "rank": i + 1
        }
        for i in np.argsort(predictions.flatten())[::-1]
    ]
    
    return {
        "top_prediction": ranked_predictions[0],
        "all_predictions": ranked_predictions,
        "mean_confidence": float(np.mean(predictions)),
    }


@dataclass
class BatchPredictParams:
    """Parameters for batch prediction."""
    items: List[Dict[str, Any]]
    model_name: str
    batch_size: int = 32


@activity.defn(name="batch_predict")
async def batch_predict(input: BatchPredictParams) -> Dict[str, Any]:
    """
    Run batch predictions efficiently using PyTorch batching for large-scale inference.
    
    Optimized for scenarios requiring predictions across many items simultaneously,
    such as:
    - Simulating entire draft (predict all picks for all owners)
    - Analyzing historical drafts (predict all past picks for validation)
    - Multi-scenario analysis (predict picks across different roster states)
    
    Performance Benefits:
    - Batched inference: 5-10x faster than individual predict calls
    - Single model load: Amortized loading cost across all items
    - GPU utilization: Better GPU occupancy with larger batches
    - Memory efficient: Processes in configurable batch chunks
    
    Args:
        input: BatchPredictParams containing:
            - items: List of dicts, each with 'features' key (15-dim array)
            - model_name: Trained model identifier
            - batch_size: Chunk size for processing (default: 32)
                         Tune based on memory: 16 for low memory, 64+ for GPU
    
    Returns:
        Dict[str, Any] with structure:
        {
            "predictions": [float, ...],  # One score per item (0-1)
            "num_items": int,              # Total items processed
            "batch_size": int              # Batch size used
        }
    
    Example:
        # Predict all picks in a mock draft simulation
        scenarios = [
            {"features": [0.2, 0.8, ...]},  # Pick 1 candidate 1
            {"features": [0.3, 0.7, ...]},  # Pick 1 candidate 2
            ...
        ]
        
        result = await batch_predict(
            BatchPredictParams(
                items=scenarios,
                model_name="owner_123456789_v1",
                batch_size=64
            )
        )
        
        # Process results
        for i, score in enumerate(result["predictions"]):
            print(f"Scenario {i}: {score:.3f}")
    
    Performance:
        - Small batches (10-100 items): 50-200ms
        - Medium batches (100-1000 items): 200-500ms
        - Large batches (1000+ items): 0.5-2s
        - GPU speedup: 3-5x faster than CPU for batches >100
    
    Batch Size Guidelines:
        - CPU: 16-32 (balance memory and speed)
        - GPU: 64-128 (maximize GPU utilization)
        - Memory constrained: 8-16
        - Large models: Reduce if OOM errors
    
    Related Activities:
        - predict_draft_pick: Single prediction alternative (simpler interface)
        - train_owner_model: Creates model being used
    
    Use Cases:
        - Mock draft simulation: Predict 200+ picks across 12 owners
        - Historical analysis: Validate model on past drafts
        - Monte Carlo scenarios: Test draft strategies across variations
    """
    try:
        model_manager = get_pytorch_model_manager()
        model = model_manager.load_model(input.model_name)
        device = model_manager.get_device()
        
        # Ensure model is on correct device and in eval mode
        model = model.to(device)
        model.eval()
        
        all_predictions = []
        num_batches = (len(input.items) + input.batch_size - 1) // input.batch_size
        
        print(f"Running batch prediction: {len(input.items)} items in {num_batches} batches")
        
        with torch.no_grad():
            for i in range(0, len(input.items), input.batch_size):
                batch = input.items[i:i + input.batch_size]
                batch_array = _prepare_batch(batch)
                
                # Convert to tensor and move to device
                batch_tensor = torch.tensor(batch_array, dtype=torch.float32).to(device)
                
                # Batch prediction is more efficient than individual calls
                batch_predictions = model(batch_tensor)
                
                # Convert back to numpy and extend results
                all_predictions.extend(batch_predictions.cpu().numpy())
        
        print(f"Batch prediction complete: {len(all_predictions)} results")
        
        return {
            "predictions": [float(p) for p in all_predictions],
            "num_items": len(input.items),
            "batch_size": input.batch_size
        }
        
    except Exception as e:
        print(f"Batch prediction failed: {str(e)}")
        raise


def _prepare_batch(items: List[Dict[str, Any]]) -> np.ndarray:
    """Convert batch items to model input format."""
    # Implement based on your data structure
    return np.array([item["features"] for item in items], dtype=np.float32)


# ──────────────────────────────────────────────────────────────────────────────
# Team-owner-centric prediction
# ──────────────────────────────────────────────────────────────────────────────

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
    personality_traits: Dict[str, Any]      # Owner's personality trait vector
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

        # Build per-player tensors
        player_array = _prepare_player_features_only(input.player_features)     # (n, 9)
        context_array = _prepare_draft_context_features(input.draft_context)    # (8,)
        profile_array = _prepare_owner_profile_features(input.owner_profile)    # (26,)
        personality_array = _prepare_personality_features(input.personality_traits)  # (8,)

        # Tile owner/context/personality across all candidates
        context_tiled = np.tile(context_array, (n, 1))      # (n, 8)
        profile_tiled = np.tile(profile_array, (n, 1))      # (n, 26)
        personality_tiled = np.tile(personality_array, (n, 1))  # (n, 8)

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
                pick_scores, confidence, position_priority, influence = (
                    model.predict_with_random_personality(
                        player_t, profile_t, context_t, personality_t
                    )
                )
            else:
                pick_scores, confidence, position_priority = model(
                    player_t, profile_t, context_t, personality_t,
                    personality_influence_scale=influence,
                )

        # pick_scores: (n, 1) → apply softmax across candidates → pick probabilities
        pick_scores_np = pick_scores.squeeze(1).cpu().numpy()           # (n,)
        pick_probs_np = np.exp(pick_scores_np) / np.exp(pick_scores_np).sum()  # softmax
        confidence_np = confidence.squeeze(1).cpu().numpy()             # (n,)
        position_priority_np = position_priority[0].cpu().numpy()       # (6,) — same for all

        results = _postprocess_owner_predictions(
            pick_probs_np, pick_scores_np, confidence_np, position_priority_np,
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


def _prepare_personality_features(personality_traits: Dict[str, Any]) -> np.ndarray:
    """
    Build the 8-dimensional personality trait feature vector.

    Maps the PERSONALITY_TRAITS contract from team_owner_model.py to a float
    array. All values are expected in [0, 1] (or 0.5 = neutral for bipolar traits).
    Missing keys default to 0.5 (neutral — no particular trait expressed).

    Features (8):
        0  upside_seeking         0=floor preference, 1=ceiling/boom-bust preference
        1  floor_preference       0=ignores floor, 1=always targets safe picks
        2  adp_reach_tendency     0=always waits, 0.5=neutral, 1=always reaches
        3  injury_tolerance       0=avoids any risk, 1=ignores injury status
        4  rookie_bias            0=avoids rookies, 0.5=neutral, 1=actively targets
        5  name_recognition       0=pure stats, 1=drafts by name / reputation
        6  contrarian             0=follows consensus, 1=goes against the board
        7  positional_stubbornness 0=BPA flexible, 1=sticks to positional strategy

    Args:
        personality_traits: Dict mapping trait names to floats.

    Returns:
        np.ndarray of shape (8,).
    """
    g = personality_traits.get
    return np.array([
        g("upside_seeking", 0.5),
        g("floor_preference", 0.5),
        g("adp_reach_tendency", 0.5),
        g("injury_tolerance", 0.5),
        g("rookie_bias", 0.5),
        g("name_recognition", 0.5),
        g("contrarian", 0.5),
        g("positional_stubbornness", 0.5),
    ], dtype=np.float32)


def _postprocess_owner_predictions(
    pick_probs: np.ndarray,
    pick_scores: np.ndarray,
    confidence: np.ndarray,
    position_priority: np.ndarray,
    player_features: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Convert TeamOwnerDraftModel output to structured predictions.

    Args:
        pick_probs:        (n,) softmax probabilities over candidates
        pick_scores:       (n,) raw affinity scores (before softmax)
        confidence:        (n,) per-candidate confidence scores
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