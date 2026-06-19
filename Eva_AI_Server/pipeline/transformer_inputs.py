"""
Helpers for passing tokenizer outputs into Hugging Face models safely.

Some tokenizers (e.g. BertTokenizer) emit ``token_type_ids``, but DistilBERT
sequence classifiers do not accept that argument in ``forward()``.
"""
from __future__ import annotations

import inspect
from typing import Any, Dict, Mapping, MutableMapping

_FORWARD_PARAM_CACHE: Dict[int, frozenset[str]] = {}


def _forward_param_names(model: Any) -> frozenset[str]:
    model_id = id(model)
    cached = _FORWARD_PARAM_CACHE.get(model_id)
    if cached is not None:
        return cached

    params = frozenset(inspect.signature(model.forward).parameters.keys())
    _FORWARD_PARAM_CACHE[model_id] = params
    return params


def filter_model_inputs(
    model: Any,
    inputs: Mapping[str, Any],
) -> Dict[str, Any]:
    """Return only keys that ``model.forward`` accepts."""
    allowed = _forward_param_names(model)
    return {key: value for key, value in inputs.items() if key in allowed}


def pop_non_model_inputs(
    encoded: MutableMapping[str, Any],
    model: Any,
) -> Dict[str, Any]:
    """Remove unsupported keys in-place and return the batch for ``model(**batch)``."""
    allowed = _forward_param_names(model)
    drop_keys = [key for key in list(encoded.keys()) if key not in allowed]
    for key in drop_keys:
        encoded.pop(key, None)
    return dict(encoded)
