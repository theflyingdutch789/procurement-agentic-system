#!/usr/bin/env python3
"""
GPT-5 Model Benchmark Script

Compares performance of:
1. GPT-5 with medium reasoning effort
2. GPT-5 mini with low reasoning effort

Runs the same evaluation tests with both configurations and generates
a comparison report showing performance, accuracy, and cost differences.
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import argparse

# Color codes for terminal output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color


class ModelBenchmark:
    """Runs benchmarks comparing different GPT-5 model configurations."""

    def __init__(self, output_dir: str = "./benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.configurations = [
            {
                "name": "GPT-5 Medium Reasoning",
                "model": "gpt-5",
                "reasoning_effort": "medium",
                "label": "gpt5_medium"
            },
            {
                "name": "GPT-5 Mini Low Reasoning",
                "model": "gpt-5-mini",
                "reasoning_effort": "low",
                "label": "gpt5_mini_low"
            },
            {
                "name": "GPT-5 Nano Low Reasoning",
                "model": "gpt-5-nano",
                "reasoning_effort": "low",
                "label": "gpt5_nano_low"
            }
        ]

        self.results = {}

    def run_evaluation(self, config: Dict[str, str]) -> Dict[str, Any]:
        """Run evaluation with specified configuration."""
        print(f"\n{BLUE}{'='*80}{NC}")
        print(f"{BLUE}Running: {config['name']}{NC}")
        print(f"{BLUE}{'='*80}{NC}\n")

        try:
            # Run the evaluation
            start_time = time.time()
            profile_arg = f"{config['label']}={config['model']}:{config['reasoning_effort']}:10"
            result = subprocess.run(
                [sys.executable, "evaluation/eval_system.py", "--profiles", profile_arg],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            end_time = time.time()

            # Find the latest eval report
            eval_results_dir = Path("./reports/evaluations")
            report_files = sorted(eval_results_dir.glob("eval_report_*.json"))

            if report_files:
                latest_report = report_files[-1]
                with open(latest_report, 'r') as f:
                    eval_data = json.load(f)

                return {
                    "config": config,
                    "total_time": end_time - start_time,
                    "eval_data": eval_data,
                    "success": True,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            else:
                return {
                    "config": config,
                    "total_time": end_time - start_time,
                    "success": False,
                    "error": "No report file generated",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }

        except subprocess.TimeoutExpired:
            return {
                "config": config,
                "success": False,
                "error": "Evaluation timed out (>10 minutes)"
            }

        except Exception as e:
            return {
                "config": config,
                "success": False,
                "error": str(e)
            }

    def run_all_benchmarks(self):
        """Run benchmarks for all configurations."""
        print(f"\n{GREEN}{'='*80}{NC}")
        print(f"{GREEN}  GPT-5 Model Benchmark Suite{NC}")
        print(f"{GREEN}{'='*80}{NC}\n")
        print(f"Configurations to test: {len(self.configurations)}")
        print(f"Output directory: {self.output_dir}\n")

        for config in self.configurations:
            result = self.run_evaluation(config)
            self.results[config['label']] = result

            if result['success']:
                summary = result['eval_data']['summary']
                print(f"{GREEN}✓ {config['name']} completed{NC}")
                print(f"  Pass Rate: {summary['pass_rate']*100:.1f}%")
                print(f"  Avg Response Time: {summary['avg_response_time']:.2f}s")
                print(f"  Total Time: {result['total_time']:.2f}s")
            else:
                print(f"{RED}✗ {config['name']} failed{NC}")
                print(f"  Error: {result.get('error', 'Unknown error')}")

    def generate_comparison_report(self):
        """Generate detailed comparison report."""
        report_path = self.output_dir / f"benchmark_comparison_{self.timestamp}.json"
        summary_path = self.output_dir / f"benchmark_summary_{self.timestamp}.txt"

        # Save JSON report
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        # Generate text summary
        with open(summary_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("GPT-5 MODEL BENCHMARK COMPARISON\n")
            f.write("="*80 + "\n\n")
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Configurations Tested: {len(self.configurations)}\n\n")

            # Compare metrics
            f.write("PERFORMANCE COMPARISON\n")
            f.write("-"*80 + "\n\n")

            for label, result in self.results.items():
                if result['success']:
                    config = result['config']
                    summary = result['eval_data']['summary']

                    f.write(f"{config['name']}\n")
                    f.write(f"  Model: {config['model']}\n")
                    f.write(f"  Reasoning Effort: {config['reasoning_effort']}\n")
                    f.write(f"  Pass Rate: {summary['pass_rate']*100:.1f}% ({summary['passed']}/{summary['total_tests']})\n")
                    f.write(f"  Average Similarity: {summary['avg_similarity_score']:.3f}\n")
                    f.write(f"  Average Response Time: {summary['avg_response_time']:.2f}s\n")
                    f.write(f"  Total Benchmark Time: {result['total_time']:.2f}s\n")
                    f.write(f"\n")

                    # Category breakdown
                    f.write(f"  By Category:\n")
                    for cat, cat_data in result['eval_data']['by_category'].items():
                        f.write(f"    {cat.upper()}: {cat_data['pass_rate']*100:.1f}% ")
                        f.write(f"({cat_data['passed']}/{cat_data['total']})\n")
                    f.write("\n")

            # Winner comparison
            f.write("\n" + "="*80 + "\n")
            f.write("WINNER ANALYSIS\n")
            f.write("="*80 + "\n\n")

            successful_results = {k: v for k, v in self.results.items() if v['success']}

            if len(successful_results) >= 2:
                # Compare pass rates
                best_pass_rate = max(successful_results.items(),
                                    key=lambda x: x[1]['eval_data']['summary']['pass_rate'])
                f.write(f"Best Pass Rate: {best_pass_rate[1]['config']['name']} ")
                f.write(f"({best_pass_rate[1]['eval_data']['summary']['pass_rate']*100:.1f}%)\n")

                # Compare speed
                best_speed = min(successful_results.items(),
                               key=lambda x: x[1]['eval_data']['summary']['avg_response_time'])
                f.write(f"Fastest Response: {best_speed[1]['config']['name']} ")
                f.write(f"({best_speed[1]['eval_data']['summary']['avg_response_time']:.2f}s avg)\n")

                # Compare total time
                best_total_time = min(successful_results.items(),
                                     key=lambda x: x[1]['total_time'])
                f.write(f"Fastest Total Time: {best_total_time[1]['config']['name']} ")
                f.write(f"({best_total_time[1]['total_time']:.2f}s)\n")

            f.write("\n")

            # Detailed test results comparison
            f.write("\n" + "="*80 + "\n")
            f.write("PER-TEST COMPARISON\n")
            f.write("="*80 + "\n\n")

            if len(successful_results) >= 2:
                # Get test IDs from first successful result
                first_result = list(successful_results.values())[0]
                all_tests = (first_result['eval_data'].get('passed_tests', []) +
                           first_result['eval_data'].get('failed_tests', []))

                for test in all_tests:
                    test_id = test['id']
                    f.write(f"{test_id}: {test['question']}\n")

                    for label, result in successful_results.items():
                        config_name = result['config']['name']

                        # Find this test in the results
                        passed_tests = result['eval_data'].get('passed_tests', [])
                        failed_tests = result['eval_data'].get('failed_tests', [])

                        test_result = None
                        for t in passed_tests + failed_tests:
                            if t['id'] == test_id:
                                test_result = t
                                break

                        if test_result:
                            status = "✓ PASS" if test_result in passed_tests else "✗ FAIL"
                            f.write(f"  {config_name}: {status} ")
                            f.write(f"(similarity: {test_result.get('similarity_score', 0):.2f}, ")
                            f.write(f"time: {test_result.get('ai_response_time', 0):.2f}s)\n")

                    f.write("\n")

        print(f"\n{GREEN}{'='*80}{NC}")
        print(f"{GREEN}Benchmark reports generated:{NC}")
        print(f"  JSON: {report_path}")
        print(f"  Summary: {summary_path}")
        print(f"{GREEN}{'='*80}{NC}\n")

        # Display quick summary
        self.display_quick_summary()

    def display_quick_summary(self):
        """Display quick summary to terminal."""
        print(f"\n{BLUE}{'='*80}{NC}")
        print(f"{BLUE}QUICK COMPARISON{NC}")
        print(f"{BLUE}{'='*80}{NC}\n")

        successful_results = {k: v for k, v in self.results.items() if v['success']}

        if len(successful_results) >= 2:
            # Build dynamic headers based on number of configs
            configs = list(successful_results.values())
            config_names = [c['config']['name'] for c in configs]
            headers = ["Metric"] + config_names + ["Winner"]

            rows = []

            # Pass rate
            pass_rates = [c['eval_data']['summary']['pass_rate'] * 100 for c in configs]
            best_idx = pass_rates.index(max(pass_rates))
            row = ["Pass Rate"] + [f"{pr:.1f}%" for pr in pass_rates] + [config_names[best_idx]]
            rows.append(row)

            # Avg response time (lower is better)
            times = [c['eval_data']['summary']['avg_response_time'] for c in configs]
            best_idx = times.index(min(times))
            row = ["Avg Response Time"] + [f"{t:.2f}s" for t in times] + [config_names[best_idx]]
            rows.append(row)

            # Total time (lower is better)
            total_times = [c['total_time'] for c in configs]
            best_idx = total_times.index(min(total_times))
            row = ["Total Time"] + [f"{t:.2f}s" for t in total_times] + [config_names[best_idx]]
            rows.append(row)

            # Similarity (higher is better)
            similarities = [c['eval_data']['summary']['avg_similarity_score'] for c in configs]
            best_idx = similarities.index(max(similarities))
            row = ["Avg Similarity"] + [f"{s:.3f}" for s in similarities] + [config_names[best_idx]]
            rows.append(row)

            # Print table with dynamic column widths
            num_cols = len(headers)
            if num_cols == 4:  # 2 configs
                col_widths = [20, 20, 20, 30]
            else:  # 3+ configs
                col_widths = [18] + [15] * (num_cols - 2) + [25]

            # Header
            header_row = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
            print(header_row)
            print("-" * min(100, sum(col_widths) + (len(headers) - 1) * 2))

            # Rows
            for row in rows:
                row_str = "  ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
                print(row_str)

            print()


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark GPT-5 model configurations"
    )
    parser.add_argument(
        '--output-dir',
        default='./benchmark_results',
        help='Directory to save benchmark results'
    )

    args = parser.parse_args()

    # Create and run benchmark
    benchmark = ModelBenchmark(output_dir=args.output_dir)
    benchmark.run_all_benchmarks()
    benchmark.generate_comparison_report()

    print(f"\n{GREEN}✓ Benchmark complete!{NC}\n")


if __name__ == "__main__":
    main()
