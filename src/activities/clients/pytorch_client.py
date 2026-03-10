"""
PyTorch client manager for Temporal activities.

Provides PyTorch engine, model loading, and model caching.
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
import torch
import torch.nn as nn

@dataclass
class PyTorchModelManager:
    """
    Singleton manager for PyTorch models.
    
    Caches loaded models to avoid repeated disk I/O and initialization overhead.
    Thread-safe for use across multiple activity executions.
    """
    
    _instance: Optional["PyTorchModelManager"] = None
    _models: Dict[str, nn.Module] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._configure_pytorch()
        return cls._instance
    
    @staticmethod
    def _configure_pytorch() -> None:
        """Configure PyTorch for production use."""
        # Check if CUDA is available
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            print(f"PyTorch configured with {device_count} GPU(s)")
            for i in range(device_count):
                print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        else:
            print("PyTorch running on CPU")
        
        # Set number of threads for CPU inference
        num_threads = int(os.getenv("PYTORCH_NUM_CPU_THREADS", "4"))
        torch.set_num_threads(num_threads)
        print(f"PyTorch CPU threads: {num_threads}")
    
    def get_device(self) -> torch.device:
        """Get the optimal device (CPU or CUDA)."""
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    def load_model(
        self, 
        model_name: str, 
        model_class: Optional[type] = None,
        model_path: Optional[str] = None,
        model_kwargs: Optional[Dict[str, Any]] = None
    ) -> nn.Module:
        """
        Load a PyTorch model with caching.
        
        Args:
            model_name: Unique identifier for the model
            model_class: Model class (required for first load)
            model_path: Path to saved model weights (.pt or .pth file)
            model_kwargs: Kwargs to pass to model constructor
        
        Returns:
            Loaded PyTorch model
        
        Example:
            >>> manager = get_pytorch_model_manager()
            >>> model = manager.load_model(
            ...     "draft_model_v1",
            ...     model_class=DraftPredictionModel,
            ...     model_kwargs={"num_players": 500, "player_dim": 50}
            ... )
        """
        # Return cached model if already loaded
        if model_name in self._models:
            print(f"Using cached model: {model_name}")
            return self._models[model_name]
        
        # Determine model path
        if model_path is None:
            base_path = os.getenv("MODEL_PATH", "/app/models")
            model_path = str(Path(base_path) / f"{model_name}.pt")
        
        # Load model
        try:
            print(f"Loading model from: {model_path}")
            
            if not Path(model_path).exists():
                raise FileNotFoundError(f"Model file not found: {model_path}")
            
            # Load state dict
            state_dict = torch.load(model_path, map_location=self.get_device())
            
            # Instantiate model if class provided
            if model_class is not None:
                model_kwargs = model_kwargs or {}
                model = model_class(**model_kwargs)
                model.load_state_dict(state_dict)
            else:
                # Assume state_dict contains full model (not recommended)
                model = state_dict
            
            # Move to device and set to eval mode
            device = self.get_device()
            model = model.to(device)
            model.eval()
            
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
            # Clear CUDA cache if using GPU
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print(f"Unloaded model: {model_name}")
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a cached model."""
        if model_name not in self._models:
            return {"error": f"Model {model_name} not loaded"}
        
        model = self._models[model_name]
        
        # Count parameters
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        return {
            "model_name": model_name,
            "device": str(next(model.parameters()).device),
            "total_params": total_params,
            "trainable_params": trainable_params,
            "is_training": model.training,
        }
    
    # ========== Model Building Methods ==========
    
    def build_draft_prediction_model(
        self,
        num_players: int,
        player_feature_dim: int,
        owner_feature_dim: int,
        draft_context_dim: int,
        hidden_layers: List[int] = [256, 128, 64],
        dropout_rate: float = 0.3,
        model_name: str = "draft_prediction_model"
    ) -> nn.Module:
        """
        Build a PyTorch model for draft pick prediction.
        
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
            PyTorch model ready for training
        
        Example:
            >>> manager = get_pytorch_model_manager()
            >>> model = manager.build_draft_prediction_model(
            ...     num_players=500,
            ...     player_feature_dim=50,
            ...     owner_feature_dim=20,
            ...     draft_context_dim=15
            ... )
            >>> # Train with multiple inputs
            >>> optimizer = torch.optim.Adam(model.parameters())
            >>> for epoch in range(50):
            ...     outputs = model(player_x, owner_x, draft_x)
            ...     loss = criterion(outputs, targets)
            ...     loss.backward()
            ...     optimizer.step()
        """
        from activities.ml.models.draft_prediction_model import DraftPredictionModel
        
        model = DraftPredictionModel(
            player_feature_dim=player_feature_dim,
            owner_feature_dim=owner_feature_dim,
            draft_context_dim=draft_context_dim,
            num_players=num_players,
            hidden_layers=hidden_layers,
            dropout_rate=dropout_rate
        )
        
        device = self.get_device()
        model = model.to(device)
        
        total_params = sum(p.numel() for p in model.parameters())
        print(f"Built PyTorch model: {model_name}")
        print(f"Total parameters: {total_params:,}")
        print(f"Device: {device}")
        
        return model
    
    def build_multi_output_model(
        self,
        num_players: int,
        player_feature_dim: int,
        owner_feature_dim: int,
        draft_context_dim: int,
        model_name: str = "multi_output_draft_model"
    ) -> nn.Module:
        """
        Build a PyTorch model with multiple outputs:
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
            PyTorch model with multiple outputs
        
        Example:
            >>> model = manager.build_multi_output_model(500, 50, 20, 15)
            >>> # Returns 3 outputs: pick_prob, confidence, position_pref
            >>> pick_prob, confidence, pos_pref = model(player_x, owner_x, draft_x)
        """
        from activities.ml.models.multi_output_model import MultiOutputDraftModel
        
        model = MultiOutputDraftModel(
            player_feature_dim=player_feature_dim,
            owner_feature_dim=owner_feature_dim,
            draft_context_dim=draft_context_dim,
            num_players=num_players
        )
        
        device = self.get_device()
        model = model.to(device)
        
        print(f"Built multi-output model: {model_name}")
        return model

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
        """
        Build a team-owner-centric draft prediction model.

        Each model instance is trained to represent a specific fantasy football
        team owner and predict which player *that owner* will draft. Personality
        traits can stochastically modulate predictions pick-to-pick.

        Uses a learning-to-rank architecture: all N candidate players are scored
        in a single forward pass (batch = n_candidates), with owner profile and
        personality tiled across all candidates. Caller applies softmax over the
        returned pick scores to get per-player pick probabilities.

        Model outputs per candidate:
        - pick_score  (n_candidates, 1) — raw affinity; softmax → pick probability
        - confidence  (n_candidates, 1) — sigmoid certainty score
        - position_priority (n_candidates, num_positions) — positional preference

        Args:
            player_feature_dim:  Per-player feature dimension (default: 9)
            owner_profile_dim:   Owner historical profile dimension (default: 26)
            draft_context_dim:   Draft context dimension (default: 8)
            personality_dim:     Number of personality traits (default: 8)
            num_positions:       Number of fantasy positions (default: 6)
            hidden_dim:          Width of shared fusion layers (default: 256)
            dropout_rate:        Dropout probability (default: 0.3)
            model_name:          Name for logging

        Returns:
            TeamOwnerDraftModel ready for training

        Example:
            >>> manager = get_pytorch_model_manager()
            >>> model = manager.build_team_owner_model(
            ...     player_feature_dim=9,
            ...     owner_profile_dim=26,
            ...     draft_context_dim=8,
            ... )
            >>> # Score N available players in one pass
            >>> n = len(available_players)
            >>> player_t = torch.tensor(player_features, ...)              # (n, 9)
            >>> profile_t = owner_profile_tensor.unsqueeze(0).expand(n, -1) # (n, 26)
            >>> ctx_t     = draft_ctx_tensor.unsqueeze(0).expand(n, -1)    # (n, 8)
            >>> traits_t  = personality_tensor.unsqueeze(0).expand(n, -1)  # (n, 8)
            >>>
            >>> model.eval()
            >>> with torch.no_grad():
            ...     # Random personality influence — simulates pick-by-pick variance
            ...     scores, conf, pos_prio, influence = (
            ...         model.predict_with_random_personality(
            ...             player_t, profile_t, ctx_t, traits_t
            ...         )
            ...     )
            >>> pick_probs = torch.softmax(scores.squeeze(1), dim=0)
            >>> top_idx = torch.argmax(pick_probs).item()
        """
        from activities.ml.models.team_owner_model import TeamOwnerDraftModel

        model = TeamOwnerDraftModel(
            player_feature_dim=player_feature_dim,
            owner_profile_dim=owner_profile_dim,
            draft_context_dim=draft_context_dim,
            personality_dim=personality_dim,
            num_positions=num_positions,
            hidden_dim=hidden_dim,
            dropout_rate=dropout_rate,
        )

        device = self.get_device()
        model = model.to(device)

        total_params = sum(p.numel() for p in model.parameters())
        print(f"Built TeamOwnerDraftModel: {model_name}")
        print(f"Total parameters: {total_params:,}")
        print(f"Device: {device}")

        return model

    def save_model(
        self,
        model: nn.Module,
        model_name: str,
        save_path: Optional[str] = None,
        cache: bool = True,
        save_full_model: bool = False
    ) -> str:
        """
        Save a PyTorch model to disk.
        
        Args:
            model: PyTorch model to save
            model_name: Name/identifier for the model
            save_path: Custom save path (default: MODEL_PATH env var)
            cache: Whether to cache the model in memory
            save_full_model: If True, save full model; else save state_dict (recommended)
        
        Returns:
            Path where model was saved
        
        Example:
            >>> model = manager.build_draft_prediction_model(...)
            >>> path = manager.save_model(model, "owner_123_v1")
            >>> # Later: model = manager.load_model("owner_123_v1", model_class=DraftPredictionModel)
        """
        if save_path is None:
            base_path = os.getenv("MODEL_PATH", "/app/models")
            save_path = str(Path(base_path) / f"{model_name}.pt")
        
        # Create directory if needed
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save model
        if save_full_model:
            torch.save(model, save_path)
        else:
            # Save state dict (recommended - more portable)
            torch.save(model.state_dict(), save_path)
        
        print(f"Saved model to: {save_path}")
        
        # Cache in memory
        if cache:
            self._models[model_name] = model
            print(f"Cached model: {model_name}")
        
        return save_path
    
    def create_optimizer(
        self,
        model: nn.Module,
        optimizer_type: str = "adam",
        learning_rate: float = 0.001,
        **kwargs
    ) -> torch.optim.Optimizer:
        """
        Create an optimizer for model training.
        
        Args:
            model: PyTorch model
            optimizer_type: Type of optimizer ('adam', 'sgd', 'adamw')
            learning_rate: Learning rate
            **kwargs: Additional optimizer parameters
        
        Returns:
            PyTorch optimizer
        
        Example:
            >>> optimizer = manager.create_optimizer(model, "adam", learning_rate=0.001)
        """
        optimizer_type = optimizer_type.lower()
        
        if optimizer_type == "adam":
            return torch.optim.Adam(model.parameters(), lr=learning_rate, **kwargs)
        elif optimizer_type == "adamw":
            return torch.optim.AdamW(model.parameters(), lr=learning_rate, **kwargs)
        elif optimizer_type == "sgd":
            return torch.optim.SGD(model.parameters(), lr=learning_rate, **kwargs)
        else:
            raise ValueError(f"Unknown optimizer type: {optimizer_type}")
    
    def create_loss_function(self, loss_type: str = "cross_entropy") -> nn.Module:
        """
        Create a loss function for training.
        
        Args:
            loss_type: Type of loss ('cross_entropy', 'bce', 'mse')
        
        Returns:
            PyTorch loss module
        
        Example:
            >>> criterion = manager.create_loss_function("cross_entropy")
        """
        loss_type = loss_type.lower()
        
        if loss_type == "cross_entropy":
            return nn.CrossEntropyLoss()
        elif loss_type == "bce":
            return nn.BCEWithLogitsLoss()
        elif loss_type == "mse":
            return nn.MSELoss()
        else:
            raise ValueError(f"Unknown loss type: {loss_type}")

    # ========== GPU Training Utilities ==========

    def create_grad_scaler(self) -> Optional[torch.cuda.amp.GradScaler]:
        """
        Create a gradient scaler for Automatic Mixed Precision (AMP) training.

        AMP uses float16 for most operations and float32 for precision-sensitive
        ones, cutting GPU memory usage roughly in half and increasing throughput
        by ~2x on Tensor Core GPUs (Volta+).

        Returns None on CPU — the training loop should skip scaling entirely.

        Usage pattern::

            scaler = manager.create_grad_scaler()
            for player_x, profile_x, ctx_x, traits_x, targets in dataloader:
                optimizer.zero_grad()
                with manager.autocast():
                    scores, conf, pos_prio = model(player_x, profile_x, ctx_x, traits_x)
                    loss = criterion(scores.squeeze(1), targets)
                if scaler is not None:
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    optimizer.step()

        Returns:
            GradScaler instance when GPU is available, None for CPU training.
        """
        if torch.cuda.is_available():
            print("Created GradScaler for mixed precision (AMP) GPU training")
            return torch.cuda.amp.GradScaler()
        print("CPU detected — GradScaler not created (full precision training)")
        return None

    @contextmanager
    def autocast(self) -> Generator:
        """
        Context manager for Automatic Mixed Precision (AMP) forward passes.

        Wraps ``torch.autocast`` for the active device. On CPU the context is a
        no-op (autocast is enabled only for CUDA).

        Use together with ``create_grad_scaler()`` for a complete AMP loop::

            with manager.autocast():
                outputs = model(inputs)
                loss = criterion(outputs, targets)
        """
        device_type = "cuda" if torch.cuda.is_available() else "cpu"
        with torch.autocast(device_type=device_type, enabled=torch.cuda.is_available()):
            yield

    def get_gpu_memory_info(self) -> Dict[str, Any]:
        """
        Return current GPU memory statistics for the active CUDA device.

        Useful for logging during training to detect OOM before it happens
        and to tune batch size.

        Returns:
            Dict containing device name, allocated/reserved/total/free memory
            in MB, and utilisation percentage. Returns ``{"gpu_available": False}``
            on CPU-only hosts.

        Example::

            info = manager.get_gpu_memory_info()
            print(f"GPU memory: {info['allocated_mb']:.0f} / {info['total_mb']:.0f} MB "
                  f"({info['utilization_pct']:.1f}%)")
        """
        if not torch.cuda.is_available():
            return {"device": "cpu", "gpu_available": False}

        idx = torch.cuda.current_device()
        allocated = torch.cuda.memory_allocated(idx)
        reserved = torch.cuda.memory_reserved(idx)
        total = torch.cuda.get_device_properties(idx).total_memory

        return {
            "device": f"cuda:{idx}",
            "gpu_available": True,
            "gpu_name": torch.cuda.get_device_name(idx),
            "allocated_mb": allocated / 1024 ** 2,
            "reserved_mb": reserved / 1024 ** 2,
            "total_mb": total / 1024 ** 2,
            "free_mb": (total - allocated) / 1024 ** 2,
            "utilization_pct": (allocated / total) * 100,
        }

    def clear_gpu_cache(self) -> None:
        """
        Release unused GPU memory back to the CUDA allocator.

        Call between training runs or after loading/unloading models to avoid
        fragmentation. Safe to call on CPU — it is a no-op.
        """
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print("GPU cache cleared")
        else:
            print("CPU Process - No GPU cache to clear")

    def get_dataloader_kwargs(self) -> Dict[str, Any]:
        """
        Return recommended ``DataLoader`` keyword arguments for the active device.

        ``pin_memory=True`` with ``non_blocking=True`` tensor transfers overlaps
        host-to-device copy with GPU compute, giving a ~10-20% throughput bump.
        ``num_workers`` is read from ``DATALOADER_NUM_WORKERS`` env var
        (default 4 for GPU, 0 for CPU to avoid multiprocessing overhead).

        Usage::

            dl = DataLoader(dataset, batch_size=64, **manager.get_dataloader_kwargs())

        Returns:
            Dict ready to unpack into ``torch.utils.data.DataLoader(...)``.
        """
        if torch.cuda.is_available():
            num_workers = int(os.getenv("DATALOADER_NUM_WORKERS", "4"))
            return {"pin_memory": True, "num_workers": num_workers}
        return {"num_workers": int(os.getenv("DATALOADER_NUM_WORKERS", "0"))}

    def move_batch_to_device(
        self,
        *tensors: torch.Tensor,
        non_blocking: bool = True,
    ) -> Tuple[torch.Tensor, ...]:
        """
        Move a variable number of tensors to the active device in one call.

        ``non_blocking=True`` initiates an asynchronous H2D transfer when the
        source tensor is pinned (from a pin_memory DataLoader), allowing the
        CPU to queue the next batch immediately.

        Args:
            *tensors:     One or more ``torch.Tensor`` objects to move.
            non_blocking: Use async transfer for pinned tensors (default True).

        Returns:
            Tuple of tensors on the active device, in the same order supplied.

        Example::

            player_t, profile_t, ctx_t, traits_t, labels_t = (
                manager.move_batch_to_device(
                    player_t, profile_t, ctx_t, traits_t, labels_t
                )
            )
        """
        device = self.get_device()
        return tuple(t.to(device, non_blocking=non_blocking) for t in tensors)


def get_pytorch_model_manager() -> PyTorchModelManager:
    """Get the single PyTorch model manager instance."""
    return PyTorchModelManager()
