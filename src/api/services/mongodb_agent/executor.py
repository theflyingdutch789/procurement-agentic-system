"""
Execution helpers for MongoDB aggregation pipelines.
"""

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from bson import ObjectId
from pymongo.errors import PyMongoError


class MongoDBQueryExecutor:
    """Executes validated MongoDB aggregation pipelines."""

    def __init__(self, collection, max_results: int = 100):
        self.collection = collection
        self.max_results = max_results
        self.logger = logging.getLogger(__name__)

    def execute_aggregation(
        self,
        pipeline: List[Dict[str, Any]],
        limit: Optional[int] = None,
    ) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        Execute an aggregation pipeline.

        Returns:
            Tuple of (success, results_or_error_message)
        """
        try:
            limit = limit or self.max_results
            has_limit = any("$limit" in stage for stage in pipeline)
            if not has_limit:
                pipeline.append({"$limit": limit})

            start_time = datetime.now()
            results = list(self.collection.aggregate(pipeline, maxTimeMS=30000))
            execution_time = (datetime.now() - start_time).total_seconds()

            self.logger.info(
                "Query executed in %.2fs, returned %d results",
                execution_time,
                len(results),
            )

            return True, self._serialize_results(results)

        except PyMongoError as exc:
            error_msg = f"Query execution failed: {exc}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as exc:  # pragma: no cover - safety net
            error_msg = f"Unexpected error during execution: {exc}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _serialize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
