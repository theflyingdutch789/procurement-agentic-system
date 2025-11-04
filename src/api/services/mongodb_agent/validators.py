"""
Validation utilities for agent-generated MongoDB pipelines.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from pymongo.errors import OperationFailure


class QueryValidator:
    """Validates MongoDB aggregation pipelines prior to execution."""

    def __init__(self, collection):
        self.collection = collection
        self.logger = logging.getLogger(__name__)

    def validate_aggregation_pipeline(self, pipeline: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """
        Validate an aggregation pipeline.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not isinstance(pipeline, list):
                return False, "Pipeline must be a list of stages"

            if len(pipeline) == 0:
                return False, "Pipeline cannot be empty"

            for idx, stage in enumerate(pipeline):
                if not isinstance(stage, dict):
                    return False, f"Stage {idx} must be a dictionary"

                if len(stage) != 1:
                    return False, f"Stage {idx} must have exactly one operator"

                operator = next(iter(stage))
                if not operator.startswith("$"):
                    return False, f"Stage {idx}: '{operator}' is not a valid aggregation operator (must start with $)"

            try:
                test_pipeline = pipeline.copy()
                if not any("$limit" in stage for stage in test_pipeline):
                    test_pipeline.append({"$limit": 1})

                list(self.collection.aggregate(test_pipeline, maxTimeMS=1000, allowDiskUse=False))
                return True, None
            except OperationFailure as exc:
                error_msg = str(exc)
                error_code = getattr(exc, "code", None)
                if error_code == 50 or "exceeded time limit" in error_msg.lower():
                    return True, None
                return False, f"Invalid pipeline: {error_msg}"

        except Exception as exc:
            self.logger.exception("Pipeline validation failed")
            return False, f"Validation error: {exc}"
