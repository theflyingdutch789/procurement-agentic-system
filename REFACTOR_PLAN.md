# Production-Ready Refactor Plan

## Executive Summary

Current system is a prototype with AI generating raw MongoDB pipelines directly. This is unreliable, untestable, and unmaintainable. We will refactor to a **proper layered architecture** where AI only handles intent understanding, and deterministic code handles query building.

---

## Problem Analysis

### Current Architecture (What's Wrong)

```
User Question
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    MONOLITHIC AI AGENT                       │
│                                                              │
│  • 17+ prompt rules                                         │
│  • AI generates raw MongoDB pipelines                        │
│  • Retry 3x on failure                                       │
│  • No validation                                             │
│  • No type safety                                            │
│  • Unpredictable behavior                                    │
│  • Debugging nightmare                                       │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
MongoDB (pray it works)
```

### Specific Problems

| Problem | Impact | Root Cause |
|---------|--------|------------|
| AI generates invalid pipelines | Query failures | No schema validation |
| "Purchase order" ambiguity | Wrong results | No semantic layer |
| Prompt is 100+ lines | High token cost, still fails | Prompt doing code's job |
| Retry as error handling | Unreliable, slow | No proper validation |
| Can't unit test | Bugs in production | AI is non-deterministic |
| Hard to debug | Long resolution time | No separation of concerns |

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Question                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              LAYER 1: INTENT EXTRACTOR (AI)                  │
│                                                              │
│  • Simple prompt: "What does the user want?"                │
│  • Returns STRUCTURED intent (Pydantic model)                │
│  • Uses OpenAI structured output / function calling          │
│  • Detects ambiguity → asks for clarification               │
│                                                              │
│  Input:  "Top 5 departments by spending"                     │
│  Output: QueryIntent(action=TOP_N, group_by=DEPARTMENT,      │
│                      metric=SPENDING, limit=5)               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           LAYER 2: SEMANTIC MAPPING (Code)                   │
│                                                              │
│  • Maps business terms to database fields                    │
│  • DEPARTMENT → department.normalized_name                   │
│  • SPENDING → item.total_price                               │
│  • Pure Python, no AI                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           LAYER 3: QUERY BUILDER (Code)                      │
│                                                              │
│  • Deterministic pipeline construction                       │
│  • 100% testable with unit tests                            │
│  • Type-safe, predictable                                    │
│  • Handles all query patterns                                │
│                                                              │
│  Input:  QueryIntent(...)                                    │
│  Output: [{"$group": {...}}, {"$sort": {...}}, ...]         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           LAYER 4: VALIDATOR (Code)                          │
│                                                              │
│  • Validates pipeline before execution                       │
│  • Checks for dangerous operations                           │
│  • Enforces limits and security                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           LAYER 5: EXECUTOR (Code)                           │
│                                                              │
│  • Executes validated pipeline                               │
│  • Handles timeouts                                          │
│  • Returns structured results                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           LAYER 6: RESPONSE GENERATOR (AI)                   │
│                                                              │
│  • Converts results to natural language                      │
│  • Simple task, low error rate                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Design

### 1. Intent Schema (Pydantic Models)

