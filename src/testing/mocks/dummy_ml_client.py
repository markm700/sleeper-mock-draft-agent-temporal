"""
Mock ML model manager for testing Temporal ML activities.

Provides a stub implementation of MLModelManager that records method calls
without requiring real model files on disk. Uses real TeamOwnerDraftModel
instances so that activities running LightGBM training work correctly — only
disk-I/O operations are intercepted and stubbed out.

Usage in tests::

    dummy_ml = DummyMLModelManager()
    monkeypatch.setattr(
        "activities.ml.models.manage_model.get_ml_model_manager",
        lambda: dummy_ml,
    )
"""

from typing import Any, Dict, List, Optional


class DummyMLModelManager:
    """
    Mock manager for ML model lifecycle operations.

    Records build, save, and load calls. Returned models are real
    TeamOwnerDraftModel instances backed by LightGBM so that training
    tests can exercise the full code path. Save operations are no-ops
    that track call arguments.
    """

    def __init__(self) -> None:
        self._models: Dict[str, Any] = {}
        self.save_calls: List[Dict[str, Any]] = []
        self.load_calls: List[Dict[str, Any]] = []
        self.close_calls: int = 0

    def load_model(
        self,
        model_name: str,
        model_path: Optional[str] = None,
    ) -> Any:
        """Return a cached model or raise FileNotFoundError."""
        self.load_calls.append({"model_name": model_name, "model_path": model_path})
        if model_name in self._models:
            return self._models[model_name]
        raise FileNotFoundError(f"[DummyMLModelManager] Model not found: {model_name}")

    def save_model(
        self,
        model: Any,
        model_name: str,
        save_path: Optional[str] = None,
        cache: bool = True,
    ) -> str:
        """Record the save call and optionally cache; never touches the filesystem."""
        resolved_path = save_path or f"/tmp/test_models/{model_name}.joblib"
        self.save_calls.append(
            {"model_name": model_name, "save_path": resolved_path, "cache": cache}
        )
        if cache:
            self._models[model_name] = model
        return resolved_path

    def unload_model(self, model_name: str) -> None:
        """Remove a model from cache (no-op if not cached)."""
        self._models.pop(model_name, None)

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Return basic info for a cached model, or an error dict."""
        if model_name not in self._models:
            return {"error": f"Model {model_name} not loaded"}
        model = self._models[model_name]
        return {
            "model_name": model_name,
            "model_type": type(model).__name__,
        }

    def close(self) -> None:
        """Record the close call and clear the model cache."""
        self.close_calls += 1
        self._models.clear()
