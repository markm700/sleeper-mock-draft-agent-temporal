"""
ML model manager for Temporal activities.

Provides model loading, saving, and caching using joblib serialisation.
Replaces the previous PyTorch-based manager with a lightweight scikit-learn /
LightGBM compatible implementation.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import joblib


class MLModelManager:
    """
    Singleton manager for ML models (scikit-learn, LightGBM).

    Caches loaded models to avoid repeated disk I/O across activity executions.
    """

    _instance: Optional["MLModelManager"] = None
    _models: Dict[str, Any] = {}

    def __new__(cls) -> "MLModelManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            print("MLModelManager initialised (scikit-learn / LightGBM)")
        return cls._instance

    def load_model(self, model_name: str, model_path: Optional[str] = None) -> Any:
        """
        Load a model from disk with caching.

        Args:
            model_name: Unique identifier for the model.
            model_path: Path to the serialised model file. Defaults to MODEL_PATH/<model_name>.joblib.

        Returns:
            The deserialised model object.
        """
        if model_name in self._models:
            print(f"Using cached model: {model_name}")
            return self._models[model_name]

        if model_path is None:
            base_path = os.getenv("MODEL_PATH", "/app/models")
            model_path = str(Path(base_path) / f"{model_name}.joblib")

        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        print(f"Loading model from: {model_path}")
        model = joblib.load(model_path)
        self._models[model_name] = model
        print(f"Successfully loaded and cached model: {model_name}")
        return model

    def save_model(
        self,
        model: Any,
        model_name: str,
        save_path: Optional[str] = None,
        cache: bool = True,
    ) -> str:
        """
        Save a model to disk using joblib.

        Args:
            model: The model object to persist.
            model_name: Unique identifier for the model.
            save_path: Custom save path. Defaults to MODEL_PATH/<model_name>.joblib.
            cache: Whether to keep the model in the in-memory cache.

        Returns:
            The path where the model was saved.
        """
        if save_path is None:
            base_path = os.getenv("MODEL_PATH", "/app/models")
            save_path = str(Path(base_path) / f"{model_name}.joblib")

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, save_path)
        print(f"Saved model to: {save_path}")

        if cache:
            self._models[model_name] = model
            print(f"Cached model: {model_name}")

        return save_path

    def unload_model(self, model_name: str) -> None:
        """Remove a model from the in-memory cache."""
        if model_name in self._models:
            del self._models[model_name]
            print(f"Unloaded model: {model_name}")

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Return information about a cached model."""
        if model_name not in self._models:
            return {"error": f"Model {model_name} not loaded"}

        model = self._models[model_name]
        return {
            "model_name": model_name,
            "model_type": type(model).__name__,
        }

    def close(self) -> None:
        """Clear all cached models and reset the singleton."""
        model_names = list(self._models.keys())
        print(f"MLModelManager shutdown: unloading {len(model_names)} cached model(s)...")
        self._models.clear()
        MLModelManager._instance = None
        print("MLModelManager closed")


def get_ml_model_manager() -> MLModelManager:
    """Get the single ML model manager instance."""
    return MLModelManager()