```python
# src/api/services/query_engine/models/intent.py

from enum import Enum
from typing import Optional, List, Union
from pydantic import BaseModel, Field


class QueryAction(str, Enum):
    """What type of query the user wants"""
    LIST = "list"              # "Show me orders..."
    COUNT = "count"            # "How many..."
    TOP_N = "top_n"            # "Top 5..."
    BOTTOM_N = "bottom_n"      # "Lowest 5..."
    AGGREGATE = "aggregate"    # "Total spending by..."
    SINGLE_VALUE = "single"    # "What is the total..."
    COMPARE = "compare"        # "Compare X vs Y..."
    TREND = "trend"            # "Spending over time..."


class MetricField(str, Enum):
    """Measurable fields (for aggregation)"""
    SPENDING = "spending"           # item.total_price
    QUANTITY = "quantity"           # item.quantity
    UNIT_PRICE = "unit_price"       # item.unit_price
    ORDER_COUNT = "order_count"     # count of documents


class DimensionField(str, Enum):
    """Groupable/filterable fields"""
    DEPARTMENT = "department"               # department.normalized_name
    SUPPLIER = "supplier"                   # supplier.name
    FISCAL_YEAR = "fiscal_year"             # dates.fiscal_year
    ACQUISITION_TYPE = "acquisition_type"   # acquisition.type
    ITEM_NAME = "item_name"                 # item.name
    ITEM_DESCRIPTION = "item_description"   # item.description
    PO_NUMBER = "po_number"                 # po_number
    SUPPLIER_ZIP = "supplier_zip"           # supplier.zip_code
    CLASSIFICATION = "classification"       # classification.segment_title
    CAL_CARD = "cal_card"                   # cal_card (boolean)


class FilterOperator(str, Enum):
    """Filter comparison operators"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_OR_EQUAL = "gte"
    LESS_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "nin"
    CONTAINS = "contains"      # Regex match
    STARTS_WITH = "starts_with"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class AggregateFunction(str, Enum):
    """Aggregation functions"""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"


class SortOrder(str, Enum):
    """Sort direction"""
    ASC = "asc"
    DESC = "desc"


class Filter(BaseModel):
    """A single filter condition"""
    field: DimensionField
    operator: FilterOperator
    value: Optional[Union[str, int, float, bool, List[str]]] = None

    class Config:
        use_enum_values = True


class QueryIntent(BaseModel):
    """
    Structured representation of user's query intent.
    This is what the AI extracts from natural language.
    """
    # Core action
    action: QueryAction

    # What to measure (for aggregations)
    metric: Optional[MetricField] = None
    aggregate_function: AggregateFunction = AggregateFunction.SUM

    # How to group results
    group_by: Optional[DimensionField] = None

    # Filtering conditions
    filters: List[Filter] = Field(default_factory=list)

    # Sorting
    sort_by: Optional[Union[MetricField, DimensionField]] = None
    sort_order: SortOrder = SortOrder.DESC

    # Result limiting
    limit: int = Field(default=10, ge=1, le=1000)

    # Fields to include in output (for LIST action)
    select_fields: List[DimensionField] = Field(default_factory=list)

    # Ambiguity handling
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    suggested_interpretations: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True
```

### 2. Semantic Field Mappings

```python
# src/api/services/query_engine/field_mappings.py

from typing import Dict, Any
from .models.intent import MetricField, DimensionField


class FieldMapper:
    """Maps semantic field names to MongoDB field paths"""

    # Metric fields (measurable, numeric)
    METRIC_MAPPINGS: Dict[str, str] = {
        MetricField.SPENDING: "item.total_price",
        MetricField.QUANTITY: "item.quantity",
        MetricField.UNIT_PRICE: "item.unit_price",
        MetricField.ORDER_COUNT: "__COUNT__",  # Special marker for $sum: 1
    }

    # Dimension fields (groupable, filterable)
    DIMENSION_MAPPINGS: Dict[str, str] = {
        DimensionField.DEPARTMENT: "department.normalized_name",
        DimensionField.SUPPLIER: "supplier.name",
        DimensionField.FISCAL_YEAR: "dates.fiscal_year",
        DimensionField.ACQUISITION_TYPE: "acquisition.type",
        DimensionField.ITEM_NAME: "item.name",
        DimensionField.ITEM_DESCRIPTION: "item.description",
        DimensionField.PO_NUMBER: "po_number",
        DimensionField.SUPPLIER_ZIP: "supplier.zip_code",
        DimensionField.CLASSIFICATION: "classification.segment_title",
        DimensionField.CAL_CARD: "cal_card",
    }

    # Fields that need null handling in aggregations
    NULLABLE_METRICS = {MetricField.SPENDING, MetricField.QUANTITY, MetricField.UNIT_PRICE}

    # Default sort fields per action type
    DEFAULT_SORT_FIELDS = {
        "top_n": "metric",      # Sort by the metric being measured
        "bottom_n": "metric",
        "list": "item.total_price",
        "aggregate": "metric",
    }

    @classmethod
    def get_mongo_field(cls, field: str) -> str:
        """Convert semantic field to MongoDB path"""
        if field in cls.METRIC_MAPPINGS:
            return cls.METRIC_MAPPINGS[field]
        if field in cls.DIMENSION_MAPPINGS:
            return cls.DIMENSION_MAPPINGS[field]
        raise ValueError(f"Unknown field: {field}")

    @classmethod
    def needs_null_handling(cls, field: str) -> bool:
        """Check if field needs $ifNull wrapper"""
        return field in cls.NULLABLE_METRICS
```

