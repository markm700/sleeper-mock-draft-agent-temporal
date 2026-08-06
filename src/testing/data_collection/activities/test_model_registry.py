"""
Tests for the DraftModel factory/registry (activities/ml/models/registry.py).

Covers registration, factory instantiation, duplicate/unknown error handling, and
the registration side effect that makes TeamOwnerDraftModel resolvable by name.

The ``_REGISTRY`` mapping is module-global, so tests that mutate it (registering
temporary backends, asserting duplicate errors) use the ``clean_registry`` fixture
to snapshot and restore it, keeping tests independent.
"""

from typing import Any, Dict

import numpy as np
import pytest

from activities.ml.models import registry
from activities.ml.models.model_interface import DraftModel
from activities.ml.models.registry import (
    available_models,
    create_model,
    register_model,
)


@pytest.fixture
def clean_registry():
    """Snapshot ``_REGISTRY`` and restore it after the test to avoid pollution."""
    saved = dict(registry._REGISTRY)
    try:
        yield
    finally:
        registry._REGISTRY.clear()
        registry._REGISTRY.update(saved)


class _FakeModel:
    """Minimal DraftModel-conforming backend used to exercise the registry."""

    def __init__(
        self,
        player_feature_dim: int = 2,
        owner_profile_dim: int = 3,
        draft_context_dim: int = 4,
        personality_dim: int = 5,
    ) -> None:
        self.player_feature_dim = player_feature_dim
        self.owner_profile_dim = owner_profile_dim
        self.draft_context_dim = draft_context_dim
        self.personality_dim = personality_dim
        self.input_dim = (
            player_feature_dim + owner_profile_dim + draft_context_dim + personality_dim
        )

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.zeros(len(X))

    def get_config(self) -> Dict[str, Any]:
        return {"model_type": "_FakeModel", "input_dim": self.input_dim}


# ---------------------------------------------------------------------------
# available_models / built-in registration side effect
# ---------------------------------------------------------------------------

def test_team_owner_model_is_registered() -> None:
    """Importing the models package registers TeamOwnerDraftModel by name."""
    assert "TeamOwnerDraftModel" in available_models()


def test_available_models_is_sorted() -> None:
    """available_models() returns keys in sorted order."""
    models = available_models()
    assert models == sorted(models)


# ---------------------------------------------------------------------------
# create_model — happy path
# ---------------------------------------------------------------------------

def test_create_model_builds_conforming_team_owner_model() -> None:
    """create_model resolves the default backend to a conforming DraftModel."""
    model = create_model("TeamOwnerDraftModel")

    assert isinstance(model, DraftModel)
    assert type(model).__name__ == "TeamOwnerDraftModel"


def test_create_model_forwards_kwargs_to_constructor() -> None:
    """create_model forwards **kwargs, so input_dim reflects the requested dims."""
    model = create_model(
        "TeamOwnerDraftModel",
        player_feature_dim=11,
        owner_profile_dim=26,
        draft_context_dim=8,
        personality_dim=8,
    )

    assert model.input_dim == 11 + 26 + 8 + 8


# ---------------------------------------------------------------------------
# create_model — error handling
# ---------------------------------------------------------------------------

def test_create_model_unknown_type_raises_value_error() -> None:
    """An unregistered model_type raises ValueError naming the available backends."""
    with pytest.raises(ValueError) as exc_info:
        create_model("NoSuchModel")

    message = str(exc_info.value)
    assert "NoSuchModel" in message
    # The error should surface the registered backends to aid debugging.
    assert "TeamOwnerDraftModel" in message


# ---------------------------------------------------------------------------
# register_model — decorator behaviour
# ---------------------------------------------------------------------------

def test_register_model_makes_backend_creatable(clean_registry) -> None:
    """A freshly registered backend is resolvable via create_model."""
    register_model("_FakeModel")(_FakeModel)

    assert "_FakeModel" in available_models()

    model = create_model("_FakeModel", player_feature_dim=1)
    assert isinstance(model, _FakeModel)
    assert model.player_feature_dim == 1


def test_register_model_duplicate_raises_value_error(clean_registry) -> None:
    """Registering the same model_type twice raises ValueError."""
    register_model("_DupModel")(_FakeModel)

    with pytest.raises(ValueError):
        register_model("_DupModel")(_FakeModel)


def test_register_model_returns_class_unchanged(clean_registry) -> None:
    """The decorator returns the class it wraps (usable as a normal decorator)."""

    @register_model("_DecoratedModel")
    class _Decorated(_FakeModel):
        pass

    assert _Decorated.__name__ == "_Decorated"
    assert isinstance(create_model("_DecoratedModel"), _Decorated)
