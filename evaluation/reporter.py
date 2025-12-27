"""
Reporting helpers for evaluation runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from .models import EvalProfile, EvalResult
from .utils import mean_or_zero, serialize_for_json, write_json


def build_profile_report(profile: EvalProfile, results: List[EvalResult]) -> Dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    avg_similarity = mean_or_zero([r.similarity_score for r in results])
    avg_response_time = mean_or_zero([r.ai_response_time for r in results])

    by_category: Dict[str, Dict[str, Any]] = {}
    by_difficulty: Dict[str, Dict[str, Any]] = {}

    for res in results:
        cat = res.category
        diff = res.difficulty

        if cat not in by_category:
            by_category[cat] = {"total": 0, "passed": 0, "similarities": []}
        if diff not in by_difficulty:
            by_difficulty[diff] = {"total": 0, "passed": 0}

        by_category[cat]["total"] += 1
        by_difficulty[diff]["total"] += 1
        if res.passed:
            by_category[cat]["passed"] += 1
            by_difficulty[diff]["passed"] += 1
        by_category[cat]["similarities"].append(res.similarity_score)

    for metrics in by_category.values():
        metrics["pass_rate"] = (
            metrics["passed"] / metrics["total"] if metrics["total"] else 0.0
        )
        metrics["avg_similarity"] = mean_or_zero(metrics.pop("similarities"))

    for metrics in by_difficulty.values():
        metrics["pass_rate"] = (
            metrics["passed"] / metrics["total"] if metrics["total"] else 0.0
        )

    failed_tests = [
        {
            "id": res.test_id,
            "question": res.question,
            "similarity": res.similarity_score,
            "error": res.error,
            "details": serialize_for_json(res.details),
        }
        for res in results
        if not res.passed
    ]

    serialized_results = [
        {
            **res.__dict__,
            "ground_truth": serialize_for_json(res.ground_truth),
            "ai_answer": serialize_for_json(res.ai_answer),
            "ai_pipeline": serialize_for_json(res.ai_pipeline),
            "details": serialize_for_json(res.details),
        }
        for res in results
    ]

    return {
        "profile": {
            "name": profile.name,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "max_results": profile.max_results,
        },
        "summary": {
            "total": total,
            "passed": passed,
            "pass_rate": passed / total if total else 0.0,
            "avg_similarity_score": avg_similarity,
            "avg_response_time": avg_response_time,
        },
        "by_category": by_category,
        "by_difficulty": by_difficulty,
        "failed_tests": failed_tests,
        "results": serialized_results,
    }


def write_reports(report: Dict[str, Any], output_dir: Path) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = report["generated_at"].replace(":", "").replace("-", "").replace(".", "")

    json_path = output_dir / f"eval_report_{timestamp}.json"
    write_json(json_path, report)

    summary_path = output_dir / f"eval_summary_{timestamp}.txt"
    with summary_path.open("w", encoding="utf-8") as fh:
        fh.write("=" * 80 + "\n")
        fh.write("EVALUATION SUMMARY\n")
        fh.write("=" * 80 + "\n")
        fh.write(f"Generated at: {report['generated_at']}\n")
        fh.write(f"Test cases : {report['test_case_count']}\n\n")

        for profile in report["profiles"]:
            fh.write(f"[Profile] {profile['profile']['name']}\n")
            fh.write(
                f"  Model           : {profile['profile']['model']} "
                f"(effort={profile['profile']['reasoning_effort']}, "
                f"max_results={profile['profile']['max_results']})\n"
            )
            summary = profile["summary"]
            fh.write(
                f"  Pass Rate       : {summary['passed']}/{summary['total']} "
                f"({summary['pass_rate']:.1%})\n"
            )
            fh.write(
                f"  Avg Similarity  : {summary['avg_similarity_score']:.2f}\n"
            )
            fh.write(
                f"  Avg Response(s) : {summary['avg_response_time']:.2f}\n"
            )

            if profile["failed_tests"]:
                fh.write("  Failed Tests:\n")
                for failure in profile["failed_tests"]:
                    fh.write(
                        f"    - {failure['id']} (similarity "
                        f"{failure['similarity']:.2f})\n"
                    )
                    if failure.get("error"):
                        fh.write(f"      error: {failure['error']}\n")
            fh.write("\n")

    return json_path, summary_path
