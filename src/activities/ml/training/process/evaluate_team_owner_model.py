"""ML model training activities using TensorFlow and PostgreSQL data."""

from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.tensorflow_client import get_tensorflow_model_manager
    from activities.ml.training.process.utils import prepare_training_features

@dataclass
class EvaluateOwnerModelParams:
    """Parameters for evaluating trained model."""
    user_id: str
    model_name: str
    test_samples: List[Dict[str, Any]]


@activity.defn(name="evaluate_owner_model")
async def evaluate_owner_model(input: EvaluateOwnerModelParams) -> Dict[str, Any]:
    """
    Evaluate trained owner model on held-out test data using scikit-learn metrics.
    
    Performs comprehensive model evaluation to assess real-world performance on unseen
    draft picks. Essential for validating model quality before deployment and monitoring
    performance degradation over time.
    
    Calculated Metrics:
    
    1. Accuracy: Fraction of correct binary predictions (threshold=0.5)
       - Good baseline metric
       - Target: >0.70 for viable model
    
    2. AUC-ROC: Area under receiver operating characteristic curve
       - Measures ranking quality across all thresholds
       - Target: >0.75 for good model, >0.85 for excellent
       - Preferred metric for imbalanced datasets
    
    3. Precision: Of predicted picks, what % were actually picked?
       - High precision = low false positives
       - Important if model drives auto-draft decisions
    
    4. Recall: Of actual picks, what % did model predict?
       - High recall = low false negatives
       - Important for not missing crucial picks
    
    5. Confusion Matrix: Breakdown of prediction outcomes
       - True Negatives: Correctly predicted non-picks
       - False Positives: Predicted pick but wasn't picked
       - False Negatives: Didn't predict pick but was picked
       - True Positives: Correctly predicted picks
    
    Args:
        input: EvaluateOwnerModelParams containing:
            - user_id: Owner user ID (for logging/tracking)
            - model_name: Trained model identifier (e.g., "owner_123456789_v1")
            - test_samples: Enriched samples with 'features' and 'label' keys
                           Should be held-out data NOT used in training
    
    Returns:
        Dict[str, Any] with structure:
        {
            "user_id": str,
            "model_name": str,
            "metrics": {
                "accuracy": float,          # Binary accuracy (0-1)
                "auc": float,               # AUC-ROC score (0-1)
                "precision": float,         # Precision (0-1)
                "recall": float,            # Recall (0-1)
                "test_samples": int,        # Number of test samples
            },
            "confusion_matrix": {
                "true_negative": int,       # Correct rejections
                "false_positive": int,      # Incorrect pick predictions
                "false_negative": int,      # Missed actual picks
                "true_positive": int        # Correct pick predictions
            },
            "evaluated_at": str             # ISO timestamp
        }
    
    Example:
        # Evaluate model on test set
        result = await evaluate_owner_model(
            EvaluateOwnerModelParams(
                user_id="123456789",
                model_name="owner_123456789_v1",
                test_samples=test_data  # From separate draft not used in training
            )
        )
        
        print(f"Accuracy: {result['metrics']['accuracy']:.3f}")
        print(f"AUC: {result['metrics']['auc']:.3f}")
        
        # Check confusion matrix
        cm = result['confusion_matrix']
        print(f"True Positives: {cm['true_positive']}")
        print(f"False Positives: {cm['false_positive']}")
    
    Interpretation Guidelines:
    
    Strong Model:
    - Accuracy: >0.75
    - AUC: >0.85
    - Precision: >0.70
    - Recall: >0.70
    
    Acceptable Model:
    - Accuracy: 0.65-0.75
    - AUC: 0.75-0.85
    - Precision: 0.60-0.70
    - Recall: 0.60-0.70
    
    Weak Model (needs retraining):
    - Accuracy: <0.65
    - AUC: <0.75
    - Consider: More training data, feature engineering, hyperparameter tuning
    
    Test Data Requirements:
        - Size: Minimum 50 samples, prefer 100+ for reliable metrics
        - Balance: Should reflect real draft scenarios (more negatives than positives)
        - Diversity: Include multiple drafts/scenarios for generalization
        - Recency: Recent drafts better reflect current owner behavior
    
    Model Loading:
        - Uses tensorflow_client singleton for efficient caching
        - Model loaded from {MODEL_PATH}/{model_name}.h5
        - Prediction batch processed for efficiency
    
    Performance:
        - Evaluation time: <1 second for 100 test samples
        - Memory: <500MB during inference
        - Network: None (local evaluation)
    
    Related Activities:
        - train_owner_model: Creates model being evaluated (previous step)
        - enrich_training_samples: Prepares test samples same way as training
        - predict_draft_pick: Uses model for real-time inference
    
    Best Practices:
        - Always evaluate on held-out test data (never training data)
        - Re-evaluate periodically as new draft data becomes available
        - Compare metrics across model versions to track improvements
        - Monitor AUC as primary metric (handles class imbalance well)
        - Use confusion matrix to identify specific model weaknesses
    
    Next Steps:
        1. If metrics acceptable: Deploy model for predictions
        2. If metrics weak: Retrain with more data or adjust architecture
        3. Monitor: Track prediction accuracy vs actual picks over time
        4. Retrain: When new draft data available or metrics degrade
    """
    try:
        print(f"Evaluating model for owner {input.user_id}")
        
        # Load model
        model_manager = get_tensorflow_model_manager()
        model = model_manager.load_model(input.model_name)
        
        # Prepare test features
        X_test, y_test = prepare_training_features(input.test_samples)
        
        # Get predictions
        predictions = model.predict(X_test, verbose=0).flatten()
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score, confusion_matrix
        
        # Binary predictions
        y_pred_binary = (predictions > 0.5).astype(int)
        
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred_binary)),
            "auc": float(roc_auc_score(y_test, predictions)),
            "precision": float(precision_score(y_test, y_pred_binary, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred_binary, zero_division=0)),
            "test_samples": len(X_test),
        }
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred_binary)
        metrics["confusion_matrix"] = {
            "true_negative": int(cm[0][0]),
            "false_positive": int(cm[0][1]),
            "false_negative": int(cm[1][0]),
            "true_positive": int(cm[1][1]),
        }
        
        print(f"Evaluation complete - Accuracy: {metrics['accuracy']:.3f}, AUC: {metrics['auc']:.3f}")
        
        return {
            "user_id": input.user_id,
            "model_name": input.model_name,
            "metrics": metrics,
            "evaluated_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        print(f"Model evaluation failed: {str(e)}")
        raise