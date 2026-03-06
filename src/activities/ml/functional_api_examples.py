"""
Examples demonstrating Functional API usage for draft prediction.

Shows how to use TensorFlowModelManager to build, train, and deploy
Functional API models for fantasy football draft prediction.
"""

from typing import Dict, Any
import numpy as np
from temporalio import workflow

# Import TensorFlow client through Temporal's import manager
with workflow.unsafe.imports_passed_through():
    from activities.clients.tensorflow_client import get_tensorflow_model_manager


# ========== Example 1: Basic Draft Prediction Model ==========

def example_basic_model():
    """
    Build and compile a basic Functional API model for draft prediction.
    
    This is the simplest use case: predict which player an owner will pick
    based on player features, owner preferences, and draft context.
    """
    manager = get_tensorflow_model_manager()
    
    # Build model with Functional API
    model = manager.build_draft_prediction_model(
        num_players=500,           # 500 possible players
        player_feature_dim=50,     # 50 player features (ADP, stats, position, etc.)
        owner_feature_dim=20,      # 20 owner preference features
        draft_context_dim=15,      # 15 draft context features (available spots, etc.)
        hidden_layers=[256, 128, 64],
        dropout_rate=0.3
    )
    
    # Compile with appropriate loss function
    model = manager.compile_model(
        model,
        learning_rate=0.001,
        loss='categorical_crossentropy',  # Multi-class classification
        metrics=['accuracy']
    )
    
    # Model is ready for training!
    print("\n=== Model Architecture ===")
    model.summary()
    
    # Example training (pseudocode)
    # model.fit(
    #     [player_features, owner_features, draft_context],
    #     pick_labels,  # One-hot encoded (500 classes)
    #     epochs=50,
    #     batch_size=32,
    #     validation_split=0.2
    # )
    
    # Save model
    save_path = manager.save_model(model, "draft_model_v1")
    print(f"\nModel saved to: {save_path}")
    
    return model


# ========== Example 2: Multi-Output Model ==========

def example_multi_output_model():
    """
    Build a model that predicts multiple outputs:
    - Which player will be picked
    - Confidence in the prediction
    - Position preference (QB/RB/WR/TE/K/DEF)
    
    Multi-output models provide richer predictions and insights.
    """
    manager = get_tensorflow_model_manager()
    
    # Build multi-output model
    model = manager.build_multi_output_model(
        num_players=500,
        player_feature_dim=50,
        owner_feature_dim=20,
        draft_context_dim=15
    )
    
    # Compile with multiple losses (one per output)
    model.compile(
        optimizer='adam',
        loss={
            'pick_probability': 'categorical_crossentropy',
            'confidence_score': 'binary_crossentropy',
            'position_preference': 'categorical_crossentropy'
        },
        loss_weights={
            'pick_probability': 1.0,    # Most important
            'confidence_score': 0.3,     # Moderate importance
            'position_preference': 0.5   # Moderate importance
        },
        metrics={
            'pick_probability': ['accuracy'],
            'confidence_score': ['mae'],
            'position_preference': ['accuracy']
        }
    )
    
    print("\n=== Multi-Output Model ===")
    model.summary()
    
    # Example prediction
    # outputs = model.predict([player_feat, owner_feat, draft_ctx])
    # pick_prob, confidence, position_pref = outputs
    
    return model


# ========== Example 3: Custom Architecture ==========

def example_custom_architecture():
    """
    Build a completely custom Functional API model with flexible configuration.
    
    Use this when you need non-standard architectures, custom input/output combinations,
    or experimental features.
    """
    manager = get_tensorflow_model_manager()
    
    # Define custom inputs and outputs
    input_shapes = {
        'player': (50,),        # Player features
        'owner': (20,),         # Owner preferences
        'draft': (15,),         # Draft context
        'league': (10,),        # League settings (NEW!)
        'personality': (5,)     # Personality fun facts encoded (NEW!)
    }
    
    output_shapes = {
        'pick': (500,),         # Pick probability
        'confidence': (1,),     # Confidence score
    }
    
    architecture_config = {
        'shared_layers': [512, 256, 128],  # Deeper network
        'dropout': 0.4                      # Higher regularization
    }
    
    model = manager.build_custom_functional_model(
        input_shapes=input_shapes,
        output_shapes=output_shapes,
        architecture_config=architecture_config,
        model_name='custom_draft_model'
    )
    
    print("\n=== Custom Architecture ===")
    model.summary()
    
    return model


# ========== Example 4: Training Pipeline ==========

def example_training_pipeline():
    """
    Complete training pipeline: build → compile → train → evaluate → save.
    
    This is what you'd use in a real activity.
    """
    manager = get_tensorflow_model_manager()
    
    # 1. Build model
    model = manager.build_draft_prediction_model(
        num_players=500,
        player_feature_dim=50,
        owner_feature_dim=20,
        draft_context_dim=15
    )
    
    # 2. Compile with custom settings
    model = manager.compile_model(
        model,
        learning_rate=0.0005,  # Lower learning rate for stability
        loss='categorical_crossentropy'
    )
    
    # 3. Prepare training data (pseudocode)
    # X_player, X_owner, X_draft, y_picks = prepare_training_data()
    
    # 4. Train model with callbacks
    # history = model.fit(
    #     [X_player, X_owner, X_draft],
    #     y_picks,
    #     epochs=100,
    #     batch_size=32,
    #     validation_split=0.2,
    #     callbacks=[
    #         tf.keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True),
    #         tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=5),
    #         tf.keras.callbacks.ModelCheckpoint('best_model.h5', save_best_only=True)
    #     ]
    # )
    
    # 5. Evaluate
    # test_loss, test_acc = model.evaluate([X_test_player, X_test_owner, X_test_draft], y_test)
    # print(f"Test accuracy: {test_acc:.4f}")
    
    # 6. Save final model
    save_path = manager.save_model(model, "production_model_v1", cache=True)
    
    return {
        "model_path": save_path,
        "status": "trained",
        # "metrics": {
        #     "final_accuracy": test_acc,
        #     "final_loss": test_loss,
        #     "epochs_trained": len(history.history['loss'])
        # }
    }