### 3. Query Builder

```python
# src/api/services/query_engine/query_builder.py

from typing import List, Dict, Any, Optional
from .models.intent import (
    QueryIntent, QueryAction, AggregateFunction,
    Filter, FilterOperator, SortOrder
)
from .field_mappings import FieldMapper


class QueryBuilder:
    """
    Deterministic MongoDB pipeline builder.
    No AI, no randomness - pure code.
    """

    def __init__(self):
        self.mapper = FieldMapper()

    def build(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        """Build MongoDB aggregation pipeline from intent"""

        if intent.is_ambiguous:
            raise ValueError(f"Cannot build query: {intent.ambiguity_reason}")

        # Route to appropriate builder method
        builder_method = {
            QueryAction.LIST: self._build_list,
            QueryAction.COUNT: self._build_count,
            QueryAction.TOP_N: self._build_top_n,
            QueryAction.BOTTOM_N: self._build_bottom_n,
            QueryAction.AGGREGATE: self._build_aggregate,
            QueryAction.SINGLE_VALUE: self._build_single_value,
        }.get(intent.action)

        if not builder_method:
            raise ValueError(f"Unsupported action: {intent.action}")

        return builder_method(intent)

    # ─────────────────────────────────────────────────────────────
    # Builder Methods (one per action type)
    # ─────────────────────────────────────────────────────────────

    def _build_list(self, intent: QueryIntent) -> List[Dict]:
        """Build pipeline for LIST action (show records)"""
        pipeline = []

        # 1. Filter
        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        # 2. Sort
        sort_field = self._get_sort_field(intent, default="item.total_price")
        sort_dir = 1 if intent.sort_order == SortOrder.ASC else -1
        pipeline.append({"$sort": {sort_field: sort_dir}})

        # 3. Limit
        pipeline.append({"$limit": intent.limit})

        # 4. Project (optional - select specific fields)
        if intent.select_fields:
            pipeline.append({"$project": self._build_projection(intent.select_fields)})

        return pipeline

    def _build_count(self, intent: QueryIntent) -> List[Dict]:
        """Build pipeline for COUNT action"""
        pipeline = []

        # 1. Filter
        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        # 2. Count
        pipeline.append({"$count": "count"})

        return pipeline

    def _build_top_n(self, intent: QueryIntent) -> List[Dict]:
        """Build pipeline for TOP_N action"""
        pipeline = []

        # 1. Filter
        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        # 2. Group (if group_by specified)
        if intent.group_by:
            pipeline.append(self._build_group_stage(intent))

        # 3. Sort (descending for top)
        sort_field = self._get_sort_field_for_aggregation(intent)
        pipeline.append({"$sort": {sort_field: -1}})

        # 4. Limit
        pipeline.append({"$limit": intent.limit})

        return pipeline

    def _build_bottom_n(self, intent: QueryIntent) -> List[Dict]:
        """Build pipeline for BOTTOM_N action"""
        pipeline = self._build_top_n(intent)
        # Change sort to ascending
        for stage in pipeline:
            if "$sort" in stage:
                for field in stage["$sort"]:
                    stage["$sort"][field] = 1
        return pipeline

    def _build_aggregate(self, intent: QueryIntent) -> List[Dict]:
        """Build pipeline for AGGREGATE action (group by)"""
        pipeline = []

        # 1. Filter
        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        # 2. Group
        pipeline.append(self._build_group_stage(intent))

        # 3. Sort
        sort_field = self._get_sort_field_for_aggregation(intent)
        sort_dir = 1 if intent.sort_order == SortOrder.ASC else -1
        pipeline.append({"$sort": {sort_field: sort_dir}})

        # 4. Limit
        pipeline.append({"$limit": intent.limit})

        return pipeline

    def _build_single_value(self, intent: QueryIntent) -> List[Dict]:
        """Build pipeline for SINGLE_VALUE action (e.g., total spending)"""
        pipeline = []

        # 1. Filter
        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        # 2. Group with null _id (aggregate all)
        pipeline.append(self._build_group_stage(intent, group_all=True))

        return pipeline

    # ─────────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────────

    def _build_match(self, filters: List[Filter]) -> Dict[str, Any]:
        """Build $match stage from filters"""
        conditions = {}

        for f in filters:
            mongo_field = FieldMapper.get_mongo_field(f.field)
            condition = self._filter_to_condition(f)
            conditions[mongo_field] = condition

        return conditions

    def _filter_to_condition(self, f: Filter) -> Any:
        """Convert Filter to MongoDB condition"""
        op_map = {
            FilterOperator.EQUALS: lambda v: v,
            FilterOperator.NOT_EQUALS: lambda v: {"$ne": v},
            FilterOperator.GREATER_THAN: lambda v: {"$gt": v},
            FilterOperator.LESS_THAN: lambda v: {"$lt": v},
            FilterOperator.GREATER_OR_EQUAL: lambda v: {"$gte": v},
            FilterOperator.LESS_OR_EQUAL: lambda v: {"$lte": v},
            FilterOperator.IN: lambda v: {"$in": v if isinstance(v, list) else [v]},
            FilterOperator.NOT_IN: lambda v: {"$nin": v if isinstance(v, list) else [v]},
            FilterOperator.CONTAINS: lambda v: {"$regex": v, "$options": "i"},
            FilterOperator.STARTS_WITH: lambda v: {"$regex": f"^{v}", "$options": "i"},
            FilterOperator.IS_NULL: lambda v: None,
            FilterOperator.IS_NOT_NULL: lambda v: {"$ne": None},
        }

        return op_map[f.operator](f.value)

    def _build_group_stage(self, intent: QueryIntent, group_all: bool = False) -> Dict:
        """Build $group stage"""
        group_id = None if group_all else f"${FieldMapper.get_mongo_field(intent.group_by)}"

        metric_field = FieldMapper.get_mongo_field(intent.metric) if intent.metric else None

        # Build accumulator
        accumulator = self._build_accumulator(
            intent.aggregate_function,
            metric_field
        )

        return {
            "$group": {
                "_id": group_id,
                "value": accumulator,
                "count": {"$sum": 1}  # Always include count
            }
        }

    def _build_accumulator(self, func: AggregateFunction, field: Optional[str]) -> Dict:
        """Build aggregation accumulator with null handling"""

        if func == AggregateFunction.COUNT:
            return {"$sum": 1}

        if func == AggregateFunction.COUNT_DISTINCT:
            return {"$addToSet": f"${field}"}

        # For SUM, AVG, MIN, MAX - handle nulls
        field_ref = {"$ifNull": [f"${field}", 0]} if field else 0

        func_map = {
            AggregateFunction.SUM: "$sum",
            AggregateFunction.AVG: "$avg",
            AggregateFunction.MIN: "$min",
            AggregateFunction.MAX: "$max",
        }

        return {func_map[func]: field_ref}

    def _get_sort_field(self, intent: QueryIntent, default: str) -> str:
        """Get sort field for non-aggregation queries"""
        if intent.sort_by:
            return FieldMapper.get_mongo_field(intent.sort_by)
        return default

    def _get_sort_field_for_aggregation(self, intent: QueryIntent) -> str:
        """Get sort field for aggregation queries"""
        return "value"  # Always sort by computed value in aggregations

    def _build_projection(self, fields: List[str]) -> Dict[str, int]:
        """Build $project stage"""
        projection = {"_id": 0}
        for field in fields:
            mongo_field = FieldMapper.get_mongo_field(field)
            projection[mongo_field] = 1
        return projection
```

