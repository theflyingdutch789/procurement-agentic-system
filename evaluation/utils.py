"""
Shared helper functions for the evaluation toolkit.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence


def serialize_for_json(value: Any) -> Any:
    """Convert MongoDB/complex Python objects to JSON-safe structures."""
    if isinstance(value, list):
        return [serialize_for_json(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_for_json(val) for key, val in value.items()}
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # pragma: no cover - defensive
            pass
    type_name = type(value).__name__
    if type_name == "ObjectId":
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
    return value


def mean_or_zero(values: Sequence[float]) -> float:
    """Return the mean of a sequence or 0.0 if empty."""
    return sum(values) / len(values) if values else 0.0


def write_json(path: Path, payload: Any) -> None:
    """Persist structured payloads as formatted JSON."""
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
