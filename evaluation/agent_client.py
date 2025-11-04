"""
Utilities for interacting with MongoDB and the FastAPI agent during evaluation.
"""

from __future__ import annotations

import copy
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from pymongo import MongoClient

logger = logging.getLogger(__name__)


class GroundTruthGenerator:
    """Executes aggregation pipelines directly against MongoDB with caching."""

    def __init__(self, mongo_uri: str, database: str, collection: str):
        self.client = MongoClient(mongo_uri)
        self.collection = self.client[database][collection]
        self.cache: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("Connected to MongoDB %s.%s", database, collection)

    def execute_pipeline(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cache_key = json.dumps(pipeline, sort_keys=True, default=str)
        if cache_key in self.cache:
            return copy.deepcopy(self.cache[cache_key])

        results = list(self.collection.aggregate(pipeline))
        self.cache[cache_key] = results
        logger.debug("Pipeline %s returned %d documents", pipeline, len(results))
        return copy.deepcopy(results)

    def close(self) -> None:
        self.client.close()


class AIQueryTester:
    """Wrapper for issuing requests to the FastAPI LangGraph agent."""

    def __init__(self, api_base_url: str, request_timeout: int = 120):
        self.api_base_url = api_base_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = request_timeout

    def send_query(
        self,
        question: str,
        *,
        model: str,
        reasoning_effort: str,
        max_results: int,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Dict[str, Any], float]:
        payload: Dict[str, Any] = {
            "question": question,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "max_results": max_results,
            "verbosity": "medium",
        }

        if conversation_id:
            payload["conversation_id"] = conversation_id
        if conversation_history:
            payload["conversation_history"] = conversation_history

        start = datetime.utcnow()
        try:
            response = self.session.post(
                f"{self.api_base_url}/api/ai/query",
                json=payload,
                timeout=self.timeout,
            )
            elapsed = (datetime.utcnow() - start).total_seconds()

            if response.status_code == 200:
                return response.json(), elapsed

            logger.error("API error %s: %s", response.status_code, response.text[:400])
            return (
                {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "details": response.text[:400],
                },
                elapsed,
            )

        except requests.RequestException as exc:
            elapsed = (datetime.utcnow() - start).total_seconds()
            logger.error("Request error: %s", exc)
            return {"success": False, "error": str(exc)}, elapsed

    def close(self) -> None:
        self.session.close()
