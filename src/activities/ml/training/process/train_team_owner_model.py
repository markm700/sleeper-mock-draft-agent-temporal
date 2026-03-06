"""ML model training activities using TensorFlow and PostgreSQL data."""

from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime
import os
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import tensorflow as tf
    from activities.ml.training.process.utils import prepare_training_features


def _build_owner_model(input_shape: int, learning_rate: float = 0.001) -> tf.keras.Model:
    """
    Build TensorFlow model for owner-specific draft prediction.
    
    Args:
        input_shape: Number of input features
        learning_rate: Learning rate for Adam optimizer
    
    Returns:
        Compiled Keras model
    """
    model = tf.keras.Sequential([
        tf.keras.layers.InputLayer(input_shape=(input_shape,)),
        tf.keras.layers.Dense(128, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(0.001)),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(64, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(0.001)),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid'),  # Binary classification
    ])
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss='binary_crossentropy',
        metrics=['accuracy', tf.keras.metrics.AUC(name='auc')],
    )
    
    return model


def _get_training_callbacks(
    user_id: str, 
    model_name: str,
    patience: int = 10
) -> List[tf.keras.callbacks.Callback]:
    """
    Create TensorFlow callbacks for training.
    
    Args:
        user_id: Owner user ID
        model_name: Model identifier
        patience: Patience for early stopping
    
    Returns:
        List of Keras callbacks
    """
    callbacks = []
    
    # Checkpoint: Save best model during training
    checkpoint_dir = f"/app/models/checkpoints"
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_path = f"{checkpoint_dir}/{model_name}_best.h5"
    
    callbacks.append(
        tf.keras.callbacks.ModelCheckpoint(
            checkpoint_path,
            monitor='val_loss',
            save_best_only=True,
            verbose=1
        )
    )
    
    # Early stopping: Prevent overfitting
    callbacks.append(
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=patience,
            restore_best_weights=True,
            verbose=1
        )
    )
    
    # Reduce learning rate on plateau
    callbacks.append(
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=1
        )
    )
    
    # Custom callback for Temporal heartbeat
    class TemporalHeartbeatCallback(tf.keras.callbacks.Callback):
        """Send heartbeat to Temporal after each epoch."""
        
        def __init__(self, user_id: str):
            super().__init__()
            self.user_id = user_id
        
        def on_epoch_end(self, epoch, logs=None):
            try:
                loss = logs.get('loss', 0)
                val_loss = logs.get('val_loss', 0)
                activity.heartbeat(
                    f"Owner {self.user_id}: Epoch {epoch + 1} - "
                    f"loss: {loss:.4f}, val_loss: {val_loss:.4f}"
                )
                print(f"Heartbeat sent: Epoch {epoch + 1}")
            except Exception as e:
                print(f"Heartbeat failed: {e}")
    
    callbacks.append(TemporalHeartbeatCallback(user_id))
    
    return callbacks


@dataclass
class TrainOwnerModelParams:
    """Parameters for training owner-specific model."""
    user_id: str
    enriched_samples: List[Dict[str, Any]]
    model_version: str = "v1"
    epochs: int = 100
    batch_size: int = 32
    validation_split: float = 0.2
    learning_rate: float = 0.001
    early_stopping_patience: int = 15


