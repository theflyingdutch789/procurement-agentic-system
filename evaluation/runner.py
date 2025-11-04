"""
Evaluation runner orchestration.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .agent_client import AIQueryTester, GroundTruthGenerator
from .comparators import AnswerComparator
from .models import EvalProfile, EvalResult, TestCase
from .reporter import build_profile_report, write_reports
from .test_catalog import load_test_cases


class EvaluationRunner:
    """Coordinates ground-truth generation, agent calls, and reporting."""

    def __init__(self, config: Dict[str, Any], profiles: List[EvalProfile]):
        self.config = config
        self.profiles = profiles
        self.ground_truth_gen = GroundTruthGenerator(
            mongo_uri=config["mongo_uri"],
            database=config["database"],
            collection=config["collection"],
        )
        self.comparator = AnswerComparator(
            default_tolerance=config.get("default_tolerance", 0.01),
            openai_api_key=config.get("openai_api_key"),
            semantic_mode=config.get("semantic_mode", "auto"),
        )
        self.test_cases = load_test_cases()

    def run_evaluation(self) -> Dict[str, Any]:
        tests_count = len(self.test_cases)
        profile_reports: List[Dict[str, Any]] = []

        for profile in self.profiles:
            tester = AIQueryTester(
                api_base_url=self.config["api_base_url"],
                request_timeout=self.config.get("request_timeout", 120),
            )
            profile_results: List[EvalResult] = []

            for test_case in self.test_cases:
                result = self._evaluate_test_case(test_case, profile, tester)
                profile_results.append(result)

            tester.close()
            profile_reports.append(build_profile_report(profile, profile_results))

        self.ground_truth_gen.close()

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "profiles": profile_reports,
            "test_case_count": tests_count,
        }

    def _evaluate_test_case(
        self,
        test_case: TestCase,
        profile: EvalProfile,
        tester: AIQueryTester,
    ) -> EvalResult:
        try:
            ground_truth = self.ground_truth_gen.execute_pipeline(test_case.ground_truth_query)
            ai_response, response_time = tester.send_query(
                test_case.question,
                model=profile.model,
                reasoning_effort=profile.reasoning_effort,
                max_results=profile.max_results,
            )

            passed, similarity, details = self.comparator.compare(
                ground_truth, ai_response, test_case
            )

            return EvalResult(
                profile=profile.name,
                test_id=test_case.id,
                question=test_case.question,
                category=test_case.category,
                difficulty=test_case.difficulty,
                passed=passed,
                ground_truth=ground_truth,
                ai_answer=ai_response.get("results"),
                ai_pipeline=ai_response.get("pipeline"),
                ai_reasoning_summary=ai_response.get("reasoning_summary"),
                ai_response_time=response_time,
                similarity_score=similarity,
                error=ai_response.get("error"),
                details=details,
            )

        except Exception as exc:  # pragma: no cover - runtime safeguard
            return EvalResult(
                profile=profile.name,
                test_id=test_case.id,
                question=test_case.question,
                category=test_case.category,
                difficulty=test_case.difficulty,
                passed=False,
                ground_truth=[],
                ai_answer=[],
                ai_pipeline=None,
                ai_reasoning_summary=None,
                ai_response_time=0.0,
                similarity_score=0.0,
                error=str(exc),
                details={"exception": str(exc)},
            )

    def save_report(self, report: Dict[str, Any], output_dir: Path):
        return write_reports(report, output_dir)