### 4. Intent Extractor (AI Component)

```python
# src/api/services/query_engine/intent_extractor.py

import json
from typing import Optional
from openai import OpenAI
from .models.intent import QueryIntent


# JSON Schema for structured output
INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["list", "count", "top_n", "bottom_n", "aggregate", "single", "compare", "trend"]
        },
        "metric": {
            "type": "string",
            "enum": ["spending", "quantity", "unit_price", "order_count"],
            "description": "What to measure"
        },
        "aggregate_function": {
            "type": "string",
            "enum": ["sum", "avg", "min", "max", "count", "count_distinct"],
            "default": "sum"
        },
        "group_by": {
            "type": "string",
            "enum": ["department", "supplier", "fiscal_year", "acquisition_type", "item_name", "po_number", "classification", "cal_card"],
            "description": "Field to group results by"
        },
        "filters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "operator": {"type": "string", "enum": ["eq", "ne", "gt", "lt", "gte", "lte", "in", "nin", "contains"]},
                    "value": {}
                },
                "required": ["field", "operator", "value"]
            }
        },
        "sort_order": {
            "type": "string",
            "enum": ["asc", "desc"],
            "default": "desc"
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 1000,
            "default": 10
        },
        "is_ambiguous": {
            "type": "boolean",
            "default": False
        },
        "ambiguity_reason": {
            "type": "string"
        }
    },
    "required": ["action"]
}


EXTRACTION_PROMPT = """You are an intent extractor for a procurement database query system.

Your job is to understand what the user wants and return a structured intent object.
Do NOT generate database queries. Only extract the user's intent.

DATABASE CONTEXT:
- Each record is a purchase order line item
- Fields available:
  * spending (item.total_price) - the dollar amount
  * quantity - number of items
  * department - government department name
  * supplier - vendor/supplier name
  * fiscal_year - e.g., "2013-2014"
  * acquisition_type - "IT Goods", "IT Services", "NON-IT Goods", "NON-IT Services"
  * item_name - name of the purchased item
  * po_number - purchase order number
  * cal_card - whether CalCard was used (true/false)

ACTIONS:
- list: Show individual records ("show me orders", "list purchases")
- count: Count records ("how many orders")
- top_n: Top N by some metric ("top 5 departments by spending")
- bottom_n: Bottom N ("lowest spending departments")
- aggregate: Group and summarize ("spending by fiscal year")
- single: Single computed value ("total spending", "average order value")

RULES:
1. "Top N X by Y" → action=top_n, group_by=X, metric=Y
2. "How many" → action=count
3. "Total/sum of" → action=single, aggregate_function=sum
4. "Average" → aggregate_function=avg
5. If user says "orders" or "purchase orders" without "grouped" or "by PO", treat as individual records
6. If genuinely ambiguous, set is_ambiguous=true and explain why

Return ONLY the JSON object matching the schema."""


class IntentExtractor:
    """Extract structured query intent from natural language"""

    def __init__(self, client: OpenAI, model: str = "gpt-4o"):
        self.client = client
        self.model = model

    def extract(self, question: str, conversation_context: Optional[str] = None) -> QueryIntent:
        """Extract intent from user question"""

        prompt = EXTRACTION_PROMPT
        if conversation_context:
            prompt += f"\n\nPREVIOUS CONTEXT:\n{conversation_context}"

        prompt += f"\n\nUSER QUESTION: {question}"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "query_intent",
                    "schema": INTENT_SCHEMA,
                    "strict": True
                }
            },
            temperature=0  # Deterministic
        )

        intent_data = json.loads(response.choices[0].message.content)
        return QueryIntent(**intent_data)
```

