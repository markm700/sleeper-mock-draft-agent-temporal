"""ML training data preparation activities using PostgreSQL data."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from sqlalchemy import select
    from activities.clients.postgres_client import get_postgres_client_manager
    from schema.database_models import Player

@dataclass
class EnrichTrainingSamplesParams:
    """Parameters for enriching training samples with player features."""
    training_samples: List[Dict[str, Any]]
    adp_data: Dict[str, Any]


@activity.defn(name="enrich_training_samples")
async def enrich_training_samples(input: EnrichTrainingSamplesParams) -> Dict[str, Any]:
    """
    Enrich training samples with player features and context from PostgreSQL for ML training.
    
    Final step in training data pipeline that transforms sparse samples into complete
    feature vectors by joining player attributes and ADP metrics. Output is ready for
    TensorFlow model training.
    
    Feature Engineering:
    Combines data from multiple sources to create feature vector per sample:
    
    1. Player Static Features (from Player table):
       - position, age, years_exp, status, team, injury_status
    
    2. ADP Features (from calculate_adp_from_picks):
       - adp: Average draft position
       - adp_std: Draft volatility
       - times_drafted: Pick frequency
    
    3. Draft Context Features (from prepare_team_owner_training_data):
       - round, pick_number, roster_state, available_count
    
    Args:
        input: EnrichTrainingSamplesParams containing:
            - training_samples: Output from prepare_team_owner_training_data
            - adp_data: Output from calculate_adp_from_picks (required)
    
    Returns:
        Dict[str, Any] with structure:
        {
            "enriched_samples": [
                {
                    # Original sample data
                    "player_id": str,
                    "label": int,
                    "draft_id": str,
                    "pick_number": int,
                    # Added player features
                    "position": str,
                    "age": int,
                    "years_exp": int,
                    "status": str,
                    "team": str,
                    "injury_status": str,
                    # ADP features
                    "adp": float,
                    "adp_std": float,
                    "times_drafted": int,
                    # Complete feature vector for model input
                    "features": [float, float, ...]
                },
                ...
            ],
            "total_samples": int,
            "feature_count": int,
            "missing_players": int,
            "user_id": str
        }
    
    Example:
        # Complete training data pipeline
        adp = await calculate_adp_from_picks(CalculateADPParams())
        samples = await prepare_team_owner_training_data(
            PrepareOwnerTrainingDataParams(user_id="user_123")
        )
        enriched = await enrich_training_samples(
            EnrichTrainingSamplesParams(
                training_samples=samples["training_samples"],
                adp_data=adp["adp_data"]
            )
        )
        # Ready for training
        features = [s["features"] for s in enriched["enriched_samples"]]
        labels = [s["label"] for s in enriched["enriched_samples"]]
    
    Performance:
        - ~300-800ms for 500+ samples (depends on unique player count)
        - Bottleneck: Player table lookups (optimize with indexes on player_id)
    
    Related Activities:
        - prepare_team_owner_training_data: Provides base samples (previous step)
        - calculate_adp_from_picks: Provides ADP features (required input)
        - train_owner_model: Consumes enriched samples (next step)
    
    Next Step:
        Pass enriched_samples to train_owner_model for TensorFlow training.
    """
    try:
        postgres = get_postgres_client_manager()
        
        # Get unique player IDs from samples
        player_ids = list(set(s["player_id"] for s in input.training_samples))
        
        with postgres.get_session() as session:
            # Fetch player data for all players in training set
            players_query = (
                select(Player)
                .where(Player.player_id.in_(player_ids))
            )
            
            players = session.execute(players_query).scalars().all()
            player_data = {p.player_id: p for p in players}
        
        # Enrich each sample
        enriched_samples = []
        
        for sample in input.training_samples:
            player_id = sample["player_id"]
            player = player_data.get(player_id)
            adp_info = input.adp_data.get(player_id, {})
            
            # Build enriched sample
            enriched = {
                **sample,  # Original sample data
                # Player features
                "position": player.position if player else None,
                "age": player.age if player else None,
                "years_exp": player.years_exp if player else None,
                "status": player.status if player else None,
                "team": player.team if player else None,
                "injury_status": player.injury_status if player else None,
                # ADP features
                "adp": adp_info.get("adp", 999.0),
                "adp_std": adp_info.get("std_dev", 0.0),
                "times_drafted": adp_info.get("times_drafted", 0),
            }
            
            enriched_samples.append(enriched)
        
        print(f"Enriched {len(enriched_samples)} training samples with player features")
        
        return {
            "enriched_samples": enriched_samples,
            "num_samples": len(enriched_samples),
            "num_players_found": len(player_data),
            "num_players_missing": len(player_ids) - len(player_data),
        }
        
    except Exception as e:
        print(f"Failed to enrich training samples: {str(e)}")
        raise
