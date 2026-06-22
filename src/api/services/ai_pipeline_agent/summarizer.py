"""
Tools for transforming query results into natural language answers.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from .prompts import ANSWER_STATIC_PROMPT


class AnswerSummarizer:
    """Use the Responses API to translate MongoDB results into natural language answers."""

    DEFAULT_COLUMNS = (
        "purchase_order_number",
        "requisition_number",
        "lpa_number",
        "department.normalized_name",
        "department.name",
        "supplier.name",
        "supplier.code",
        "supplier.zip_code",
        "item.name",
        "item.description",
        "item.quantity",
        "item.unit_price",
        "item.total_price",
        "dates.fiscal_year_start",
        "dates.fiscal_year",
        "dates.creation",
        "dates.purchase",
        "acquisition.type",
        "acquisition.method",
        "cal_card",
    )

    MAX_COLUMNS = 10
    MAX_ROWS = 5

    def __init__(self, client: OpenAI, model_name: str) -> None:
        self.client = client
        self.model_name = model_name

    def set_model_name(self, model_name: str) -> None:
        self.model_name = model_name

    def summarize(
        self,
        *,
        question: str,
        pipeline: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
        verbosity: str,
        previous_response_id: Optional[str],
    ) -> Tuple[str, Optional[str]]:
        """Return the answer text and new response id."""
        columns, compact_rows = self._compact_results(results, pipeline)

        prompt = ANSWER_STATIC_PROMPT + f"""

Question: {question}

Result Columns: {json.dumps(columns)}

Rows (showing {len(compact_rows)} of {len(results)} total):
{json.dumps(compact_rows, indent=2)}

Provide your answer:"""

        request: Dict[str, Any] = {
            "model": self.model_name,
            "input": prompt,
            "text": {"verbosity": "low"},  # Valid values: low, medium, high
            "max_output_tokens": 500,
        }

        if previous_response_id:
            request["previous_response_id"] = previous_response_id

        response = self.client.responses.create(**request)
        answer_text = getattr(response, "output_text", None) or "Results retrieved successfully"
        return answer_text, response.id

    def _compact_results(
        self,
        results: List[Dict[str, Any]],
        pipeline: List[Dict[str, Any]],
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        if not results:
            return [], []

        columns = self._extract_columns(results, pipeline)
        compact_rows: List[Dict[str, Any]] = []
        for row in results[: self.MAX_ROWS]:
            compact_row: Dict[str, Any] = {}
            for col in columns:
                if col == "_id":
                    compact_row["_id"] = row.get("_id")
                else:
                    compact_row[col] = self._get_nested_value(row, col)
            compact_rows.append(compact_row)
        return columns, compact_rows

    def _extract_columns(
        self,
        results: List[Dict[str, Any]],
        pipeline: List[Dict[str, Any]],
    ) -> List[str]:
        project = self._find_stage(pipeline, "$project")
        if project:
            keys = [key for key, value in project.items() if value and key != "_id"]
            if project.get("_id") not in (0, False):
                keys.insert(0, "_id")
            return keys[: self.MAX_COLUMNS]

        group = self._find_stage(pipeline, "$group")
        if group:
            keys = [key for key in group.keys() if key != "_id"]
            columns = ["_id"] + keys
            return columns[: self.MAX_COLUMNS]

        sample = results[0]
        columns = [
            path
            for path in self.DEFAULT_COLUMNS
            if self._get_nested_value(sample, path) is not None
        ]
        if not columns:
            columns = list(sample.keys())
        return columns[: self.MAX_COLUMNS]

    def _find_stage(
        self,
        pipeline: List[Dict[str, Any]],
        stage_name: str,
    ) -> Optional[Dict[str, Any]]:
        for stage in pipeline:
            if stage_name in stage:
                return stage[stage_name]
        return None

    def _get_nested_value(self, source: Dict[str, Any], path: str) -> Any:
        current: Any = source
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current