### 5. Validator

```python
# src/api/services/query_engine/validator.py

from typing import List, Dict, Any, Tuple, Optional
from .models.intent import QueryIntent, QueryAction


class QueryValidator:
    """Validate intents and pipelines before execution"""

    MAX_LIMIT = 1000
    DANGEROUS_OPERATORS = {"$where", "$function", "$accumulator"}

    def validate_intent(self, intent: QueryIntent) -> Tuple[bool, Optional[str]]:
        """Validate intent before building query"""

        # Check for ambiguity
        if intent.is_ambiguous:
            return False, f"Ambiguous query: {intent.ambiguity_reason}"

        # Validate action requirements
        if intent.action in [QueryAction.TOP_N, QueryAction.BOTTOM_N, QueryAction.AGGREGATE]:
            if not intent.metric and not intent.group_by:
                return False, "Aggregation requires metric or group_by"

        # Validate limit
        if intent.limit > self.MAX_LIMIT:
            return False, f"Limit exceeds maximum ({self.MAX_LIMIT})"

        return True, None

    def validate_pipeline(self, pipeline: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """Validate pipeline before execution"""

        # Check for dangerous operators
        pipeline_str = str(pipeline)
        for op in self.DANGEROUS_OPERATORS:
            if op in pipeline_str:
                return False, f"Dangerous operator not allowed: {op}"

        # Check pipeline structure
        if not pipeline:
            return False, "Empty pipeline"

        # Must end with $limit
        last_stage = pipeline[-1]
        if "$limit" not in last_stage and "$count" not in last_stage:
            return False, "Pipeline must have $limit or $count"

        return True, None
```

