#!/usr/bin/env python3
"""
AI Query System Evaluation Framework (modular edition).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.append(str(PACKAGE_ROOT))

try:  # Support execution as module or script
    from .models import EvalProfile  # type: ignore
    from .runner import EvaluationRunner  # type: ignore
except ImportError:  # pragma: no cover - script fallback
    from models import EvalProfile
    from runner import EvaluationRunner


logger = logging.getLogger("eval")


def parse_profile_spec(spec: str, defaults: argparse.Namespace) -> EvalProfile:
    """
    Parse profile specification strings.

    Supported formats:
        label=model:reasoning:max_results
        model:reasoning:max_results
        model:reasoning
        model
    """
    label: Optional[str]
    body: str
    if "=" in spec:
        label, body = spec.split("=", 1)
    else:
        label, body = None, spec

    parts = [part for part in body.split(":") if part]
    model = parts[0] if parts else defaults.model
    reasoning = parts[1] if len(parts) > 1 else defaults.reasoning_effort
    max_results = int(parts[2]) if len(parts) > 2 else defaults.max_results

    name = label or f"{model}-{reasoning}-k{max_results}"
    return EvalProfile(name=name, model=model, reasoning_effort=reasoning, max_results=max_results)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate GPT MongoDB LangGraph Agent")
    parser.add_argument("--output-dir", default="./reports/evaluations", help="Directory for evaluation reports")
    parser.add_argument("--mongo-uri", default="mongodb://admin:changeme_secure_password@localhost:27017", help="MongoDB URI")
    parser.add_argument("--database", default="government_procurement", help="MongoDB database name")
    parser.add_argument("--collection", default="purchase_orders", help="MongoDB collection name")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL for the AI agent")
    parser.add_argument("--openai-api-key", default=None, help="Optional OpenAI API key for semantic comparison")
    parser.add_argument("--model", default="gpt-5", help="Default model if profiles are not specified")
    parser.add_argument(
        "--reasoning-effort",
        default="medium",
        choices=["minimal", "low", "medium", "high"],
        help="Default reasoning effort",
    )
    parser.add_argument("--max-results", type=int, default=10, help="Default max results (profile fallback)")
    parser.add_argument("--request-timeout", type=int, default=90, help="HTTP timeout for API requests")
    parser.add_argument(
        "--profiles",
        nargs="*",
        help="Optional list of evaluation profiles. Format label=model:effort:max_results",
    )
    parser.add_argument(
        "--semantic-mode",
        choices=["auto", "llm", "heuristic"],
        default="auto",
        help="Semantic comparison strategy",
    )
    parser.add_argument(
        "--pass-threshold",
        type=float,
        default=0.8,
        help="Pass rate threshold per profile required for successful exit status",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    # Load .env for API keys if present
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    profiles: List[EvalProfile]
    if args.profiles:
        profiles = [parse_profile_spec(spec, args) for spec in args.profiles]
    else:
        default_name = f"{args.model}-{args.reasoning_effort}-k{args.max_results}"
        profiles = [
            EvalProfile(
                name=default_name,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                max_results=args.max_results,
            )
        ]

    config = {
        "mongo_uri": args.mongo_uri,
        "database": args.database,
        "collection": args.collection,
        "api_base_url": args.api_url,
        "openai_api_key": args.openai_api_key,
        "request_timeout": args.request_timeout,
        "semantic_mode": args.semantic_mode,
        "default_tolerance": 0.01,
    }

    runner = EvaluationRunner(config, profiles)
    report = runner.run_evaluation()
    json_path, summary_path = runner.save_report(report, Path(args.output_dir))

    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    for profile in report["profiles"]:
        summary = profile["summary"]
        print(
            f"[{profile['profile']['name']}] "
            f"Pass Rate: {summary['pass_rate']:.1%} "
            f"(avg similarity {summary['avg_similarity_score']:.2f}, "
            f"avg response {summary['avg_response_time']:.2f}s)"
        )
    print(f"\nJSON Report   : {json_path}")
    print(f"Summary Report: {summary_path}")
    print("=" * 80)

    threshold = args.pass_threshold
    all_passed = all(profile["summary"]["pass_rate"] >= threshold for profile in report["profiles"])
    raise SystemExit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
