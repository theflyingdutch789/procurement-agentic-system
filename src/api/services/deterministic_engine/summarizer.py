"""AI summarizer for query results."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from .models.intent import QueryAction, QueryIntent


SUMMARY_PROMPT = """You are a helpful assistant that converts database query results into clear, natural language answers.

Instructions:
- If the user asked for a specific number (e.g., "top 10"), show all of those results in your answer
- Format results in a numbered list when presenting multiple items
- Be direct and accurate
- Avoid mentioning internal implementation details
"""


class ResponseSummarizer:
    """Summarize MongoDB results into natural language."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def set_model_name(self, model: str) -> None:
        self.model = model

    def summarize(
        self,
        question: str,
        results: List[Dict[str, Any]],
        intent: QueryIntent,
        *,
        verbosity: str = "medium",
        previous_response_id: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        deterministic_answer = self._summarize_deterministic(results, intent)
        if deterministic_answer is not None:
            return deterministic_answer, None

        max_results_for_prompt = 20
        limited_results = results[:max_results_for_prompt]

        prompt = (
            SUMMARY_PROMPT
            + f"\nQuestion: {question}\n"
            + f"\nIntent: {intent.model_dump()}\n"
            + f"\nResults (showing {len(limited_results)} of {len(results)} total):\n"
            + json.dumps(limited_results, indent=2)
            + "\n\nProvide your answer:"
        )

        request: Dict[str, Any] = {
            "model": self.model,
            "input": prompt,
            "text": {"verbosity": verbosity},
            "max_output_tokens": 1000,
        }

        if previous_response_id:
            request["previous_response_id"] = previous_response_id

        response = self.client.responses.create(**request)
        answer_text = getattr(response, "output_text", None) or "Results retrieved successfully"
        return answer_text, response.id

    def _summarize_deterministic(
        self, results: List[Dict[str, Any]], intent: QueryIntent
    ) -> Optional[str]:
        action = intent.action
        if isinstance(action, str):
            action = QueryAction(action)

        if action == QueryAction.COUNT:
            count = 0
            if results:
                count = results[0].get("count", 0)
            return f"Total count: {count}"

        if action == QueryAction.SINGLE_VALUE:
            value = None
            if results:
                value = results[0].get("value")
            return f"Total value: {value}" if value is not None else "Total value: 0"

        if action in {QueryAction.TOP_N, QueryAction.BOTTOM_N} and not intent.group_by and not intent.group_by_secondary:
            return self._summarize_ranked_list(results, intent)

        if action in {QueryAction.TOP_N, QueryAction.BOTTOM_N, QueryAction.AGGREGATE, QueryAction.COMPARE, QueryAction.TREND}:
            if not results:
                return "No results found."
            lines = []
            for idx, row in enumerate(results, 1):
                label = row.get("_id")
                value = row.get("value")
                if isinstance(label, dict):
                    primary = label.get("primary")
                    secondary = label.get("secondary")
                    label = f"{primary} / {secondary}" if secondary is not None else primary
                lines.append(f"{idx}. {label}: {value}")
            return "\n".join(lines)

        if action == QueryAction.LIST:
            if not results:
                return "No results found."
            lines = []
            for idx, row in enumerate(results, 1):
                label = self._pick_label(row)
                metric_value = self._metric_value(row, intent)
                if metric_value is not None:
                    lines.append(f"{idx}. {label} — ${metric_value}")
                else:
                    lines.append(f"{idx}. {label}")
            return "\n".join(lines)

        return None

    def _summarize_ranked_list(
        self, results: List[Dict[str, Any]], intent: QueryIntent
    ) -> str:
        if not results:
            return "No results found."
        lines = []
        for idx, row in enumerate(results, 1):
            label = self._pick_label(row)
            metric_value = self._metric_value(row, intent)
            if metric_value is not None:
                lines.append(f"{idx}. {label} — ${metric_value}")
            else:
                lines.append(f"{idx}. {label}")
        return "\n".join(lines)

    def _pick_label(self, row: Dict[str, Any]) -> str:
        purchase_order = row.get("purchase_order_number")
        if purchase_order:
            return purchase_order
        item = row.get("item")
        if isinstance(item, dict):
            return item.get("name") or item.get("description") or "Item"
        return row.get("item") or row.get("_id") or "Record"

    def _metric_value(self, row: Dict[str, Any], intent: QueryIntent) -> Optional[Any]:
        metric = intent.metric
        if metric in (None, "spending"):
            item = row.get("item")
            if isinstance(item, dict):
                return item.get("total_price")
            return row.get("item.total_price")
        if metric == "quantity":
            item = row.get("item")
            if isinstance(item, dict):
                return item.get("quantity")
            return row.get("item.quantity")
        if metric == "unit_price":
            item = row.get("item")
            if isinstance(item, dict):
                return item.get("unit_price")
            return row.get("item.unit_price")
        return None
