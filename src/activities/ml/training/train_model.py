"""
Activity to train a TeamOwnerDraftModel on historical draft pick data.

Accepts pre-encoded training samples from prepare_owner_training_data and
runs a listwise cross-entropy training loop where the picked player is always
at index 0 among MAX_NEGATIVES + 1 candidates. This matches the pairwise
ranking inference pattern of TeamOwnerDraftModel.

Training uses the Adam optimiser. The model is saved to MODEL_PATH after every
completed run so the workflow can restart from the last checkpoint on retry.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from activities.clients.pytorch_client import get_pytorch_model_manager
    from activities.ml.models.team_owner_model import (
        DRAFT_CONTEXT_DIM,
        OWNER_PROFILE_DIM,
        PLAYER_FEATURE_DIM,
        TeamOwnerDraftModel,
    )


@dataclass
class TrainTeamOwnerModelParams:
    """
    Parameters for training a team owner draft prediction model.

    Args:
        model_name: Name/path key for the model (e.g. "owner_abc123_v1").
        training_samples: Encoded training samples from prepare_owner_training_data.
            Each sample contains "candidate_features", "context", and "target_idx".
        owner_profile: 26-dim owner profile float vector (OWNER_PROFILE_FEATURES).
        player_feature_dim: Per-player feature dimension (default 9).
        owner_profile_dim: Owner history profile dimension (default 26).
        draft_context_dim: Draft context dimension (default 8).
        personality_dim: Personality trait dimension (default 8).
        hidden_dim: Width of shared fusion layers (default 256).
        dropout_rate: Dropout probability (default 0.3).
        epochs: Number of full passes over training samples (default 50).
        learning_rate: Adam learning rate (default 0.001).
    """

    model_name: str
    training_samples: List[Dict[str, Any]]
    owner_profile: List[float]
    player_feature_dim: int = PLAYER_FEATURE_DIM
    owner_profile_dim: int = OWNER_PROFILE_DIM
    draft_context_dim: int = DRAFT_CONTEXT_DIM
    personality_dim: int = 8
    hidden_dim: int = 256
    dropout_rate: float = 0.3
    epochs: int = 50
    learning_rate: float = 0.001


@activity.defn(name="train_team_owner_model")
async def train_team_owner_model(input: TrainTeamOwnerModelParams) -> Dict[str, Any]:
    """
    Train or fine-tune a TeamOwnerDraftModel on historical draft picks.

    Loads the named model from MODEL_PATH if it exists, otherwise builds one with
    fresh weights. Runs a listwise cross-entropy training loop where the picked
    player is always at index 0 among the candidates. Saves the model after training.

    Args:
        input: TrainTeamOwnerModelParams with model_name, training samples, and hyperparameters.

    Returns:
        Dict[str, Any]: {"model_name": str, "model_path": str, "epochs_trained": int, "final_loss": float, "initial_loss": float, "num_samples": int}
    """
    import torch
    import torch.nn.functional as F

    pytorch = get_pytorch_model_manager()
    base_path = os.getenv("MODEL_PATH", "/app/models")
    model_path = str(Path(base_path) / f"{input.model_name}.pt")
    device = pytorch.get_device()

    # Filter samples that have at least one candidate player
    samples = [s for s in input.training_samples if s.get("candidate_features")]
    num_samples = len(samples)

    if num_samples == 0:
        print(f"No usable training samples for '{input.model_name}'; skipping training.")
        return {
            "model_name": input.model_name,
            "model_path": model_path,
            "epochs_trained": 0,
            "final_loss": 0.0,
            "initial_loss": 0.0,
            "num_samples": 0,
        }

    try:
        # Load existing model or build fresh
        if Path(model_path).exists():
            model = pytorch.load_model(
                input.model_name,
                model_class=TeamOwnerDraftModel,
                model_path=model_path,
                model_kwargs={
                    "player_feature_dim": input.player_feature_dim,
                    "owner_profile_dim": input.owner_profile_dim,
                    "draft_context_dim": input.draft_context_dim,
                    "personality_dim": input.personality_dim,
                    "hidden_dim": input.hidden_dim,
                    "dropout_rate": input.dropout_rate,
                },
            )
        else:
            model = pytorch.build_team_owner_model(
                player_feature_dim=input.player_feature_dim,
                owner_profile_dim=input.owner_profile_dim,
                draft_context_dim=input.draft_context_dim,
                personality_dim=input.personality_dim,
                hidden_dim=input.hidden_dim,
                dropout_rate=input.dropout_rate,
                model_name=input.model_name,
            )

        model.train()
        optimizer = pytorch.create_optimizer(model, "adam", input.learning_rate)

        # Pre-build the owner profile tensor (tiled per-sample in the loop)
        owner_profile_t = torch.tensor(
            input.owner_profile, dtype=torch.float32, device=device
        )  # (owner_profile_dim,)

        initial_loss = 0.0
        final_loss = 0.0

        for epoch in range(input.epochs):
            epoch_loss = 0.0
            valid_batches = 0

            for sample in samples:
                candidate_features: List[List[float]] = sample["candidate_features"]
                context_vec: List[float] = sample["context"]
                target_idx: int = sample["target_idx"]
                n = len(candidate_features)

                if n == 0:
                    continue

                # Build tensors for this pick
                player_t = torch.tensor(
                    candidate_features, dtype=torch.float32, device=device
                )  # (n, player_feature_dim)

                profile_t = owner_profile_t.unsqueeze(0).expand(
                    n, -1
                )  # (n, owner_profile_dim)

                ctx_t = torch.tensor(
                    context_vec, dtype=torch.float32, device=device
                ).unsqueeze(0).expand(n, -1)  # (n, draft_context_dim)

                # No personality during training — use neutral zeros so the base
                # history-driven path is trained without personality noise
                personality_t = torch.zeros(
                    n, input.personality_dim, dtype=torch.float32, device=device
                )  # (n, personality_dim)

                optimizer.zero_grad()

                pick_scores, _confidence, _pos_priority = model(
                    player_t, profile_t, ctx_t, personality_t, 0.0
                )
                logits = pick_scores.squeeze(1)  # (n,)

                target_t = torch.tensor(
                    target_idx, dtype=torch.long, device=device
                )
                loss = F.cross_entropy(logits.unsqueeze(0), target_t.unsqueeze(0))
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                valid_batches += 1

            if valid_batches > 0:
                avg_loss = epoch_loss / valid_batches
                if epoch == 0:
                    initial_loss = avg_loss
                final_loss = avg_loss
                if epoch % 10 == 0 or epoch == input.epochs - 1:
                    print(
                        f"[{input.model_name}] Epoch {epoch + 1}/{input.epochs} "
                        f"— avg_loss: {avg_loss:.4f}"
                    )

        # Save trained model to disk and refresh cache
        model.eval()
        saved_path = pytorch.save_model(
            model, input.model_name, save_path=model_path, cache=True
        )
        print(
            f"Saved trained model '{input.model_name}' → {saved_path} "
            f"(initial_loss={initial_loss:.4f}, final_loss={final_loss:.4f})"
        )

        return {
            "model_name": input.model_name,
            "model_path": saved_path,
            "epochs_trained": input.epochs,
            "final_loss": round(final_loss, 6),
            "initial_loss": round(initial_loss, 6),
            "num_samples": num_samples,
        }

    except Exception as e:
        print(f"Failed to train model '{input.model_name}': {str(e)}")
        raise
