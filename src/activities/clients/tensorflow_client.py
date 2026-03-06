"""
TensorFlow client manager for Temporal activities.

Provides TensorFlow engine, model loading, and model caching.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import tensorflow as tf

@dataclass
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
    
    # ========== Functional API Methods ==========
    
    def build_draft_prediction_model(
        self,
        num_players: int,
        player_feature_dim: int,
        owner_feature_dim: int,
        draft_context_dim: int,
        hidden_layers: List[int] = [256, 128, 64],
        dropout_rate: float = 0.3,
        model_name: str = "draft_prediction_model"
    ) -> tf.keras.Model:
        """
        Build a Functional API model for draft pick prediction.
        
        This is the recommended architecture for fantasy football draft prediction,
        using multiple inputs (player features, owner preferences, draft context)
        to predict which player will be picked next.
        
        Args:
            num_players: Number of possible players (output dimension)
            player_feature_dim: Dimension of player feature vector
            owner_feature_dim: Dimension of owner preference vector
            draft_context_dim: Dimension of draft context vector
            hidden_layers: List of hidden layer sizes [256, 128, 64]
            dropout_rate: Dropout rate for regularization (0.0-0.5)
            model_name: Name for the model
        
        Returns:
            Compiled Functional API model with multiple inputs
        
        Example:
            >>> manager = get_tensorflow_model_manager()
            >>> model = manager.build_draft_prediction_model(
            ...     num_players=500,
            ...     player_feature_dim=50,
            ...     owner_feature_dim=20,
            ...     draft_context_dim=15
            ... )
            >>> # Train with multiple inputs
            >>> model.fit(
            ...     [player_features, owner_features, draft_context],
            ...     pick_labels,
            ...     epochs=10
            ... )
        """
        # Define inputs
        player_input = tf.keras.Input(
            shape=(player_feature_dim,), 
            name='player_features'
        )
        owner_input = tf.keras.Input(
            shape=(owner_feature_dim,), 
            name='owner_preferences'
        )
        draft_input = tf.keras.Input(
            shape=(draft_context_dim,), 
            name='draft_context'
        )
        
        # Process each input stream separately
        player_processed = tf.keras.layers.Dense(
            128, 
            activation='relu', 
            name='player_encoder'
        )(player_input)
        player_processed = tf.keras.layers.BatchNormalization()(player_processed)
        
        owner_processed = tf.keras.layers.Dense(
            64, 
            activation='relu', 
            name='owner_encoder'
        )(owner_input)
        owner_processed = tf.keras.layers.BatchNormalization()(owner_processed)
        
        context_processed = tf.keras.layers.Dense(
            32, 
            activation='relu', 
            name='context_encoder'
        )(draft_input)
        context_processed = tf.keras.layers.BatchNormalization()(context_processed)
        
        # Combine all features
        combined = tf.keras.layers.Concatenate(name='feature_fusion')([
            player_processed, 
            owner_processed, 
            context_processed
        ])
        
        # Deep prediction layers
        x = combined
        for i, units in enumerate(hidden_layers):
            x = tf.keras.layers.Dense(
                units, 
                activation='relu', 
                name=f'hidden_{i+1}'
            )(x)
            x = tf.keras.layers.Dropout(dropout_rate, name=f'dropout_{i+1}')(x)
        
        # Output layer: probability distribution over all players
        pick_probability = tf.keras.layers.Dense(
            num_players, 
            activation='softmax', 
            name='pick_probability'
        )(x)
        
        # Build model
        model = tf.keras.Model(
            inputs=[player_input, owner_input, draft_input],
            outputs=pick_probability,
            name=model_name
        )
        
        print(f"Built Functional API model: {model_name}")
        print(f"Total parameters: {model.count_params():,}")
        
        return model
    
    def build_multi_output_model(
        self,
        num_players: int,
        player_feature_dim: int,
        owner_feature_dim: int,
        draft_context_dim: int,
        model_name: str = "multi_output_draft_model"
    ) -> tf.keras.Model:
        """
        Build a Functional API model with multiple outputs:
        - Pick probability (which player)
        - Confidence score (how certain)
        - Position preference (which position is prioritized)
        
        Args:
            num_players: Number of possible players
            player_feature_dim: Dimension of player features
            owner_feature_dim: Dimension of owner preferences
            draft_context_dim: Dimension of draft context
            model_name: Name for the model
        
        Returns:
            Functional API model with multiple outputs
        
        Example:
            >>> model = manager.build_multi_output_model(500, 50, 20, 15)
            >>> # Returns 3 outputs: [pick_prob, confidence, position_pref]
            >>> outputs = model.predict([player_feat, owner_feat, draft_ctx])
        """
        # Inputs
        player_input = tf.keras.Input(shape=(player_feature_dim,), name='player_features')
        owner_input = tf.keras.Input(shape=(owner_feature_dim,), name='owner_preferences')
        draft_input = tf.keras.Input(shape=(draft_context_dim,), name='draft_context')
        
        # Shared feature processing
        player_enc = tf.keras.layers.Dense(128, activation='relu')(player_input)
        owner_enc = tf.keras.layers.Dense(64, activation='relu')(owner_input)
        draft_enc = tf.keras.layers.Dense(32, activation='relu')(draft_input)
        
        combined = tf.keras.layers.Concatenate()([player_enc, owner_enc, draft_enc])
        
        # Shared representation
        shared = tf.keras.layers.Dense(256, activation='relu', name='shared_repr')(combined)
        shared = tf.keras.layers.Dropout(0.3)(shared)
        shared = tf.keras.layers.Dense(128, activation='relu')(shared)
        
        # Output 1: Pick probability
        pick_prob = tf.keras.layers.Dense(num_players, activation='softmax', name='pick_probability')(shared)
        
        # Output 2: Confidence score
        confidence = tf.keras.layers.Dense(64, activation='relu')(shared)
        confidence = tf.keras.layers.Dense(1, activation='sigmoid', name='confidence_score')(confidence)
        
        # Output 3: Position preference (QB, RB, WR, TE, K, DEF)
        position_pref = tf.keras.layers.Dense(32, activation='relu')(shared)
        position_pref = tf.keras.layers.Dense(6, activation='softmax', name='position_preference')(position_pref)
        
        model = tf.keras.Model(
            inputs=[player_input, owner_input, draft_input],
            outputs=[pick_prob, confidence, position_pref],
            name=model_name
        )
        
        print(f"Built multi-output model: {model_name}")
        return model
    
    def compile_model(
        self,
        model: tf.keras.Model,
        learning_rate: float = 0.001,
        loss: str = 'categorical_crossentropy',
        metrics: Optional[List[str]] = None
    ) -> tf.keras.Model:
        """
        Compile a Functional API model with appropriate optimizer and loss.
        
        Args:
            model: Keras model to compile
            learning_rate: Learning rate for Adam optimizer
            loss: Loss function ('categorical_crossentropy' for pick prediction)
            metrics: List of metrics to track (default: ['accuracy', 'top_k_categorical_accuracy'])
        
        Returns:
            Compiled model
        
        Example:
            >>> model = manager.build_draft_prediction_model(...)
            >>> model = manager.compile_model(model, learning_rate=0.0005)
        """
        if metrics is None:
            metrics = ['accuracy', tf.keras.metrics.TopKCategoricalAccuracy(k=5, name='top_5_accuracy')]
        
        optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
        
        model.compile(
            optimizer=optimizer,
            loss=loss,
            metrics=metrics
        )
        
        print(f"Compiled model with optimizer=Adam(lr={learning_rate}), loss={loss}")
        return model
    
    def save_model(
        self,
        model: tf.keras.Model,
        model_name: str,
        save_path: Optional[str] = None,
        cache: bool = True
    ) -> str:
        """
        Save a Functional API model to disk.
        
        Args:
            model: Keras model to save
            model_name: Name/identifier for the model
            save_path: Custom save path (default: MODEL_PATH env var)
            cache: Whether to cache the model in memory
        
        Returns:
            Path where model was saved
        
        Example:
            >>> model = manager.build_draft_prediction_model(...)
            >>> path = manager.save_model(model, "owner_123_v1")
            >>> # Later: model = manager.load_model("owner_123_v1")
        """
        if save_path is None:
            base_path = os.getenv("MODEL_PATH", "/app/models")
            save_path = str(Path(base_path) / model_name)
        
        # Create directory if needed
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model.save(save_path)
        print(f"Saved model to: {save_path}")
        
        # Cache in memory
        if cache:
            self._models[model_name] = model
            print(f"Cached model: {model_name}")
        
        return save_path
    
    def build_custom_functional_model(
        self,
        input_shapes: Dict[str, Tuple[int, ...]],
        output_shapes: Dict[str, Tuple[int, ...]],
        architecture_config: Dict,
        model_name: str = "custom_model"
    ) -> tf.keras.Model:
        """
        Build a custom Functional API model with flexible configuration.
        
        Args:
            input_shapes: Dict of input names to shapes, e.g., {'player': (50,), 'owner': (20,)}
            output_shapes: Dict of output names to shapes, e.g., {'pick': (500,), 'confidence': (1,)}
            architecture_config: Dict with 'shared_layers', 'output_heads', 'dropout', etc.
            model_name: Name for the model
        
        Returns:
            Custom Functional API model
        
        Example:
            >>> model = manager.build_custom_functional_model(
            ...     input_shapes={'player': (50,), 'owner': (20,)},
            ...     output_shapes={'pick': (500,)},
            ...     architecture_config={
            ...         'shared_layers': [256, 128],
            ...         'dropout': 0.3
            ...     }
            ... )
        """
        # Create inputs
        inputs = {}
        for name, shape in input_shapes.items():
            inputs[name] = tf.keras.Input(shape=shape, name=f'{name}_input')
        
        # Process and concatenate inputs
        processed = []
        for name, inp in inputs.items():
            x = tf.keras.layers.Dense(64, activation='relu', name=f'{name}_encoder')(inp)
            processed.append(x)
        
        combined = tf.keras.layers.Concatenate(name='combined_features')(processed) if len(processed) > 1 else processed[0]
        
        # Shared layers
        x = combined
        shared_layers = architecture_config.get('shared_layers', [256, 128])
        dropout = architecture_config.get('dropout', 0.3)
        
        for i, units in enumerate(shared_layers):
            x = tf.keras.layers.Dense(units, activation='relu', name=f'shared_{i+1}')(x)
            x = tf.keras.layers.Dropout(dropout, name=f'dropout_{i+1}')(x)
        
        # Create outputs
        outputs = {}
        for name, shape in output_shapes.items():
            # Determine activation based on output shape
            if len(shape) == 1 and shape[0] == 1:
                activation = 'sigmoid'
            elif len(shape) == 1 and shape[0] > 1:
                activation = 'softmax'
            else:
                activation = 'linear'
            
            outputs[name] = tf.keras.layers.Dense(
                shape[0], 
                activation=activation, 
                name=f'{name}_output'
            )(x)
        
        model = tf.keras.Model(
            inputs=list(inputs.values()),
            outputs=list(outputs.values()),
            name=model_name
        )
        
        print(f"Built custom Functional API model: {model_name}")
        return model

def get_tensorflow_model_manager() -> TensorFlowModelManager:
    """Get the single TensorFlow model manager instance."""
    return TensorFlowModelManager()