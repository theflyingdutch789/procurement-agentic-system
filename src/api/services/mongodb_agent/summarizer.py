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
        max_results_for_prompt = 20
        limited_results = results[:max_results_for_prompt]

        prompt = ANSWER_STATIC_PROMPT + f"""

Question: {question}

MongoDB Pipeline: {json.dumps(pipeline, indent=2)}

Query Results (showing {len(limited_results)} of {len(results)} total):
{json.dumps(limited_results, indent=2)}

Provide your answer:"""

        request: Dict[str, Any] = {
            "model": self.model_name,
            "input": prompt,
            "text": {"verbosity": verbosity},
            "max_output_tokens": 1000,
        }

        if previous_response_id:
            request["previous_response_id"] = previous_response_id

        response = self.client.responses.create(**request)
        answer_text = getattr(response, "output_text", None) or "Results retrieved successfully"
        return answer_text, response.id