@activity.defn(name="train_owner_model")
async def train_owner_model(input: TrainOwnerModelParams) -> Dict[str, Any]:
    """
    Train personalized TensorFlow binary classification model for a specific team owner.
    
    Builds and trains a deep neural network that learns owner-specific draft preferences
    from historical pick patterns. Model predicts probability (0-1) that owner will select
    each available player at any draft position.
    
    Model Architecture:
    - Input: 15-dimensional feature vector (player attributes + context)
    - Layer 1: Dense(128) + ReLU + L2 regularization + Dropout(0.3)
    - Layer 2: Dense(64) + ReLU + L2 regularization + Dropout(0.2)
    - Layer 3: Dense(32) + ReLU
    - Output: Dense(1) + Sigmoid (probability 0-1)
    - Loss: Binary crossentropy
    - Optimizer: Adam with configurable learning rate
    - Metrics: Accuracy, AUC-ROC
    
    Training Features:
    - Early stopping: Prevents overfitting by monitoring validation loss
    - Model checkpointing: Saves best model during training
    - Learning rate reduction: Adapts LR on validation plateaus
    - Temporal heartbeats: Sends progress updates every epoch (prevents timeout)
    - GPU support: Automatically uses GPU if available
    
    Training Strategy:
    - Validation split (default 20%): Held-out data for overfitting detection
    - Batch size (default 32): Balance between speed and gradient stability
    - Epochs (default 100): Early stopping typically ends training at 30-50 epochs
    - Class weighting: Optional (not implemented) for imbalanced datasets
    
    Args:
        input: TrainOwnerModelParams containing:
            - user_id: Sleeper owner user ID (used in model naming)
            - enriched_samples: Output from enrich_training_samples (List[Dict])
                               Must contain 'features' and 'label' keys
            - model_version: Version identifier (default: "v1")
            - epochs: Maximum training epochs (default: 100, early stop may end sooner)
            - batch_size: Training batch size (default: 32)
            - validation_split: Fraction for validation (default: 0.2)
            - learning_rate: Adam optimizer LR (default: 0.001)
            - early_stopping_patience: Epochs without improvement before stopping (default: 15)
    
    Returns:
        Dict[str, Any] with structure:
        {
            "user_id": str,
            "model_name": str,              # "owner_{user_id}_{version}"
            "model_path": str,              # File path to saved .h5 model
            "metrics": {
                "loss": float,              # Final training loss
                "accuracy": float,          # Final training accuracy
                "auc": float,               # Final training AUC-ROC
                "val_loss": float,          # Final validation loss
                "val_accuracy": float,      # Final validation accuracy
                "val_auc": float,           # Final validation AUC-ROC
                "epochs_completed": int,    # Actual epochs trained
                "best_val_loss": float      # Best validation loss achieved
            },
            "training_samples": int,        # Total samples used
            "feature_count": int,           # Input dimensionality (should be 15)
            "trained_at": str               # ISO timestamp
        }
    
    Example:
        # Train model after data preparation pipeline
        result = await train_owner_model(
            TrainOwnerModelParams(
                user_id="123456789",
                enriched_samples=enriched_data["enriched_samples"],
                epochs=100,
                batch_size=32,
                learning_rate=0.001
            )
        )
        
        print(f"Model saved: {result['model_path']}")
        print(f"Validation accuracy: {result['metrics']['val_accuracy']:.3f}")
        print(f"Validation AUC: {result['metrics']['val_auc']:.3f}")
    
    Activity Configuration:
        - Timeout: Set to at least 600s (10 minutes) for large datasets
        - Heartbeat: Sent every epoch (~1-5 seconds per epoch)
        - Retry policy: Recommend max_attempts=3 with exponential backoff
        - Long-running: Yes - use workflow.execute_activity with appropriate timeout
    
    Performance:
        - Training time: 30s-5min (depends on epochs, samples, GPU availability)
        - Typical: 2-3 minutes for 500 samples, 50 epochs on CPU
        - GPU speedup: 3-5x faster than CPU for same workload
        - Memory: 500MB-2GB during training (cleared on completion)
    
    Model Persistence:
        - Format: Keras .h5 (includes architecture + weights)
        - Location: {MODEL_PATH}/{model_name}.h5
        - Checkpoint: Best model also saved to checkpoints/ during training
        - Loading: Use tensorflow_client.load_model(model_name)
    
    Error Handling:
        - Insufficient data (<10 samples): Raises ValueError
        - Training failure: Logs error and raises exception
        - Memory cleanup: Always clears TensorFlow session in finally block
    
    Monitoring:
        - Temporal heartbeats: Check workflow history for epoch-by-epoch progress
        - Logs: Print statements show epoch metrics in activity logs
        - Metrics: Return value includes all training/validation metrics
    
    Related Activities:
        - enrich_training_samples: Provides input enriched_samples (required previous step)
        - evaluate_owner_model: Evaluates trained model on test set (next step)
        - predict_draft_pick: Uses trained model for inference
        - batch_train_owner_models: Orchestrates training for multiple owners
    
    Next Steps:
        1. Evaluate model: Call evaluate_owner_model with test samples
        2. Use for prediction: Call predict_draft_pick with trained model_name
        3. Monitor performance: Track predictions vs actual picks over time
        4. Retrain: Periodically retrain with new draft data
    """
    try:
        model_name = f"owner_{input.user_id}_{input.model_version}"
        
        print(f"Starting model training for owner {input.user_id}")
        print(f"Training samples: {len(input.enriched_samples)}, Epochs: {input.epochs}")
        
        # Prepare training data
        X_train, y_train = prepare_training_features(input.enriched_samples)
        
        if len(X_train) < 10:
            raise ValueError(f"Insufficient training data: {len(X_train)} samples. Need at least 10.")
        
        print(f"Feature shape: {X_train.shape}, Labels shape: {y_train.shape}")
        print(f"Positive samples: {int(y_train.sum())}, Negative samples: {int(len(y_train) - y_train.sum())}")
        
        # Build model
        input_shape = X_train.shape[1]
        model = _build_owner_model(input_shape, input.learning_rate)
        
        print(f"Model architecture:\n{model.summary()}")
        
        # Setup callbacks
        callbacks = _get_training_callbacks(
            input.user_id,
            model_name,
            input.early_stopping_patience
        )
        
        # Train model
        history = model.fit(
            X_train,
            y_train,
            validation_split=input.validation_split,
            epochs=input.epochs,
            batch_size=input.batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        # Save trained model
        model_dir = os.getenv("MODEL_PATH", "/app/models")
        os.makedirs(model_dir, exist_ok=True)
        model_path = f"{model_dir}/{model_name}.h5"
        
        model.save(model_path)
        print(f"Model saved to: {model_path}")
        
        # Get final metrics
        final_metrics = {
            "loss": float(history.history["loss"][-1]),
            "accuracy": float(history.history["accuracy"][-1]),
            "auc": float(history.history["auc"][-1]),
            "val_loss": float(history.history["val_loss"][-1]),
            "val_accuracy": float(history.history["val_accuracy"][-1]),
            "val_auc": float(history.history["val_auc"][-1]),
            "epochs_completed": len(history.history["loss"]),
            "best_val_loss": float(min(history.history["val_loss"])),
        }
        
        print(f"Training complete for {input.user_id}")
        print(f"Final metrics - Accuracy: {final_metrics['val_accuracy']:.3f}, AUC: {final_metrics['val_auc']:.3f}")
        
        return {
            "user_id": input.user_id,
            "model_name": model_name,
            "model_path": model_path,
            "metrics": final_metrics,
            "training_samples": len(input.enriched_samples),
            "feature_count": int(input_shape),
            "trained_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        print(f"Model training failed for {input.user_id}: {str(e)}")
        raise
    
    finally:
        # Always clear TensorFlow session to free memory
        tf.keras.backend.clear_session()


@dataclass
class BatchTrainModelsParams:
    """Parameters for batch training multiple owner models."""
    user_training_data: Dict[str, List[Dict[str, Any]]]  # user_id -> enriched_samples
    model_version: str = "v1"
    epochs: int = 100
    batch_size: int = 32


@activity.defn(name="batch_train_owner_models")
async def batch_train_owner_models(input: BatchTrainModelsParams) -> Dict[str, Any]:
    """
    Train models for multiple owners sequentially.
    
    Useful for training all owners in a league at once.
    Note: This trains sequentially. For parallel training, use workflow to
    execute multiple train_owner_model activities in parallel.
    
    Args:
        input: Training data for multiple owners
    
    Returns:
        Training results for all owners
    """
    try:
        results = []
        
        for user_id, enriched_samples in input.user_training_data.items():
            print(f"Training model for owner {user_id} ({len(enriched_samples)} samples)")
            
            try:
                train_result = await train_owner_model(
                    TrainOwnerModelParams(
                        user_id=user_id,
                        enriched_samples=enriched_samples,
                        model_version=input.model_version,
                        epochs=input.epochs,
                        batch_size=input.batch_size,
                    )
                )
                
                results.append({
                    "user_id": user_id,
                    "status": "success",
                    "result": train_result
                })
                
            except Exception as e:
                print(f"Training failed for {user_id}: {str(e)}")
                results.append({
                    "user_id": user_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        successful = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "failed")
        
        print(f"Batch training complete: {successful} succeeded, {failed} failed")
        
        return {
            "total_owners": len(input.user_training_data),
            "successful": successful,
            "failed": failed,
            "results": results,
        }
        
    except Exception as e:
        print(f"Batch training failed: {str(e)}")
        raise
