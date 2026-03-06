---
name: tensorflow-temporal
description: Integrate TensorFlow machine learning models with Temporal workflows. Use when adding ML model inference, training, or prediction capabilities to activities.
---

# Using TensorFlow in Temporal Python SDK Applications

This guide covers best practices for integrating TensorFlow ML models into Temporal Python SDK applications, maintaining deterministic workflows while leveraging TensorFlow's ML capabilities.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Installation & Setup](#installation--setup)
3. [Activity Patterns](#activity-patterns)
4. [Model Loading & Management](#model-loading--management)
5. [Inference Activities](#inference-activities)
6. [Training Activities](#training-activities)
7. [GPU Configuration](#gpu-configuration)
8. [Error Handling & Retries](#error-handling--retries)
9. [Testing](#testing)
10. [Performance Optimization](#performance-optimization)

---

## Architecture Overview

### Critical Rule: TensorFlow ONLY in Activities

**✅ DO**: Use TensorFlow in Activities  
**❌ DON'T**: Use TensorFlow in Workflows

**Why?** Temporal workflows MUST be deterministic and replayable. TensorFlow operations are:
- Non-deterministic (random seeds, GPU operations, model initialization)
- External (model file I/O, GPU memory allocation)
- State-changing (model weights, internal state)

```
┌─────────────────────────────────────────┐
│  Workflow (Deterministic)               │
│  - Orchestrates ML pipeline             │
│  - Manages execution order              │
│  - Handles failures/retries             │
│  ├─> execute_activity(load_model)      │
│  ├─> execute_activity(preprocess_data) │
│  ├─> execute_activity(predict)         │
│  └─> execute_activity(store_results)   │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  Activity (Non-Deterministic OK)        │
│  - Loads TensorFlow models              │
│  - Runs inference                       │
│  - Executes training                    │
│  - GPU/CPU operations                   │
└─────────────────────────────────────────┘
```

---

## Installation & Setup

### 1. Add TensorFlow to Requirements

Choose between CPU-only or GPU-enabled TensorFlow based on your needs:

#### CPU-Only Installation (Recommended for Most Use Cases)
```bash
# services/requirements.temporal_worker_service.txt
tensorflow==2.15.0
tensorflow-hub==0.15.0  # Optional: pre-trained models
```

**Pros:**
- ✅ Smaller Docker image (~500MB vs ~4GB)
- ✅ Simpler deployment (no CUDA/driver dependencies)
- ✅ Works on any machine (Mac, Linux, Windows)
- ✅ Sufficient for inference on small-medium models
- ✅ Lower cost (no GPU instance required)

**Cons:**
- ❌ Slower inference (2-10x slower than GPU)
- ❌ Much slower training (10-100x slower than GPU)
- ❌ Limited batch sizes (CPU memory constraints)

**Best for:** Inference workloads, small models, development/testing, cost-sensitive deployments

#### GPU Installation (For Heavy Workloads)
```bash
# services/requirements.temporal_worker_service.txt
tensorflow[and-cuda]==2.15.0  # GPU-enabled TensorFlow with CUDA
```

**Pros:**
- ✅ Fast inference (2-10x faster than CPU)
- ✅ Fast training (10-100x faster than CPU)
- ✅ Supports larger batch sizes
- ✅ Required for large models (>1GB parameters)

**Cons:**
- ❌ Large Docker image (~4GB)
- ❌ Requires GPU-enabled host (NVIDIA GPU + drivers)
- ❌ Complex setup (CUDA, cuDNN, driver versions)
- ❌ Higher cost (GPU instances are expensive)
- ❌ Not portable (won't run on Mac/Windows without NVIDIA GPU)

**Best for:** Model training, large-scale inference, real-time predictions, large models

### 2. Environment Variables

Add to `docker-compose.yaml` or `.env`:

```yaml
# Docker Compose
services:
  temporal-worker:
    environment:
      # TensorFlow Configuration
      TF_CPP_MIN_LOG_LEVEL: "2"           # 0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR
      TF_ENABLE_ONEDNN_OPTS: "0"          # Disable oneDNN optimizations if issues
      TF_FORCE_GPU_ALLOW_GROWTH: "true"   # Don't allocate all GPU memory at once
      CUDA_VISIBLE_DEVICES: "0"           # Which GPU to use (if multiple)
      
      # Model paths (mount as volumes)
      MODEL_PATH: "/app/models"
      MODEL_CACHE_DIR: "/app/.cache/models"
```

### 3. Directory Structure

```
src/
  activities/
    ml/
      __init__.py                    # Activity docstring only
      model_loader.py                # Model loading singleton
      inference.py                   # Prediction activities
      training.py                    # Training activities
      preprocessing.py               # Data preprocessing activities
    clients/
      tensorflow_client.py           # TensorFlow model manager singleton
  models/
    ml_models.py                     # Pydantic/dataclass models for ML I/O
  testing/
    ml/
      activities/
        test_inference.py
        test_training.py
```

---

## Activity Patterns

### Pattern 1: Model Loading Activity

Model loading is expensive—use a singleton pattern to cache loaded models.

**`src/activities/clients/tensorflow_client.py`**:
```python
"""TensorFlow model manager singleton for efficient model loading and caching."""

from typing import Dict, Optional
import tensorflow as tf
import os
from pathlib import Path


class TensorFlowModelManager:
    """
    Singleton manager for TensorFlow models.
    
    Caches loaded models to avoid repeated disk I/O and initialization overhead.
    Thread-safe for use across multiple activity executions.
    """
    
    _instance: Optional["TensorFlowModelManager"] = None
    _models: Dict[str, tf.keras.Model] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._configure_tensorflow()
        return cls._instance
    
    @staticmethod
    def _configure_tensorflow() -> None:
        """Configure TensorFlow for production use."""
        # Suppress excessive logging
        tf.get_logger().setLevel('ERROR')
        
        # Configure GPU memory growth (prevents OOM errors)
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            try:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
                print(f"TensorFlow configured with {len(gpus)} GPU(s)")
            except RuntimeError as e:
                print(f"GPU configuration failed: {e}")
        else:
            print("TensorFlow running on CPU")
    
    def load_model(self, model_name: str, model_path: Optional[str] = None) -> tf.keras.Model:
        """
        Load a TensorFlow/Keras model with caching.
        
        Args:
            model_name: Unique identifier for the model
            model_path: Path to saved model directory or .h5 file
        
        Returns:
            Loaded TensorFlow Keras model
        """
        # Return cached model if already loaded
        if model_name in self._models:
            print(f"Using cached model: {model_name}")
            return self._models[model_name]
        
        # Determine model path
        if model_path is None:
            base_path = os.getenv("MODEL_PATH", "/app/models")
            model_path = str(Path(base_path) / model_name)
        
        # Load model
        try:
            print(f"Loading model from: {model_path}")
            model = tf.keras.models.load_model(model_path)
            
            # Cache the model
            self._models[model_name] = model
            print(f"Successfully loaded and cached model: {model_name}")
            
            return model
            
        except Exception as e:
            print(f"Failed to load model {model_name}: {str(e)}")
            raise
    
    def unload_model(self, model_name: str) -> None:
        """Remove model from cache to free memory."""
        if model_name in self._models:
            del self._models[model_name]
            tf.keras.backend.clear_session()  # Clear TensorFlow session
            print(f"Unloaded model: {model_name}")
    
    def get_model_info(self, model_name: str) -> Dict[str, any]:
        """Get information about a cached model."""
        if model_name not in self._models:
            return {"error": f"Model {model_name} not loaded"}
        
        model = self._models[model_name]
        return {
            "model_name": model_name,
            "input_shape": model.input_shape,
            "output_shape": model.output_shape,
            "trainable_params": model.count_params(),
            "layers": len(model.layers),
        }


def get_tensorflow_model_manager() -> TensorFlowModelManager:
    """Get the singleton TensorFlow model manager instance."""
    return TensorFlowModelManager()
```

---

## Inference Activities

### Pattern 2: Prediction/Inference Activity

**`src/activities/ml/inference.py`**:
```python
"""ML inference activities using TensorFlow models."""

from dataclasses import dataclass
from typing import Dict, Any, List
import numpy as np
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import tensorflow as tf
    from activities.clients.tensorflow_client import get_tensorflow_model_manager


@dataclass
class PredictDraftPickParams:
    """Parameters for draft pick prediction."""
    player_features: List[Dict[str, Any]]  # Player stats, ADP, position, etc.
    draft_context: Dict[str, Any]          # Current draft state, roster needs
    model_name: str = "draft_predictor_v1"


@activity.defn(name="predict_draft_pick")
async def predict_draft_pick(input: PredictDraftPickParams) -> Dict[str, Any]:
    """
    Predict next draft pick using trained TensorFlow model.
    
    Args:
        input: Player features and draft context
    
    Returns:
        Dictionary with predicted player_id, confidence scores
    """
    try:
        # Get model manager and load model
        model_manager = get_tensorflow_model_manager()
        model = model_manager.load_model(input.model_name)
        
        # Preprocess features to model input format
        feature_array = _prepare_features(input.player_features, input.draft_context)
        
        # Run inference
        print(f"Running inference on {len(input.player_features)} players")
        predictions = model.predict(feature_array, verbose=0)
        
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
    
    Args:
        player_features: List of player feature dictionaries
        draft_context: Current draft state
    
    Returns:
        NumPy array ready for model input
    """
    # Example: Convert features to numpy array
    # Adjust based on your model's expected input shape
    feature_vectors = []
    
    for player in player_features:
        # Extract relevant features
        vector = [
            player.get("adp", 0),
            player.get("projected_points", 0),
            player.get("position_rank", 0),
            draft_context.get("roster_needs_score", 0),
            # ... more features
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
    Run batch predictions efficiently using TensorFlow batching.
    
    Useful for processing large datasets (e.g., predicting all draft scenarios).
    """
    try:
        model_manager = get_tensorflow_model_manager()
        model = model_manager.load_model(input.model_name)
        
        all_predictions = []
        num_batches = (len(input.items) + input.batch_size - 1) // input.batch_size
        
        print(f"Running batch prediction: {len(input.items)} items in {num_batches} batches")
        
        for i in range(0, len(input.items), input.batch_size):
            batch = input.items[i:i + input.batch_size]
            batch_array = _prepare_batch(batch)
            
            # Batch prediction is more efficient than individual calls
            batch_predictions = model.predict(batch_array, verbose=0)
            all_predictions.extend(batch_predictions)
        
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
```

---

## Training Activities

### Pattern 3: Model Training Activity

**`src/activities/ml/training.py`**:
```python
"""ML model training activities using TensorFlow."""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from temporalio import activity, workflow
from datetime import datetime
import os

with workflow.unsafe.imports_passed_through():
    import tensorflow as tf
    import numpy as np
    from activities.clients.tensorflow_client import get_tensorflow_model_manager


@dataclass
class TrainModelParams:
    """Parameters for model training."""
    training_data: List[Dict[str, Any]]
    validation_split: float = 0.2
    epochs: int = 50
    batch_size: int = 32
    learning_rate: float = 0.001
    model_name: str = "draft_predictor"
    save_path: Optional[str] = None


@activity.defn(name="train_draft_prediction_model")
async def train_draft_prediction_model(input: TrainModelParams) -> Dict[str, Any]:
    """
    Train a TensorFlow model for draft prediction.
    
    This is a long-running activity that should have:
    - Large timeout (minutes to hours)
    - Heartbeat to prevent timeout on long training
    - Checkpoint saving for recovery
    """
    try:
        print(f"Starting model training: {input.model_name}")
        print(f"Training samples: {len(input.training_data)}, Epochs: {input.epochs}")
        
        # Prepare data
        X_train, y_train = _prepare_training_data(input.training_data)
        
        # Build model
        model = _build_model(
            input_shape=X_train.shape[1:],
            learning_rate=input.learning_rate
        )
        
        # Setup callbacks
        callbacks = _get_training_callbacks(input.model_name, activity.info())
        
        # Train model with periodic heartbeats
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
        save_path = input.save_path or f"/app/models/{input.model_name}"
        model.save(save_path)
        print(f"Model saved to: {save_path}")
        
        # Get final metrics
        final_metrics = {
            "loss": float(history.history["loss"][-1]),
            "val_loss": float(history.history["val_loss"][-1]),
            "accuracy": float(history.history.get("accuracy", [0])[-1]),
            "epochs_completed": len(history.history["loss"]),
        }
        
        print(f"Training complete. Final loss: {final_metrics['loss']:.4f}")
        
        return {
            "model_name": input.model_name,
            "save_path": save_path,
            "metrics": final_metrics,
            "training_samples": len(input.training_data),
            "trained_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        print(f"Model training failed: {str(e)}")
        raise


def _prepare_training_data(training_data: List[Dict[str, Any]]) -> tuple:
    """
    Prepare training data for TensorFlow model.
    
    Returns:
        Tuple of (X_train, y_train) as numpy arrays
    """
    X = []
    y = []
    
    for sample in training_data:
        # Extract features and labels
        X.append(sample["features"])
        y.append(sample["label"])
    
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def _build_model(input_shape: tuple, learning_rate: float) -> tf.keras.Model:
    """
    Build a TensorFlow Keras model for draft prediction.
    
    Args:
        input_shape: Shape of input features
        learning_rate: Learning rate for optimizer
    
    Returns:
        Compiled Keras model
    """
    model = tf.keras.Sequential([
        tf.keras.layers.InputLayer(input_shape=input_shape),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid'),  # Binary classification
    ])
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    return model


def _get_training_callbacks(model_name: str, activity_info: Any) -> List[tf.keras.callbacks.Callback]:
    """
    Create TensorFlow callbacks for training.
    
    Includes:
    - Model checkpointing
    - Early stopping
    - Temporal activity heartbeat
    """
    callbacks = []
    
    # Checkpoint: Save best model during training
    checkpoint_path = f"/app/models/checkpoints/{model_name}_best.h5"
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
    
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
            patience=10,
            restore_best_weights=True,
            verbose=1
        )
    )
    
    # Custom callback for Temporal heartbeat
    class TemporalHeartbeatCallback(tf.keras.callbacks.Callback):
        """Send heartbeat to Temporal after each epoch."""
        
        def on_epoch_end(self, epoch, logs=None):
            # Record heartbeat to prevent activity timeout
            try:
                activity.heartbeat(f"Epoch {epoch + 1} complete")
                print(f"Heartbeat sent: Epoch {epoch + 1}")
            except Exception as e:
                print(f"Heartbeat failed: {e}")
    
    callbacks.append(TemporalHeartbeatCallback())
    
    return callbacks
```

---

## Model Loading & Management

### Pattern 4: Pre-loading Models at Worker Startup

For frequently used models, pre-load them when the worker starts to reduce cold-start latency.

**`src/workers/workflow_worker.py`** (add to worker initialization):

```python
async def main():
    """Start Temporal worker with TensorFlow models pre-loaded."""
    
    # Pre-load ML models before worker starts accepting tasks
    print("Pre-loading TensorFlow models...")
    try:
        from src.activities.clients.tensorflow_client import get_tensorflow_model_manager
        
        model_manager = get_tensorflow_model_manager()
        
        # Pre-load critical models
        model_manager.load_model("draft_predictor_v1")
        model_manager.load_model("player_value_estimator")
        
        print("TensorFlow models pre-loaded successfully")
    except Exception as e:
        print(f"Warning: Model pre-loading failed: {e}")
        print("Models will be loaded on-demand")
    
    # Start Temporal worker
    client = await Client.connect(...)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[...],
        activities=[...],
    )
    
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## GPU Configuration

### Docker Compose GPU Support

**`docker-compose.yaml`**:
```yaml
services:
  temporal-worker:
    build:
      context: ./src
      dockerfile: Dockerfile.temporal_worker_service
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      TF_FORCE_GPU_ALLOW_GROWTH: "true"
      CUDA_VISIBLE_DEVICES: "0"
```

### Checking GPU Availability in Activities

```python
@activity.defn(name="check_gpu_availability")
async def check_gpu_availability() -> Dict[str, Any]:
    """Check if TensorFlow can access GPU."""
    try:
        import tensorflow as tf
        
        gpus = tf.config.list_physical_devices('GPU')
        gpu_available = len(gpus) > 0
        
        if gpu_available:
            gpu_names = [gpu.name for gpu in gpus]
            print(f"GPUs available: {gpu_names}")
        else:
            print("No GPUs available, using CPU")
        
        return {
            "gpu_available": gpu_available,
            "num_gpus": len(gpus),
            "gpu_names": [gpu.name for gpu in gpus] if gpu_available else [],
            "tensorflow_version": tf.__version__,
        }
        
    except Exception as e:
        print(f"GPU check failed: {str(e)}")
        return {"error": str(e), "gpu_available": False}
```

---

## Error Handling & Retries

### Activity Retry Strategy for ML Operations

**In Workflow** (`src/workflows/ml_prediction.py`):

```python
from datetime import timedelta
from temporalio.common import RetryPolicy

# Retry policy for ML inference activities
inference_retry_policy = RetryPolicy(
    maximum_attempts=3,           # Retry up to 3 times
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
    non_retryable_error_types=[
        "ModelNotFoundError",     # Don't retry if model doesn't exist
        "InvalidInputShapeError", # Don't retry on bad input
    ]
)

# Retry policy for training activities (more patient)
training_retry_policy = RetryPolicy(
    maximum_attempts=2,           # Training is expensive, retry less
    initial_interval=timedelta(minutes=1),
    maximum_interval=timedelta(minutes=10),
    backoff_coefficient=2.0,
)

@workflow.run
async def run(self, params: MLPredictionParams) -> Dict[str, Any]:
    # Execute inference activity
    prediction = await workflow.execute_activity(
        predict_draft_pick,
        PredictDraftPickParams(
            player_features=params.player_features,
            draft_context=params.draft_context,
        ),
        start_to_close_timeout=timedelta(seconds=60),
        retry_policy=inference_retry_policy,
        heartbeat_timeout=timedelta(seconds=30),
    )
    
    return prediction
```

### Handling TensorFlow-Specific Errors

**In Activity**:
```python
@activity.defn(name="predict_with_error_handling")
async def predict_with_error_handling(input: PredictParams) -> Dict[str, Any]:
    """Prediction activity with comprehensive error handling."""
    try:
        model_manager = get_tensorflow_model_manager()
        model = model_manager.load_model(input.model_name)
        
        # Prepare input
        features = _prepare_features(input.features)
        
        # Validate input shape
        expected_shape = model.input_shape[1:]
        if features.shape[1:] != expected_shape:
            raise ValueError(
                f"Invalid input shape. Expected {expected_shape}, got {features.shape[1:]}"
            )
        
        # Run prediction
        predictions = model.predict(features, verbose=0)
        
        return {"predictions": predictions.tolist()}
        
    except FileNotFoundError as e:
        # Model file not found - don't retry
        print(f"Model not found: {input.model_name}")
        raise activity.ApplicationError(
            message=f"Model {input.model_name} not found",
            type="ModelNotFoundError",
            non_retryable=True,
        )
    
    except ValueError as e:
        # Invalid input - don't retry
        print(f"Invalid input: {str(e)}")
        raise activity.ApplicationError(
            message=str(e),
            type="InvalidInputShapeError",
            non_retryable=True,
        )
    
    except tf.errors.ResourceExhaustedError as e:
        # Out of memory - might succeed with retry (GPU memory might free up)
        print(f"GPU/CPU out of memory: {str(e)}")
        tf.keras.backend.clear_session()  # Clear session to free memory
        raise  # Retryable
    
    except Exception as e:
        # Generic error - retryable
        print(f"Prediction failed: {str(e)}")
        raise
```

---

## Testing

### Unit Testing TensorFlow Activities

**`src/testing/ml/activities/test_inference.py`**:

```python
"""Tests for TensorFlow inference activities."""

import pytest
import numpy as np
from temporalio.testing import ActivityEnvironment

# Relative imports from activities under test
from activities.ml.inference import predict_draft_pick, PredictDraftPickParams
from activities.clients.tensorflow_client import get_tensorflow_model_manager


@pytest.fixture
def mock_model(monkeypatch):
    """Mock TensorFlow model for testing without loading actual models."""
    
    class MockModel:
        def __init__(self):
            self.input_shape = (None, 10)
            self.output_shape = (None, 1)
        
        def predict(self, x, verbose=0):
            # Return mock predictions
            return np.random.rand(len(x), 1)
    
    def mock_load_model(self, model_name, model_path=None):
        return MockModel()
    
    # Patch model loading
    from activities.clients import tensorflow_client
    monkeypatch.setattr(
        tensorflow_client.TensorFlowModelManager,
        "load_model",
        mock_load_model
    )
    
    return MockModel()


@pytest.mark.asyncio
async def test_predict_draft_pick_success(mock_model):
    """Test successful draft pick prediction."""
    activity_env = ActivityEnvironment()
    
    params = PredictDraftPickParams(
        player_features=[
            {"player_id": "player1", "adp": 10, "projected_points": 250},
            {"player_id": "player2", "adp": 15, "projected_points": 230},
        ],
        draft_context={"roster_needs_score": 0.8},
        model_name="draft_predictor_v1"
    )
    
    result = await activity_env.run(predict_draft_pick, params)
    
    assert "predictions" in result
    assert "model_name" in result
    assert result["model_name"] == "draft_predictor_v1"
    assert result["num_candidates"] == 2


@pytest.mark.asyncio
async def test_predict_draft_pick_empty_features():
    """Test prediction with no player features."""
    activity_env = ActivityEnvironment()
    
    params = PredictDraftPickParams(
        player_features=[],
        draft_context={},
        model_name="draft_predictor_v1"
    )
    
    # Should handle gracefully or raise appropriate error
    with pytest.raises(Exception):
        await activity_env.run(predict_draft_pick, params)
```

### Integration Testing with Real Models

**`src/testing/ml/integration/test_model_integration.py`**:

```python
"""Integration tests with actual TensorFlow models."""

import pytest
from activities.clients.tensorflow_client import get_tensorflow_model_manager


@pytest.mark.integration
@pytest.mark.slow
def test_load_real_model():
    """Test loading actual trained model from disk."""
    model_manager = get_tensorflow_model_manager()
    
    # This requires a real model file to exist
    model = model_manager.load_model(
        "draft_predictor_v1",
        model_path="/app/models/draft_predictor_v1"
    )
    
    assert model is not None
    assert hasattr(model, 'predict')
    
    # Verify model info
    info = model_manager.get_model_info("draft_predictor_v1")
    assert info["model_name"] == "draft_predictor_v1"
    assert info["layers"] > 0
```

---

## Performance Optimization

### 1. Batch Processing for Inference

```python
# ✅ GOOD: Batch processing
predictions = model.predict(np.array([item1, item2, item3, ...]))

# ❌ BAD: Individual predictions
for item in items:
    prediction = model.predict(np.array([item]))
```

### 2. Model Quantization for Faster Inference

**Convert trained model to TensorFlow Lite for production**:

```python
@activity.defn(name="optimize_model_for_inference")
async def optimize_model_for_inference(input: OptimizeModelParams) -> Dict[str, Any]:
    """
    Convert TensorFlow model to optimized TFLite format.
    
    Benefits:
    - Smaller model size (up to 4x smaller)
    - Faster inference (2-4x faster)
    - Lower memory usage
    """
    import tensorflow as tf
    
    try:
        # Load original model
        model = tf.keras.models.load_model(input.model_path)
        
        # Convert to TensorFlow Lite
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        
        # Apply optimizations
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        # For even more compression (8-bit quantization)
        if input.quantize:
            converter.target_spec.supported_types = [tf.float16]
        
        tflite_model = converter.convert()
        
        # Save optimized model
        output_path = f"{input.model_path}_optimized.tflite"
        with open(output_path, 'wb') as f:
            f.write(tflite_model)
        
        print(f"Optimized model saved: {output_path}")
        
        return {
            "original_path": input.model_path,
            "optimized_path": output_path,
            "size_reduction": f"{(1 - len(tflite_model) / os.path.getsize(input.model_path)) * 100:.1f}%"
        }
        
    except Exception as e:
        print(f"Model optimization failed: {str(e)}")
        raise
```

### 3. Memory Management

```python
# Clear TensorFlow session after heavy operations
import tensorflow as tf

@activity.defn(name="memory_intensive_operation")
async def memory_intensive_operation(input: Params) -> Dict[str, Any]:
    """Activity with explicit memory cleanup."""
    try:
        # ... perform operations ...
        
        return result
        
    finally:
        # Always clear session to free GPU/CPU memory
        tf.keras.backend.clear_session()
        print("TensorFlow session cleared")
```

### 4. Parallel Model Inference

For multiple independent predictions, use TensorFlow's built-in parallelism:

```python
# TensorFlow automatically uses multiple CPU cores for inference
# Configure threading at worker startup:

import tensorflow as tf

tf.config.threading.set_intra_op_parallelism_threads(4)  # Parallel ops within operation
tf.config.threading.set_inter_op_parallelism_threads(2)  # Parallel operations
```

---

## Best Practices Summary

### ✅ DO

1. **Always use TensorFlow in Activities, never in Workflows**
2. **Use singleton pattern for model loading** (avoid reloading models)
3. **Implement heartbeats for long-running training activities**
4. **Add retry policies with appropriate timeouts**
5. **Use batch prediction for multiple items**
6. **Clear TensorFlow sessions after heavy operations**
7. **Log model versions and metrics for reproducibility**
8. **Handle GPU memory growth properly**
9. **Use activity.logger or print() for logging**
10. **Test with mocked models to avoid loading large files in tests**

### ❌ DON'T

1. **Don't import TensorFlow directly in workflow files**
2. **Don't reload models on every activity execution**
3. **Don't run training without heartbeats (will timeout)**
4. **Don't ignore OOM errors** (clear sessions, reduce batch size)
5. **Don't hardcode model paths** (use environment variables)
6. **Don't forget to save model checkpoints during training**
7. **Don't skip input validation before predictions**
8. **Don't use synchronous TensorFlow ops without timeouts**

---

## Complete Example: ML Prediction Workflow

**`src/workflows/ml_draft_prediction.py`**:

```python
"""Workflow for ML-powered draft prediction."""

from datetime import timedelta
from dataclasses import dataclass
from typing import Dict, Any, List
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.ml.inference import predict_draft_pick, PredictDraftPickParams
    from activities.ml.preprocessing import preprocess_players, PreprocessPlayersParams
    from activities.draft.get_draft_picks import get_draft_picks, GetDraftPicksParams


@dataclass
class MLDraftPredictionParams:
    """Parameters for ML draft prediction workflow."""
    draft_id: str
    available_players: List[str]
    current_roster: Dict[str, Any]
    model_name: str = "draft_predictor_v1"


@workflow.defn(name="ml-draft-prediction")
class MLDraftPredictionWorkflow:
    """
    Workflow that uses TensorFlow ML model to predict next draft pick.
    
    Steps:
    1. Fetch current draft state
    2. Preprocess available players
    3. Run ML prediction
    4. Return top recommendations
    """

    @workflow.run
    async def run(self, params: MLDraftPredictionParams) -> Dict[str, Any]:
        print(f"Starting ML draft prediction for draft: {params.draft_id}")
        
        activity_retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            backoff_coefficient=2.0,
        )
        
        # Step 1: Get draft context
        print("Fetching draft context...")
        draft_picks = await workflow.execute_activity(
            get_draft_picks,
            GetDraftPicksParams(draft_id=params.draft_id),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=activity_retry_policy,
        )
        
        # Step 2: Preprocess player features
        print("Preprocessing player features...")
        processed_features = await workflow.execute_activity(
            preprocess_players,
            PreprocessPlayersParams(
                player_ids=params.available_players,
                draft_context={"draft_picks": draft_picks}
            ),
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=activity_retry_policy,
        )
        
        # Step 3: Run ML prediction
        print("Running ML prediction...")
        prediction = await workflow.execute_activity(
            predict_draft_pick,
            PredictDraftPickParams(
                player_features=processed_features["players"],
                draft_context={
                    "roster": params.current_roster,
                    "draft_position": draft_picks.get("current_pick", 0)
                },
                model_name=params.model_name
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=activity_retry_policy,
        )
        
        print(f"Prediction complete. Top pick: {prediction['predictions']['top_prediction']}")
        
        return {
            "draft_id": params.draft_id,
            "prediction": prediction,
            "model_used": params.model_name,
            "candidates_evaluated": len(params.available_players)
        }
```

---

## Additional Resources

- **TensorFlow Documentation**: https://www.tensorflow.org/api_docs/python/tf
- **TensorFlow Guide**: https://www.tensorflow.org/guide
- **Temporal Python SDK**: https://docs.temporal.io/dev-guide/python
- **Keras Models**: https://www.tensorflow.org/api_docs/python/tf/keras/Model
- **TensorFlow Best Practices**: https://www.tensorflow.org/guide/profiler

---

## Troubleshooting

### Issue: "OOM when allocating tensor"

**Solution**: Enable GPU memory growth or reduce batch size
```python
gpus = tf.config.list_physical_devices('GPU')
for gpu in gpus:
    tf.config.experimental.set_memory_growth(gpu, True)
```

### Issue: "Activity timeout during training"

**Solution**: Increase timeout and add heartbeats
```python
# In workflow
start_to_close_timeout=timedelta(hours=2)
heartbeat_timeout=timedelta(minutes=5)

# In activity
activity.heartbeat(f"Training progress: {epoch}/{total_epochs}")
```

### Issue: "Model load time too slow"

**Solution**: Pre-load models at worker startup (see Pattern 4)

### Issue: "Predictions are non-deterministic"

**Solution**: Set random seeds (but note: some GPU ops are inherently non-deterministic)
```python
import numpy as np
import tensorflow as tf

np.random.seed(42)
tf.random.set_seed(42)
```

---

**Last Updated**: 2026-03-05  
**TensorFlow Version**: 2.15.0  
**Temporal Python SDK Version**: 1.5.0+
