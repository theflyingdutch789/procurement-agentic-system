"""Shared serialization helpers for MongoDB results."""

import math
from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId


def serialize_mongo_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Serialize MongoDB results to JSON-compatible format."""

    def serialize(value: Any) -> Any:
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, float):
            if math.isnan(value):
                return None
            if math.isinf(value):
                return "Infinity" if value > 0 else "-Infinity"
            return value
        if isinstance(value, dict):
            return {k: serialize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [serialize(item) for item in value]
        return value

    return [serialize(doc) for doc in results]
