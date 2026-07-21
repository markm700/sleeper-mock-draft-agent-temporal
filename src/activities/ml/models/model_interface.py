"""
Structural interface for draft prediction models.

Defines a Protocol that every model managed by the model-management workflow must
satisfy. Using structural typing (typing.Protocol) instead of an abstract base
class decouples the management and prediction activities from the concrete
``TeamOwnerDraftModel`` implementation: any object exposing the required
attributes and methods conforms, so alternative model backends can be built,
persisted, inspected, and scored through the same activities without subclassing
a shared base.

The interface is intentionally minimal and backend-agnostic — it excludes
implementation details such as the underlying LightGBM ``booster`` so that a
different backend (e.g. a neural network) can satisfy it just as well.
"""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class DraftModel(Protocol):
    """
    Structural interface for an owner draft prediction model via Protocol.

    Any object exposing these attributes and methods satisfies the interface —
    no explicit subclassing is required. Marked ``runtime_checkable`` so
    activities can perform lightweight ``isinstance()`` conformance checks; note
    that runtime checks verify *presence* of the members only, not their
    signatures, so treat them as a guardrail rather than full validation.
    """

    player_feature_dim: int
    owner_profile_dim: int
    draft_context_dim: int
    personality_dim: int
    input_dim: int

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict which candidate players are likely to be chosen.

        Args:
            X: (n_candidates, input_dim) feature matrix.

        Returns:
            np.ndarray: (n_candidates,) raw scores; apply softmax for probabilities.
        """
        ...

    def get_config(self) -> Dict[str, Any]:
        """Return a JSON-serialisable description of the model's architecture/state."""
        ...
