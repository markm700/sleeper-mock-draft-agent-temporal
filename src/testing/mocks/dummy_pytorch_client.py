"""
Mock PyTorch client manager for testing Temporal ML activities.

Provides a stub implementation of PyTorchModelManager that records
method calls without requiring real model files on disk or GPU compute.

Real TeamOwnerDraftModel instances are used so that activities that run
gradient computations (e.g. train_team_owner_model) work correctly — only
disk-I/O operations are intercepted and stubbed out.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from typing import Any, Dict, List, Optional


class DummyPyTorchModelManager:
    """
    Mock manager for PyTorch model lifecycle operations.

    Records build, save, and load calls. Build operations return real
    TeamOwnerDraftModel instances (so gradient-based training tests work).
    Save operations are no-ops that track call arguments. Load either
    returns a cached model or raises FileNotFoundError, depending on
    whether the model was previously built/cached.

    Usage in tests::

        dummy_pytorch = DummyPyTorchModelManager()
        monkeypatch.setattr(
            "activities.ml.models.manage_model.get_pytorch_model_manager",
            lambda: dummy_pytorch,
        )
    """

    def __init__(self) -> None:
        self._models: Dict[str, nn.Module] = {}
        self.build_calls: List[Dict[str, Any]] = []
        self.save_calls: List[Dict[str, Any]] = []
        self.load_calls: List[Dict[str, Any]] = []
        self.evict_calls: List[str] = []

    # ------------------------------------------------------------------
    # Device
    # ------------------------------------------------------------------

    def get_device(self) -> torch.device:
        """Always return CPU for deterministic test behaviour."""
        return torch.device("cpu")

    # ------------------------------------------------------------------
    # Model building
    # ------------------------------------------------------------------

    def build_team_owner_model(
        self,
        player_feature_dim: int,
        owner_profile_dim: int,
        draft_context_dim: int,
        personality_dim: int = 8,
        num_positions: int = 6,
        hidden_dim: int = 256,
        dropout_rate: float = 0.3,
        model_name: str = "team_owner_draft_model",
    ) -> nn.Module:
        """Build a real TeamOwnerDraftModel and cache it under model_name."""
        from activities.ml.models.team_owner_model import TeamOwnerDraftModel

        self.build_calls.append(
            {
                "model_name": model_name,
                "player_feature_dim": player_feature_dim,
                "owner_profile_dim": owner_profile_dim,
                "draft_context_dim": draft_context_dim,
                "personality_dim": personality_dim,
                "hidden_dim": hidden_dim,
                "dropout_rate": dropout_rate,
            }
        )
        model = TeamOwnerDraftModel(
            player_feature_dim=player_feature_dim,
            owner_profile_dim=owner_profile_dim,
            draft_context_dim=draft_context_dim,
            personality_dim=personality_dim,
            num_positions=num_positions,
            hidden_dim=hidden_dim,
            dropout_rate=dropout_rate,
        )
        model = model.to(self.get_device())
        self._models[model_name] = model
        return model

    # ------------------------------------------------------------------
    # Model persistence (stubbed — no real I/O)
    # ------------------------------------------------------------------

    def save_model(
        self,
        model: nn.Module,
        model_name: str,
        save_path: Optional[str] = None,
        cache: bool = True,
        save_full_model: bool = False,
    ) -> str:
        """Record the save call and optionally cache; never touches the filesystem."""
        resolved_path = save_path or f"/tmp/test_models/{model_name}.pt"
        self.save_calls.append(
            {
                "model_name": model_name,
                "save_path": resolved_path,
                "cache": cache,
            }
        )
        if cache:
            self._models[model_name] = model
        return resolved_path

    def load_model(
        self,
        model_name: str,
        model_class: Optional[type] = None,
        model_path: Optional[str] = None,
        model_kwargs: Optional[Dict[str, Any]] = None,
    ) -> nn.Module:
        """Return a cached model or raise FileNotFoundError to simulate missing file."""
        self.load_calls.append(
            {
                "model_name": model_name,
                "model_path": model_path,
            }
        )
        if model_name in self._models:
            return self._models[model_name]
        raise FileNotFoundError(
            f"[DummyPyTorchModelManager] Model not found: {model_name}"
        )

    def unload_model(self, model_name: str) -> None:
        """Remove a model from cache (no-op if not cached)."""
        self.evict_calls.append(model_name)
        self._models.pop(model_name, None)

    # ------------------------------------------------------------------
    # Model introspection
    # ------------------------------------------------------------------

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Return parameter counts for a cached model, or an error dict."""
        if model_name not in self._models:
            return {"error": f"Model {model_name} not loaded"}
        model = self._models[model_name]
        total = sum(p.numel() for p in model.parameters())
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        return {
            "model_name": model_name,
            "device": "cpu",
            "total_params": total,
            "trainable_params": trainable,
            "is_training": model.training,
        }

    # ------------------------------------------------------------------
    # Optimiser / training helpers
    # ------------------------------------------------------------------

    def create_optimizer(
        self,
        model: nn.Module,
        optimizer_type: str = "adam",
        learning_rate: float = 0.001,
        **kwargs: Any,
    ) -> optim.Optimizer:
        """Return a real PyTorch optimizer (Adam/AdamW/SGD) for the given model."""
        opt_type = optimizer_type.lower()
        if opt_type == "adam":
            return optim.Adam(model.parameters(), lr=learning_rate, **kwargs)
        if opt_type == "adamw":
            return optim.AdamW(model.parameters(), lr=learning_rate, **kwargs)
        if opt_type == "sgd":
            return optim.SGD(model.parameters(), lr=learning_rate, **kwargs)
        raise ValueError(f"Unknown optimizer type: {optimizer_type}")