### 6. Refactored Agent

```python
# src/api/services/query_engine/agent.py

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from openai import OpenAI
from pymongo import MongoClient

from .models.intent import QueryIntent
from .intent_extractor import IntentExtractor
from .query_builder import QueryBuilder
from .validator import QueryValidator
from .executor import QueryExecutor
from .summarizer import ResponseSummarizer


logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Production-ready query engine with clean architecture.

    Flow:
    1. Intent Extraction (AI) → Structured Intent
    2. Validation (Code) → Validated Intent
    3. Query Building (Code) → MongoDB Pipeline
    4. Pipeline Validation (Code) → Validated Pipeline
    5. Execution (Code) → Results
    6. Summarization (AI) → Natural Language Response
    """

    def __init__(
        self,
        *,
        mongo_client: MongoClient,
        database_name: str,
        collection_name: str,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else OpenAI()
        self.collection = mongo_client[database_name][collection_name]

        # Initialize components
        self.intent_extractor = IntentExtractor(self.client, model)
        self.query_builder = QueryBuilder()
        self.validator = QueryValidator()
        self.executor = QueryExecutor(self.collection)
        self.summarizer = ResponseSummarizer(self.client, model)

        self.logger = logging.getLogger(__name__)

    def query(
        self,
        question: str,
        *,
        conversation_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a natural language query"""

        try:
            # Step 1: Extract intent
            self.logger.info(f"Extracting intent for: {question}")
            intent = self.intent_extractor.extract(question, conversation_context)
            self.logger.info(f"Extracted intent: {intent.action}, group_by={intent.group_by}")

            # Step 2: Handle ambiguity
            if intent.is_ambiguous:
                return {
                    "success": False,
                    "needs_clarification": True,
                    "clarification_prompt": intent.ambiguity_reason,
                    "suggestions": intent.suggested_interpretations,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Step 3: Validate intent
            valid, error = self.validator.validate_intent(intent)
            if not valid:
                return self._error_response(f"Invalid intent: {error}")

            # Step 4: Build pipeline
            pipeline = self.query_builder.build(intent)
            self.logger.info(f"Built pipeline with {len(pipeline)} stages")

            # Step 5: Validate pipeline
            valid, error = self.validator.validate_pipeline(pipeline)
            if not valid:
                return self._error_response(f"Invalid pipeline: {error}")

            # Step 6: Execute
            results, execution_time = self.executor.execute(pipeline)
            self.logger.info(f"Query returned {len(results)} results in {execution_time:.2f}s")

            # Step 7: Summarize
            answer = self.summarizer.summarize(question, results, intent)

            return {
                "success": True,
                "answer": answer,
                "results": results,
                "result_count": len(results),
                "pipeline": pipeline,
                "intent": intent.model_dump(),
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as exc:
            self.logger.error(f"Query failed: {exc}", exc_info=True)
            return self._error_response(str(exc))

    def _error_response(self, error: str) -> Dict[str, Any]:
        return {
            "success": False,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        }
```

