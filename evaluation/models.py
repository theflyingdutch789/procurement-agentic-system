"""
Dataclasses used across the evaluation framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EvalProfile:
    """Represents a single evaluation profile (model + reasoning + limits)."""

    name: str
    model: str
    reasoning_effort: str
    max_results: int


@dataclass
class TestCase:
    """Represents an evaluation test case."""

    id: str
    category: str
    difficulty: str
    question: str
    expected_type: str  # 'count', 'aggregation', 'list', 'comparison', 'semantic'
    description: str
    ground_truth_query: List[Dict[str, Any]]
    tolerance: float = 0.01
    tags: Optional[List[str]] = None


@dataclass
class EvalResult:
    """Result of a single test case execution."""

    profile: str
    test_id: str
    question: str
    category: str
    difficulty: str
    passed: bool
    ground_truth: Any
    ai_answer: Any
    ai_pipeline: Optional[List[Dict[str, Any]]]
    ai_reasoning_summary: Optional[str]
    ai_response_time: float
    similarity_score: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
