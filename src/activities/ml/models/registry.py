"""
Registry and factory for DraftModel backends, keyed by a stable model_type string.

Centralizes model selection for building/training a *new* model can choose type 
instead of hardcoding a class at the call site.

Note: joblib deserialization restores the exact class and does not consult the model registry.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, TypeVar

from activities.ml.models.model_interface import DraftModel

_T = TypeVar("_T", bound=type)

# Maps model_type -> callable that returns a DraftModel-conforming instance.
_REGISTRY: Dict[str, Callable[..., DraftModel]] = {}


def register_model(model_type: str) -> Callable[[_T], _T]:
    """
    Class decorator that registers a DraftModel implementation under a stable key.

    Args:
        model_type: Unique identifier for the backend, e.g. "TeamOwnerDraftModel".
            Should match the ``model_type`` reported by the model's ``get_config()``.

    Returns:
        The class decorator, which returns the class unchanged.

    Raises:
        ValueError: If ``model_type`` is already registered.
    """

    def _decorator(cls: _T) -> _T:
        if model_type in _REGISTRY:
            raise ValueError(
                f"model_type '{model_type}' is already registered to "
                f"{_REGISTRY[model_type].__name__}"
            )
        _REGISTRY[model_type] = cls
        return cls

    return _decorator


def create_model(model_type: str, **kwargs: Any) -> DraftModel:
    """
    Instantiate a registered DraftModel backend by key.

    Args:
        model_type: Registered backend identifier.
        **kwargs: Constructor arguments forwarded to the backend.

    Returns:
        DraftModel: A conforming model instance.

    Raises:
        ValueError: If ``model_type`` is not registered.
    """
    try:
        factory = _REGISTRY[model_type]
    except KeyError:
        raise ValueError(
            f"Unknown model_type '{model_type}'. "
            f"Registered backends: {available_models()}"
        )
    return factory(**kwargs)


def available_models() -> List[str]:
    """Return the sorted list of registered model_type keys."""
    return sorted(_REGISTRY)