---

## File Structure

```
src/api/services/
├── mongodb_agent/          # OLD (keep for reference, then delete)
│   └── ...
│
└── query_engine/           # NEW
    ├── __init__.py
    ├── models/
    │   ├── __init__.py
    │   └── intent.py       # QueryIntent, Filter, enums
    ├── field_mappings.py   # Semantic layer
    ├── intent_extractor.py # AI extracts intent
    ├── query_builder.py    # Deterministic pipeline builder
    ├── validator.py        # Validation logic
    ├── executor.py         # Pipeline execution
    ├── summarizer.py       # AI summarizes results
    └── agent.py            # Orchestrator (QueryEngine)
```

---

## Implementation Schedule

### Day 1 (Wednesday): Foundation
| Time | Task | Output |
|------|------|--------|
| 2h | Create models/intent.py | Pydantic models, enums |
| 2h | Create field_mappings.py | FieldMapper class |
| 2h | Write unit tests for models | test_models.py |
| 1h | Review and refine | Clean code |

### Day 2 (Thursday): Query Builder
| Time | Task | Output |
|------|------|--------|
| 3h | Create query_builder.py | QueryBuilder class |
| 2h | Unit tests for builder | test_query_builder.py |
| 2h | Test with known queries | Verified pipelines |

### Day 3 (Friday): Intent Extractor + Integration
| Time | Task | Output |
|------|------|--------|
| 2h | Create intent_extractor.py | IntentExtractor class |
| 2h | Create validator.py | QueryValidator class |
| 3h | Create agent.py (QueryEngine) | Full orchestrator |
| 1h | Integration tests | Working system |

### Day 4 (Saturday): API + Testing
| Time | Task | Output |
|------|------|--------|
| 2h | Update API routes | Use new QueryEngine |
| 3h | End-to-end testing | All queries working |
| 2h | Fix bugs | Stable system |
| 1h | Performance testing | Acceptable speed |

### Day 5 (Sunday): Polish + Demo
| Time | Task | Output |
|------|------|--------|
| 2h | Final testing | Everything works |
| 1h | Update documentation | Clean README |
| 1h | Prepare demo | Demo script ready |

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Reliability | 100% of test queries work correctly |
| Predictability | Same question → same pipeline (deterministic) |
| Testability | >80% unit test coverage on query_builder |
| Debuggability | Can trace any failure to specific component |
| Maintainability | Adding new query type = add one builder method |
| Performance | <3s average response time |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Not enough time | Core functionality first, polish later |
| AI extraction fails | Fallback to simple pattern matching |
| New query types | Designed for extensibility |
| Demo failure | Keep old system as backup |

---

## Rollback Plan

If the new system isn't ready by Sunday:
1. Keep old system running
2. Present old system but explain the refactor plan
3. Show the new architecture design as "in progress"
4. Demonstrate understanding of proper engineering

---

## Questions to Answer in Demo

**"Why this architecture?"**
> "AI is non-deterministic, so we minimize what AI does. AI only understands intent. Deterministic code builds queries. This gives us reliability, testability, and debuggability."

**"How do you handle new query types?"**
> "Add a new QueryAction enum value, add a builder method. The intent extractor learns from examples in the prompt. Fully extensible."

**"What if the AI misunderstands?"**
> "The intent is validated before execution. If ambiguous, we ask for clarification instead of guessing. Much better UX than wrong results."

---

Ready to implement? Let's start with Day 1 tasks.
