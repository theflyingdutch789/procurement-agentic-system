# 🧪 AI Agent Evaluation Framework

A comprehensive testing and benchmarking system for evaluating LLM-powered MongoDB query generation agents.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Test Catalog](#-test-catalog)
- [Quick Start](#-quick-start)
- [Components](#-components)
- [Evaluation Metrics](#-evaluation-metrics)
- [Running Evaluations](#-running-evaluations)
- [Interpreting Results](#-interpreting-results)
- [Custom Tests](#-custom-tests)
- [Advanced Usage](#-advanced-usage)

---

## 🎯 Overview

The evaluation framework provides a robust, extensible system for testing and benchmarking AI agents that convert natural language queries into MongoDB operations. It includes 30+ carefully crafted test cases spanning multiple difficulty levels and query types.

### Key Features

- **30+ Test Cases**: Comprehensive coverage from basic to ultra-complex queries
- **Multi-Model Support**: Test different LLM models and configurations simultaneously
- **Automated Validation**: Semantic and structural result comparison
- **Detailed Reporting**: JSON and human-readable summary reports
- **Configurable Profiles**: Test with different model parameters and reasoning levels
- **Ground Truth Validation**: Compare against reference MongoDB queries

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Evaluation System                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Test Catalog (30+ cases)                 │  │
│  │  • Basic (easy)  • Intermediate (medium)              │  │
│  │  • Advanced (hard)  • Ultra (very hard)               │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                      │
│                       ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Evaluation Runner                        │  │
│  │  • Profile Management  • Parallel Execution           │  │
│  │  • Progress Tracking  • Error Handling                │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                      │
│                       ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Agent Client                             │  │
│  │  • API Communication  • Request Formatting            │  │
│  │  • Response Parsing  • Timeout Handling               │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                      │
│                       ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Comparators & Validators                    │  │
│  │  • Structural Comparison  • Semantic Analysis         │  │
│  │  • LLM-based Validation  • Heuristic Checks           │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                      │
│                       ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Report Generator                         │  │
│  │  • JSON Reports  • Summary Statistics                 │  │
│  │  • Pass/Fail Analysis  • Performance Metrics          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📚 Test Catalog

The framework includes 30+ test cases organized by difficulty and category.

### Test Categories

#### 1. Basic Queries (Easy)
Simple operations testing fundamental capabilities.

| Test ID | Description | Query Type |
|---------|-------------|------------|
| `basic_001` | Total document count | Count |
| `basic_002` | Total spending across all years | Aggregation |
| `basic_003` | List all fiscal years | Distinct |
| `basic_004` | Top N suppliers by spending | Sort + Limit |
| `basic_005` | Items above price threshold | Filter |

**Example:**
```python
TestCase(
    id="basic_001",
    category="basic",
    difficulty="easy",
    question="How many total purchase order line items are in the database?",
    expected_type="count",
    description="Simple total document count.",
    ground_truth_query=[
        {"$count": "total_purchase_orders"}
    ]
)
```

#### 2. Intermediate Queries (Medium)
Multi-step operations requiring data grouping and analysis.

| Test ID | Description | Query Type |
|---------|-------------|------------|
| `intermediate_001` | Spending by fiscal year | Group + Sort |
| `intermediate_002` | Top department by spending | Group + Sort + Limit |
| `intermediate_003` | Average price per acquisition type | Group + Avg |
| `intermediate_004` | Supplier order frequency | Group + Count |
| `intermediate_005` | Department spending trends | Multi-stage aggregation |

**Example:**
```python
TestCase(
    id="intermediate_002",
    category="intermediate",
    difficulty="medium",
    question="Which department spent the most overall?",
    expected_type="aggregation",
    ground_truth_query=[
        {"$match": {"department.normalized_name": {"$ne": None}}},
        {
            "$group": {
                "_id": "$department.normalized_name",
                "total_spending": {"$sum": {"$ifNull": ["$item.total_price", 0]}}
            }
        },
        {"$sort": {"total_spending": -1}},
        {"$limit": 1}
    ]
)
```

#### 3. Advanced Queries (Hard)
Complex multi-stage pipelines with sophisticated logic.

| Test ID | Description | Query Type |
|---------|-------------|------------|
| `advanced_001` | Top suppliers with conditions | Complex filter + Group |
| `advanced_002` | Department category breakdown | Nested aggregation |
| `advanced_003` | Year-over-year growth analysis | Temporal aggregation |
| `advanced_004` | Supplier concentration metrics | Statistical aggregation |
| `advanced_005` | Multi-dimensional analysis | Complex pipeline |

**Example:**
```python
TestCase(
    id="advanced_003",
    category="advanced",
    difficulty="hard",
    question="Compare IT vs NON-IT spending across fiscal years",
    expected_type="aggregation",
    ground_truth_query=[
        {
            "$group": {
                "_id": {
                    "year": "$dates.fiscal_year",
                    "it_type": {
                        "$cond": [
                            {"$regexMatch": {"input": "$acquisition.type", "regex": "^IT"}},
                            "IT",
                            "NON-IT"
                        ]
                    }
                },
                "total": {"$sum": "$item.total_price"}
            }
        },
        {"$sort": {"_id.year": 1, "_id.it_type": 1}}
    ]
)
```

#### 4. Ultra Queries (Very Hard)
Cutting-edge queries testing advanced reasoning and edge cases.

| Test ID | Description | Query Type |
|---------|-------------|------------|
| `ultra_001` | Geospatial supplier analysis | Geo + Aggregation |
| `ultra_002` | Anomaly detection | Statistical + Conditional |
| `ultra_003` | Cross-dimensional trends | Complex temporal analysis |
| `ultra_004` | Supplier network analysis | Graph-like operations |
| `ultra_005` | Predictive spending patterns | Advanced aggregation |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=your_api_key_here

# Ensure API and MongoDB are running
docker-compose up -d mongodb api
```

### Basic Evaluation

Run the full test suite with default settings:

```bash
python eval_system.py
```

### Custom Profile Evaluation

Test with specific model configurations:

```bash
python eval_system.py \
  --profiles "gpt-5:high:10" "gpt-5-mini:medium:5" \
  --output-dir ./reports/evaluations \
  --pass-threshold 0.8
```

### Using the Shell Script

```bash
# Navigate to project root
cd ..

# Run evaluation (from project root)
./scripts/run_eval.sh
```

---

## 🔧 Components

### 1. `eval_system.py` - Main Entry Point

The orchestrator for the entire evaluation process.

**Key Features:**
- Command-line interface
- Profile management
- Environment configuration
- Exit status based on pass threshold

**Usage:**
```bash
python eval_system.py \
  --model gpt-5 \
  --reasoning-effort high \
  --max-results 10 \
  --api-url http://localhost:8000 \
  --mongo-uri mongodb://admin:password@localhost:27017 \
  --database government_procurement \
  --collection purchase_orders \
  --output-dir ./reports
```

### 2. `test_catalog.py` - Test Case Repository

Contains all test case definitions with ground truth queries.

**Structure:**
```python
def load_test_cases() -> List[TestCase]:
    return [
        TestCase(
            id="unique_id",
            category="basic|intermediate|advanced|ultra",
            difficulty="easy|medium|hard|very hard",
            question="Natural language question",
            expected_type="count|list|aggregation|documents",
            description="What this test validates",
            ground_truth_query=[...]  # MongoDB pipeline
        ),
        # ... more tests
    ]
```

### 3. `runner.py` - Evaluation Executor

Manages test execution, result collection, and reporting.

**Key Methods:**
- `run_evaluation()`: Execute full test suite
- `run_single_test()`: Run one test case
- `collect_results()`: Aggregate test outcomes
- `generate_report()`: Create output files

### 4. `agent_client.py` - API Communication

Handles communication with the AI agent API.

**Features:**
- Configurable timeouts
- Retry logic
- Error handling
- Response parsing
- Request validation

**Example:**
```python
from agent_client import AgentClient

client = AgentClient(
    api_url="http://localhost:8000",
    timeout=90
)

result = client.query_natural_language(
    question="What is the total spending?",
    profile=EvalProfile(model="gpt-5", reasoning_effort="high", max_results=10)
)
```

### 5. `comparators.py` - Result Validation

Compares agent results against ground truth using multiple strategies.

**Comparison Modes:**

1. **Structural Comparison**
   - Direct result matching
   - Schema validation
   - Type checking

2. **Semantic Comparison**
   - LLM-based similarity
   - Heuristic analysis
   - Tolerance for minor differences

3. **Hybrid Approach**
   - Combines multiple strategies
   - Confidence scoring
   - Fallback mechanisms

**Example:**
```python
from comparators import SemanticComparator

comparator = SemanticComparator(
    openai_api_key="...",
    mode="auto"  # or "llm" or "heuristic"
)

is_match, confidence = comparator.compare(
    expected_results,
    actual_results,
    question="What is the total spending?"
)
```

### 6. `reporter.py` - Report Generation

Creates detailed reports in multiple formats.

**Output Files:**
- `eval_report_TIMESTAMP.json`: Complete test results
- `eval_summary_TIMESTAMP.txt`: Human-readable summary

**Report Contents:**
- Test pass/fail status
- Execution times
- Error messages
- Confidence scores
- Profile comparisons

### 7. `models.py` - Data Models

Type-safe data structures for the entire system.

**Key Models:**
```python
@dataclass
class EvalProfile:
    name: str
    model: str
    reasoning_effort: str
    max_results: int

@dataclass
class TestCase:
    id: str
    category: str
    difficulty: str
    question: str
    expected_type: str
    description: str
    ground_truth_query: List[Dict]

@dataclass
class TestResult:
    test_id: str
    profile_name: str
    passed: bool
    agent_response: Any
    expected_response: Any
    execution_time: float
    error: Optional[str]
```

### 8. `utils.py` - Helper Functions

Utility functions for common operations:
- JSON serialization
- Timestamp formatting
- Path management
- Logging configuration

---

## 📊 Evaluation Metrics

### Pass/Fail Criteria

A test passes if:
1. **Response Valid**: Agent returns a well-formed response
2. **Query Correct**: Generated MongoDB query is semantically correct
3. **Results Match**: Results match ground truth (structurally or semantically)
4. **No Errors**: Execution completed without errors

### Metrics Tracked

| Metric | Description |
|--------|-------------|
| **Pass Rate** | Percentage of tests passed |
| **Avg Execution Time** | Mean time per test |
| **Confidence Score** | Average semantic similarity |
| **Category Performance** | Pass rate by difficulty |
| **Error Rate** | Percentage of tests with errors |
| **Timeout Rate** | Percentage of tests exceeding timeout |

### Performance Benchmarks

**Expected Performance:**
- Basic queries: 95%+ pass rate
- Intermediate queries: 85%+ pass rate
- Advanced queries: 70%+ pass rate
- Ultra queries: 50%+ pass rate

---

## 🏃 Running Evaluations

### Standard Evaluation

```bash
# Full evaluation with defaults
python eval_system.py

# With custom API endpoint
python eval_system.py --api-url http://production-api:8000

# With specific database
python eval_system.py \
  --mongo-uri mongodb://localhost:27017 \
  --database my_db \
  --collection my_collection
```

### Multi-Profile Evaluation

Compare multiple models or configurations:

```bash
python eval_system.py \
  --profiles \
    "high-quality=gpt-5:high:20" \
    "fast=gpt-5-mini:low:10" \
    "balanced=gpt-5:medium:10"
```

**Profile Format:**
```
label=model:reasoning_effort:max_results
```

**Examples:**
- `gpt-5:high:10` - GPT-5 with high reasoning, 10 results
- `fast=gpt-5-mini:low:5` - Labeled "fast", GPT-5-mini, low reasoning, 5 results
- `gpt-5` - Just model name (uses defaults for other params)

### Semantic Comparison Modes

```bash
# Auto-select best comparison strategy
python eval_system.py --semantic-mode auto

# Force LLM-based comparison
python eval_system.py --semantic-mode llm

# Use heuristic comparison only
python eval_system.py --semantic-mode heuristic
```

### Custom Thresholds

```bash
# Require 90% pass rate for success
python eval_system.py --pass-threshold 0.9

# Lenient threshold for experimentation
python eval_system.py --pass-threshold 0.5
```

### Timeout Configuration

```bash
# Increase timeout for complex queries
python eval_system.py --request-timeout 120

# Quick testing with short timeout
python eval_system.py --request-timeout 30
```

---

## 📈 Interpreting Results

### Summary Report

```
=== Evaluation Summary ===
Profile: gpt-5-high-k10
Total Tests: 32
Passed: 28
Failed: 4
Pass Rate: 87.5%
Avg Execution Time: 2.34s

By Category:
  basic: 5/5 (100%)
  intermediate: 10/10 (100%)
  advanced: 10/12 (83.3%)
  ultra: 3/5 (60%)

Failed Tests:
  - advanced_008: Timeout (90s)
  - advanced_011: Query syntax error
  - ultra_002: Result mismatch (confidence: 0.45)
  - ultra_004: Unexpected error
```

### JSON Report Structure

```json
{
  "evaluation_id": "eval_20251104_123456",
  "timestamp": "2025-11-04T12:34:56Z",
  "profiles": [...],
  "test_results": [
    {
      "test_id": "basic_001",
      "profile": "gpt-5:high:10",
      "passed": true,
      "execution_time": 1.23,
      "agent_response": {...},
      "expected_response": {...},
      "comparison": {
        "method": "structural",
        "confidence": 1.0
      }
    }
  ],
  "summary": {
    "total_tests": 32,
    "passed": 28,
    "failed": 4,
    "pass_rate": 0.875,
    "avg_time": 2.34
  }
}
```

### Understanding Failures

**Common Failure Types:**

1. **Timeout Failures**
   - Agent took too long to respond
   - Increase `--request-timeout`
   - Check API performance

2. **Query Syntax Errors**
   - Invalid MongoDB query generated
   - Indicates model reasoning issues
   - Review agent prompts

3. **Result Mismatches**
   - Query correct but results differ
   - Check semantic comparison confidence
   - May indicate ground truth issues

4. **Unexpected Errors**
   - API errors, network issues
   - Check logs for details
   - Verify service health

---

## 🛠️ Custom Tests

### Adding New Test Cases

Edit `test_catalog.py`:

```python
def load_test_cases() -> List[TestCase]:
    return [
        # ... existing tests ...
        TestCase(
            id="custom_001",
            category="advanced",
            difficulty="hard",
            question="Your natural language question here",
            expected_type="aggregation",
            description="What this test validates",
            ground_truth_query=[
                {"$match": {"field": "value"}},
                {"$group": {"_id": "$field", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
        )
    ]
```

### Test Case Guidelines

1. **Clear Questions**: Use unambiguous natural language
2. **Ground Truth**: Verify queries return correct results
3. **Categorization**: Assign appropriate difficulty
4. **Documentation**: Add clear descriptions
5. **Edge Cases**: Include boundary conditions

### Validation Before Adding

```bash
# Test your new case individually
python -c "
from test_catalog import load_test_cases
from runner import EvaluationRunner

cases = load_test_cases()
runner = EvaluationRunner(...)
result = runner.run_single_test(cases[-1])  # Your new test
print(result)
"
```

---

## 🔬 Advanced Usage

### Programmatic Usage

```python
from eval_system import EvaluationRunner
from models import EvalProfile, TestCase
from test_catalog import load_test_cases

# Configure
profile = EvalProfile(
    name="my-profile",
    model="gpt-5",
    reasoning_effort="high",
    max_results=10
)

# Initialize
runner = EvaluationRunner(
    profiles=[profile],
    api_url="http://localhost:8000",
    mongo_uri="mongodb://localhost:27017",
    output_dir="./results"
)

# Run
test_cases = load_test_cases()
results = runner.run_evaluation(test_cases)

# Analyze
for result in results:
    if not result.passed:
        print(f"Failed: {result.test_id} - {result.error}")
```

### Custom Comparators

Implement custom comparison logic:

```python
from comparators import BaseComparator

class MyComparator(BaseComparator):
    def compare(self, expected, actual, question=None):
        # Your comparison logic
        is_match = your_logic_here(expected, actual)
        confidence = calculate_confidence(expected, actual)
        return is_match, confidence

# Use in runner
runner = EvaluationRunner(
    comparator=MyComparator(),
    ...
)
```

### Filtering Tests

Run specific test categories:

```python
# Load and filter
all_tests = load_test_cases()
basic_tests = [t for t in all_tests if t.category == "basic"]
hard_tests = [t for t in all_tests if t.difficulty == "hard"]

# Run filtered
runner.run_evaluation(basic_tests)
```

### Parallel Execution

The framework supports concurrent test execution:

```python
runner = EvaluationRunner(
    max_workers=4,  # Run 4 tests in parallel
    ...
)
```

### Custom Reporting

Generate custom reports:

```python
from reporter import Reporter

reporter = Reporter(output_dir="./reports")
results = runner.run_evaluation(test_cases)

# Standard reports
reporter.generate_json_report(results)
reporter.generate_summary(results)

# Custom analysis
import pandas as pd
df = pd.DataFrame([r.__dict__ for r in results])
print(df.groupby('category')['passed'].mean())
```

---

## 📝 Requirements

```txt
# Core dependencies
pymongo>=4.6.0
requests>=2.31.0
python-dotenv>=1.0.0

# Optional for semantic comparison
openai>=1.3.0

# Testing and development
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

---

## 🐛 Debugging

### Enable Verbose Logging

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or modify eval_system.py
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Individual Tests

```python
# Load specific test
from test_catalog import load_test_cases
tests = load_test_cases()
test = next(t for t in tests if t.id == "advanced_003")

# Print ground truth query
import json
print(json.dumps(test.ground_truth_query, indent=2))

# Run against MongoDB directly
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017")
db = client.government_procurement
result = list(db.purchase_orders.aggregate(test.ground_truth_query))
print(result)
```

### API Communication Issues

```bash
# Test API manually
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test question", "reasoning_effort": "medium"}'

# Check API logs
docker-compose logs -f api
```

---

## 📚 Additional Resources

- **Main Project README**: [../README.md](../README.md)
- **Schema Documentation**: [../docs/SCHEMA.md](../docs/SCHEMA.md)
- **API Documentation**: http://localhost:8000/docs
- **MongoDB Aggregation**: https://www.mongodb.com/docs/manual/aggregation/

---

## 🤝 Contributing

Contributions to improve the evaluation framework are welcome!

**Areas for Contribution:**
- Additional test cases
- New comparison strategies
- Performance optimizations
- Better error handling
- Documentation improvements

---

## 📄 License

This evaluation framework is part of the Government Procurement Data System and is licensed under the MIT License.

---

**Last Updated**: November 2025
**Version**: 1.0.0
