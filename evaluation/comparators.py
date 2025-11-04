"""
Comparison helpers for evaluating agent responses against ground truth.
"""

from __future__ import annotations

import difflib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from .models import TestCase
from .utils import serialize_for_json

logger = logging.getLogger(__name__)


class AnswerComparator:
    """Compares agent answers with ground truth using structured heuristics."""

    def __init__(
        self,
        *,
        default_tolerance: float = 0.01,
        openai_api_key: Optional[str] = None,
        semantic_mode: str = "auto",
    ):
        self.default_tolerance = default_tolerance
        self.semantic_mode = semantic_mode
        self.client: Optional[Any] = None

        if semantic_mode != "heuristic" and openai_api_key and OpenAI:
            try:
                self.client = OpenAI(api_key=openai_api_key)
                self.semantic_mode = "llm"
                logger.info("Semantic comparison using OpenAI client")
            except Exception as err:  # pragma: no cover - runtime safeguard
                logger.warning("Failed to init OpenAI client (%s); falling back to heuristics", err)
                self.client = None
                self.semantic_mode = "heuristic"
        else:
            self.semantic_mode = "heuristic"

    def compare(
        self,
        ground_truth: List[Dict[str, Any]],
        ai_response: Dict[str, Any],
        test_case: TestCase,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        if not ai_response.get("success"):
            error_msg = ai_response.get("error") or "Agent returned success=false"
            return False, 0.0, {"error": error_msg}

        ai_results: List[Dict[str, Any]] = ai_response.get("results") or []

        if test_case.expected_type == "count":
            return self._compare_count(ground_truth, ai_results, test_case, ai_response)
        if test_case.expected_type == "aggregation":
            return self._compare_aggregation(ground_truth, ai_results, test_case)
        if test_case.expected_type == "list":
            return self._compare_list(ground_truth, ai_results, test_case)
        if test_case.expected_type == "comparison":
            return self._compare_comparison(ground_truth, ai_results, test_case)
        return self._semantic_compare(ground_truth, ai_response, ai_results, test_case)

    # Structured comparison helpers ------------------------------------- #
    def _compare_count(
        self,
        ground_truth: List[Dict[str, Any]],
        ai_results: List[Dict[str, Any]],
        test_case: TestCase,
        ai_response: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        gt_count = self._extract_count_value(ground_truth)
        ai_count = self._extract_count_value(ai_results)

        if ai_count is None and ai_response:
            result_count = ai_response.get("result_count")
            if isinstance(result_count, (int, float)):
                ai_count = float(result_count)

        if ai_count is None:
            ai_count = float(len(ai_results))

        diff = abs(gt_count - ai_count)
        tolerance = max(1.0, gt_count * test_case.tolerance)
        passed = diff <= tolerance
        similarity = 1.0 if gt_count == 0 else max(0.0, 1.0 - (diff / max(gt_count, 1.0)))

        return passed, similarity, {
            "ground_truth_count": gt_count,
            "ai_count": ai_count,
            "difference": diff,
            "tolerance": tolerance,
        }

    def _compare_aggregation(
        self,
        ground_truth: List[Dict[str, Any]],
        ai_results: List[Dict[str, Any]],
        test_case: TestCase,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        if not ground_truth and not ai_results:
            return True, 1.0, {"note": "both results empty"}

        gt_values = self._extract_numerical_values(ground_truth)
        ai_values = self._extract_numerical_values(ai_results)

        if not gt_values or not ai_values:
            return False, 0.0, {"error": "missing numeric values"}

        matches = 0
        unmatched_ai = list(ai_values)
        for gt_val in gt_values:
            for ai_val in list(unmatched_ai):
                if self._values_match(gt_val, ai_val, test_case.tolerance):
                    matches += 1
                    unmatched_ai.remove(ai_val)
                    break

        gt_total = len(gt_values)
        ai_total = len(ai_values)
        coverage = matches / ai_total if ai_total else 0.0
        similarity = matches / gt_total if gt_total else 0.0
        required_matches = min(gt_total, ai_total) if gt_total and ai_total else matches
        passed = matches >= max(1, required_matches)

        return passed, similarity, {
            "ground_truth_values": gt_values[:5],
            "ai_values": ai_values[:5],
            "matches": matches,
            "ground_truth_total": gt_total,
            "ai_total": ai_total,
            "coverage": coverage,
            "required_matches": required_matches,
        }

    def _compare_list(
        self,
        ground_truth: List[Dict[str, Any]],
        ai_results: List[Dict[str, Any]],
        test_case: TestCase,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        gt_ids = [self._extract_id(item) for item in ground_truth[:10]]
        ai_ids = [self._extract_id(item) for item in ai_results[:10]]

        gt_set = set(gt_ids)
        ai_set = set(ai_ids)

        if not gt_set:
            passed = len(ai_set) == 0
            return passed, 1.0 if passed else 0.0, {"note": "ground truth empty"}

        intersection = len(gt_set & ai_set)
        union = len(gt_set | ai_set) or 1
        jaccard_similarity = intersection / union
        passed = jaccard_similarity >= 0.6

        return passed, jaccard_similarity, {
            "ground_truth_ids": gt_ids,
            "ai_ids": ai_ids,
            "intersection": intersection,
            "jaccard_similarity": jaccard_similarity,
        }

    def _compare_comparison(
        self,
        ground_truth: List[Dict[str, Any]],
        ai_results: List[Dict[str, Any]],
        test_case: TestCase,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        return self._compare_aggregation(ground_truth, ai_results, test_case)

    # Semantic comparison ------------------------------------------------ #
    def _semantic_compare(
        self,
        ground_truth: List[Dict[str, Any]],
        ai_response: Dict[str, Any],
        ai_results: List[Dict[str, Any]],
        test_case: TestCase,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        ground_summary = json.dumps(serialize_for_json(ground_truth), indent=2) if ground_truth else ""
        answer_text = ai_response.get("answer") or ""
        result_text = json.dumps(serialize_for_json(ai_results), indent=2) if ai_results else ""

        if self.semantic_mode == "llm" and self.client:
            prompt = (
                "Determine if the assistant answer conveys the same facts as the ground truth.\n"
                "Respond with JSON: {\"equivalent\": true|false, \"confidence\": <0-1>, \"reasoning\": \"...\"}.\n\n"
                f"Ground truth:\n{ground_summary[:2000]}\n\n"
                f"Assistant answer:\n{answer_text}\n\n"
                f"Assistant structured results:\n{result_text[:2000]}"
            )
            try:
                response = self.client.responses.create(
                    model="gpt-4o-mini",
                    input=prompt,
                    reasoning={"effort": "low"},
                    max_output_tokens=500,
                    timeout=45,
                )
                output_text = getattr(response, "output_text", None)
                if not output_text and hasattr(response, "output"):
                    output_text = "".join(getattr(item, "text", "") for item in response.output)
                data = json.loads(output_text or "{}")
                passed = bool(data.get("equivalent"))
                confidence = float(data.get("confidence", 0.0))
                return passed, confidence, {
                    "method": "llm",
                    "confidence": confidence,
                    "reasoning": data.get("reasoning", ""),
                }
            except Exception as exc:  # pragma: no cover - runtime safeguard
                logger.warning("Semantic comparison via LLM failed: %s", exc)

        concatenated_ai = (answer_text + "\n" + result_text).strip().lower()
        concatenated_gt = ground_summary.strip().lower()
        ratio = difflib.SequenceMatcher(None, concatenated_gt, concatenated_ai).ratio()

        important_numbers = self._extract_numerical_values(ground_truth)
        ai_numbers = self._extract_numerical_values(ai_results)
        if answer_text:
            number_pattern = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
            for match in number_pattern.findall(answer_text):
                normalized = match.replace(",", "")
                try:
                    ai_numbers.append(float(normalized))
                except ValueError:
                    continue

        number_overlap = 0
        for gt_val in important_numbers[:10]:
            if any(self._values_match(gt_val, ai_val, test_case.tolerance) for ai_val in ai_numbers):
                number_overlap += 1

        required_overlap = max(1, min(len(important_numbers), 3))
        has_text = bool(answer_text.strip())
        passed = has_text and (
            number_overlap >= required_overlap
            or (ratio >= 0.55 and number_overlap >= max(1, required_overlap - 1))
        )
        return passed, ratio, {
            "method": "heuristic",
            "text_similarity": ratio,
            "ground_truth_numbers_matched": number_overlap,
        }

    # Utility helpers ---------------------------------------------------- #
    @staticmethod
    def _extract_count_value(documents: List[Dict[str, Any]]) -> Optional[float]:
        if not documents:
            return 0.0

        count_keys = ("total", "total_purchase_orders", "count", "doc_count", "result", "value")
        for doc in documents:
            for key in count_keys:
                value = doc.get(key)
                if isinstance(value, (int, float)):
                    return float(value)

        if documents and isinstance(documents[0], dict):
            for value in documents[0].values():
                if isinstance(value, (int, float)):
                    return float(value)
        return None

    @staticmethod
    def _extract_numerical_values(data: List[Dict[str, Any]]) -> List[float]:
        def collect_numbers(value: Any, bucket: List[float]) -> None:
            if isinstance(value, (int, float)):
                bucket.append(float(value))
            elif isinstance(value, dict):
                for key, val in value.items():
                    if key == "_id":
                        continue
                    collect_numbers(val, bucket)
            elif isinstance(value, list):
                for item in value:
                    collect_numbers(item, bucket)

        values: List[float] = []
        collect_numbers(data, values)
        return values

    @staticmethod
    def _extract_id(item: Dict[str, Any]) -> str:
        if "_id" in item and item["_id"] is not None:
            return str(item["_id"])
        for key in ("name", "department", "supplier", "fiscal_year"):
            if key in item and item[key] is not None:
                return str(item[key])
        return json.dumps(item, sort_keys=True)

    @staticmethod
    def _values_match(val1: float, val2: float, tolerance: float) -> bool:
        if val1 == val2:
            return True
        if val1 == 0 or val2 == 0:
            return abs(val1 - val2) <= max(0.01, tolerance)
        normalized_pairs = [
            (val1, val2),
            (val1 * 100, val2),
            (val1, val2 * 100),
            (val1 / 100, val2),
            (val1, val2 / 100),
        ]
        for a, b in normalized_pairs:
            if a == 0 or b == 0:
                continue
            if abs(a - b) / max(abs(a), abs(b)) <= tolerance:
                return True
        return False
