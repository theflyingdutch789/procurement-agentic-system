"""Execution helpers for MongoDB aggregation pipelines."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pymongo.errors import PyMongoError

from ..shared.mongo_serialization import serialize_mongo_results


class QueryExecutor:
    """Executes validated MongoDB aggregation pipelines."""

    def __init__(self, collection, max_results: int = 100):
        self.collection = collection
        self.max_results = max_results
        self.logger = logging.getLogger(__name__)

    def execute(
        self,
        pipeline: List[Dict[str, Any]],
        limit: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], float]:
        limit = limit or self.max_results
        has_limit = any("$limit" in stage for stage in pipeline)
        if not has_limit:
            pipeline = list(pipeline) + [{"$limit": limit}]

        start_time = datetime.now()
        try:
            results = list(self.collection.aggregate(pipeline, maxTimeMS=30000))
        except PyMongoError as exc:
            raise RuntimeError(f"Query execution failed: {exc}") from exc

        execution_time = (datetime.now() - start_time).total_seconds()
        self.logger.info("Query executed in %.2fs, returned %d results", execution_time, len(results))

        return serialize_mongo_results(results), execution_time
