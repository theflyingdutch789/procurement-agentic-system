"""
Core GPT-powered MongoDB agent orchestration.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from pymongo import MongoClient

from .executor import MongoDBQueryExecutor
from .pipeline_generator import PipelineGenerator
from .summarizer import AnswerSummarizer
from .validators import QueryValidator

logger = logging.getLogger(__name__)


class GPT5MongoDBAgent:
    """
    GPT-5 Reasoning Agent for MongoDB query generation and execution.
    """

    def __init__(
        self,
        *,
        mongo_client: MongoClient,
        database_name: str,
        collection_name: str,
        openai_api_key: Optional[str] = None,
        model_name: str = "gpt-5",
        reasoning_effort: str = "medium",
        verbosity: str = "medium",
        max_results: int = 100,
    ) -> None:
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key

        self.client = OpenAI()
        self.database = mongo_client[database_name]
        self.collection = self.database[collection_name]

        self.validator = QueryValidator(self.collection)
        self.executor = MongoDBQueryExecutor(self.collection, max_results=max_results)

        self._model_name = model_name
        self.reasoning_effort = reasoning_effort
        self.verbosity = verbosity

        self.pipeline_generator = PipelineGenerator(self.client, model_name)
        self.summarizer = AnswerSummarizer(self.client, model_name)

        self.max_attempts = 3
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #
    @property
    def model_name(self) -> str:
        return self._model_name

    @model_name.setter
    def model_name(self, value: str) -> None:
        self._model_name = value
        self.pipeline_generator.set_model_name(value)
        self.summarizer.set_model_name(value)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _supports_reasoning_effort(self) -> bool:
        return isinstance(self.model_name, str) and self.model_name.lower().startswith("gpt-5")

    def _normalize_verbosity(self, desired: str) -> str:
        return desired if self._supports_reasoning_effort() else "medium"

    def _generate_pipeline_attempt(
        self,
        *,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        previous_error: Optional[str] = None,
        previous_response_id: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], Optional[Any], Optional[str]]:
        return self.pipeline_generator.generate(
            question=question,
            conversation_history=conversation_history,
            previous_error=previous_error,
            previous_response_id=previous_response_id,
            reasoning_effort=reasoning_effort or self.reasoning_effort,
        )

    def _validate_pipeline(self, pipeline: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        return self.validator.validate_aggregation_pipeline(pipeline)

    def _execute_pipeline(
        self, pipeline: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        success, result = self.executor.execute_aggregation(pipeline)
        if not success:
            return False, None, result if isinstance(result, str) else "Pipeline execution failed"
        return True, result, None

    def _summarize_answer(
        self,
        *,
        question: str,
        pipeline: List[Dict[str, Any]],
        result: List[Dict[str, Any]],
        verbosity: str,
        pipeline_response_id: Optional[str],
        latest_response: Optional[Any],
    ) -> Tuple[str, Optional[str], Optional[str]]:
        answer_text, answer_response_id = self.summarizer.summarize(
            question=question,
            pipeline=pipeline,
            results=result,
            verbosity=self._normalize_verbosity(verbosity),
            previous_response_id=pipeline_response_id,
        )

        reasoning_summary = None
        if latest_response is not None and hasattr(latest_response, "reasoning_summary"):
            reasoning_summary = latest_response.reasoning_summary

        return answer_text, answer_response_id, reasoning_summary

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def query(
        self,
        question: str,
        *,
        reasoning_effort: Optional[str] = None,
        verbosity: Optional[str] = None,
        previous_response_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        try:
            effort = reasoning_effort or self.reasoning_effort
            verb = verbosity or self.verbosity

            previous_error: Optional[str] = None
            last_error: Optional[str] = None
            prev_response_id = previous_response_id

            for _ in range(1, self.max_attempts + 1):
                (
                    pipeline,
                    pipeline_response_id,
                    latest_response,
                    pipeline_error,
                ) = self._generate_pipeline_attempt(
                    question=question,
                    conversation_history=conversation_history,
                    previous_error=previous_error,
                    previous_response_id=prev_response_id,
                    reasoning_effort=effort,
                )

                prev_response_id = pipeline_response_id

                if not pipeline:
                    previous_error = pipeline_error
                    last_error = pipeline_error
                    continue

                is_valid, validation_error = self._validate_pipeline(pipeline)
                if not is_valid:
                    previous_error = validation_error
                    last_error = validation_error
                    continue

                success, result, execution_error = self._execute_pipeline(pipeline)
                if not success or result is None:
                    previous_error = execution_error
                    last_error = execution_error
                    continue

                answer, answer_response_id, reasoning_summary = self._summarize_answer(
                    question=question,
                    pipeline=pipeline,
                    result=result,
                    verbosity=verb,
                    pipeline_response_id=pipeline_response_id,
                    latest_response=latest_response,
                )

                return {
                    "success": True,
                    "answer": answer,
                    "pipeline": pipeline,
                    "results": result,
                    "result_count": len(result),
                    "reasoning_summary": reasoning_summary,
                    "response_id": answer_response_id,
                    "error": None,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            return {
                "success": False,
                "answer": None,
                "pipeline": None,
                "results": None,
                "reasoning_summary": None,
                "error": last_error or "Failed to generate MongoDB pipeline",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as exc:  # pragma: no cover - defensive
            error_msg = f"GPT-5 Agent error: {exc}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "answer": None,
                "pipeline": None,
                "results": None,
                "reasoning_summary": None,
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def reset_conversation(self) -> None:
        """Reset conversation state (kept for backwards compatibility)."""
        self.logger.info("Conversation state reset")
