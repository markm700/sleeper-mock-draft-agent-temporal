from typing import Dict, Any, List
import numpy as np
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities.ml.training.process.data_maps import POSITION_MAP, STATUS_MAP

def prepare_training_features(enriched_samples: List[Dict[str, Any]]) -> tuple:
    """
    Convert enriched training samples to feature arrays and labels.
    
    Args:
        enriched_samples: List of enriched sample dictionaries
    
    Returns:
        Tuple of (X_train, y_train) as numpy arrays
    """
    X = []
    y = []
    
    for sample in enriched_samples:
        # Position encoding
        position = sample.get("position", "")
        position_encoded = POSITION_MAP.get(position, -1)
        
        # Status encoding
        status = sample.get("status", "Active")
        status_encoded = STATUS_MAP.get(status, 0.5)
        
        # Player attributes
        age = sample.get("age", 25)
        years_exp = sample.get("years_exp", 0)
        
        # ADP and draft metrics
        adp = sample.get("adp", 999.0)
        adp_std = sample.get("adp_std", 0.0)
        times_drafted = sample.get("times_drafted", 0)
        
        # Draft context
        pick_no = sample.get("pick_no", 1)
        round_num = sample.get("round", 1)
        num_picked_before = sample.get("num_picked_before", 0)
        
        # Team status
        team = sample.get("team", "")
        has_team = 1.0 if team else 0.0
        
        # Injury status
        injury_status = sample.get("injury_status")
        is_injured = 1.0 if injury_status else 0.0
        
        # Build feature vector (15 features)
        feature_vector = [
            position_encoded,           # 0: Position (0-5)
            status_encoded,             # 1: Status (0-1)
            age / 100.0,                # 2: Age (normalized)
            years_exp / 20.0,           # 3: Years exp (normalized)
            1.0 / (adp + 1),            # 4: ADP (inverse, higher = better)
            adp_std / 100.0,            # 5: ADP variance (normalized)
            times_drafted / 100.0,      # 6: Times drafted (normalized)
            has_team,                   # 7: Has team (0 or 1)
            is_injured,                 # 8: Injury flag (0 or 1)
            pick_no / 200.0,            # 9: Pick number (normalized)
            round_num / 20.0,           # 10: Round (normalized)
            num_picked_before / 200.0,  # 11: Players already picked (normalized)
            # Derived features
            (adp - pick_no) / 100.0,    # 12: Reach score (negative = reach, positive = value)
            1.0 if pick_no <= 36 else 0.0,  # 13: Early pick flag (first 3 rounds typical)
            1.0 if position in ["QB", "RB", "WR", "TE"] else 0.0,  # 14: Core position flag
        ]
        
        X.append(feature_vector)
        y.append(sample["label"])  # Binary label: 1 = picked, 0 = not picked
    
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

