"""Validation logic for intent and pipelines."""

from typing import Any, Dict, List, Optional, Tuple

from .models.intent import QueryAction, QueryIntent


class QueryValidator:
    """Validate intents and pipelines before execution."""

    MAX_LIMIT = 1000
    DANGEROUS_OPERATORS = {"$where", "$function", "$accumulator"}

    def validate_intent(self, intent: QueryIntent) -> Tuple[bool, Optional[str]]:
        if intent.is_ambiguous:
            return False, f"Ambiguous query: {intent.ambiguity_reason}"

        if intent.limit > self.MAX_LIMIT:
            return False, f"Limit exceeds maximum ({self.MAX_LIMIT})"

        action = intent.action
        if isinstance(action, str):
            action = QueryAction(action)

        if action in {QueryAction.TOP_N, QueryAction.BOTTOM_N}:
            if not intent.metric and not intent.group_by:
                return False, "Top/bottom queries require a metric or group_by"

        if action in {QueryAction.AGGREGATE, QueryAction.COMPARE} and not intent.group_by:
            return False, "Aggregate/compare actions require group_by"

        if intent.group_by_secondary and not intent.group_by:
            return False, "group_by_secondary requires group_by"

        if intent.group_by_secondary and intent.group_by_secondary == intent.group_by:
            return False, "group_by_secondary must differ from group_by"

        return True, None

    def validate_pipeline(self, pipeline: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        if not pipeline:
            return False, "Empty pipeline"

        pipeline_str = str(pipeline)
        for op in self.DANGEROUS_OPERATORS:
            if op in pipeline_str:
                return False, f"Dangerous operator not allowed: {op}"

        last_stage = pipeline[-1]
        if "$limit" not in last_stage and "$count" not in last_stage:
            return False, "Pipeline must have $limit or $count"

        return True, None