# ========== Example 5: Inference with Loaded Model ==========

def example_inference():
    """
    Load a trained Functional API model and make predictions.
    
    This is what your predict_draft_pick activity would use.
    """
    manager = get_tensorflow_model_manager()
    
    # Load model (from cache or disk)
    model = manager.load_model("production_model_v1")
    
    # Get model info
    info = manager.get_model_info("production_model_v1")
    print(f"\nModel info: {info}")
    
    # Prepare input features (pseudocode)
    # player_features = extract_player_features(available_players)
    # owner_features = extract_owner_preferences(owner_id)
    # draft_context = extract_draft_context(draft_state)
    
    # Example dummy data
    player_features = np.random.randn(1, 50)   # Batch of 1
    owner_features = np.random.randn(1, 20)
    draft_context = np.random.randn(1, 15)
    
    # Make prediction
    predictions = model.predict([player_features, owner_features, draft_context])
    
    # Get top 5 picks
    top_5_indices = np.argsort(predictions[0])[-5:][::-1]
    top_5_probs = predictions[0][top_5_indices]
    
    print("\n=== Top 5 Predictions ===")
    for idx, prob in zip(top_5_indices, top_5_probs):
        print(f"Player {idx}: {prob:.2%}")
    
    return {
        "top_pick_index": int(top_5_indices[0]),
        "top_pick_probability": float(top_5_probs[0]),
        "top_5_predictions": [
            {"player_index": int(idx), "probability": float(prob)}
            for idx, prob in zip(top_5_indices, top_5_probs)
        ]
    }


# ========== Example 6: Model Versioning ==========

def example_model_versioning():
    """
    Demonstrate how to version models per owner/league.
    
    Each owner can have their own personalized model trained on their
    historical draft data.
    """
    manager = get_tensorflow_model_manager()
    
    owner_id = "user_12345"
    league_id = "league_67890"
    
    # Build owner-specific model
    model = manager.build_draft_prediction_model(
        num_players=500,
        player_feature_dim=50,
        owner_feature_dim=20,
        draft_context_dim=15,
        model_name=f"owner_{owner_id}_model"
    )
    
    model = manager.compile_model(model)
    
    # Train on owner's historical data
    # ... training code ...
    
    # Save with versioned name
    model_name = f"owner_{owner_id}_league_{league_id}_v1"
    save_path = manager.save_model(model, model_name)
    
    print(f"\nSaved owner-specific model: {model_name}")
    print(f"Path: {save_path}")
    
    # Later, load the specific model
    owner_model = manager.load_model(model_name)
    
    return {"model_name": model_name, "path": save_path}


# ========== Usage Summary ==========

def print_usage_summary():
    """Print summary of all Functional API methods."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║       TensorFlow Functional API Methods - Usage Summary       ║
╚═══════════════════════════════════════════════════════════════╝

1. build_draft_prediction_model()
   - Standard multi-input model (player/owner/draft)
   - Best for: Basic draft prediction
   - Returns: Compiled model ready for training

2. build_multi_output_model()
   - Predicts pick + confidence + position preference
   - Best for: Richer predictions with multiple insights
   - Returns: Multi-output model

3. compile_model()
   - Add optimizer, loss function, metrics
   - Best for: Custom compilation settings
   - Returns: Compiled model

4. save_model()
   - Save to disk + optionally cache in memory
   - Best for: Persisting trained models
   - Returns: Save path

5. load_model()
   - Load from disk with caching
   - Best for: Loading pre-trained models for inference
   - Returns: Loaded model

6. build_custom_functional_model()
   - Flexible architecture with custom inputs/outputs
   - Best for: Experimental or non-standard architectures
   - Returns: Custom model

7. get_model_info()
   - Get metadata about cached model
   - Best for: Debugging, monitoring
   - Returns: Dict with model info

╔═══════════════════════════════════════════════════════════════╗
║                        Quick Start                             ║
╚═══════════════════════════════════════════════════════════════╝

from activities.clients.tensorflow_client import get_tensorflow_model_manager

# Build Functional API model
manager = get_tensorflow_model_manager()
model = manager.build_draft_prediction_model(
    num_players=500,
    player_feature_dim=50,
    owner_feature_dim=20,
    draft_context_dim=15
)

# Compile
model = manager.compile_model(model)

# Train
model.fit([player_X, owner_X, draft_X], y, epochs=50)

# Save
manager.save_model(model, "my_model_v1")

# Later: Load and predict
model = manager.load_model("my_model_v1")
predictions = model.predict([player_X, owner_X, draft_X])
""")


if __name__ == "__main__":
    print_usage_summary()
    
    # Run examples
    print("\n" + "="*70)
    print("Running Example 1: Basic Model")
    print("="*70)
    # example_basic_model()
    
    # Uncomment to run other examples:
    # example_multi_output_model()
    # example_custom_architecture()
    # example_training_pipeline()
    # example_inference()
    # example_model_versioning()
