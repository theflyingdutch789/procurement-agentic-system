# Procurement Agentic System - Technical Architecture

> **Audience**: Technical leadership, CTOs, architects
> **Purpose**: System design overview with implementation details

---

## 1. Executive Summary

An AI-powered natural language interface for querying California state government procurement data (346K+ records, 2012-2015). The system converts plain English questions into MongoDB aggregation pipelines and returns human-readable answers.

**Core Innovation**: A hybrid query engine combining deterministic code-based query generation (80% of queries) with LLM fallback (20%), plus an **ambiguity detection layer** that proactively asks for clarification rather than guessing user intent.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│  ┌──────────────────────┐         ┌──────────────────────────────────────┐  │
│  │   Web Chat UI        │         │   Direct API Clients                 │  │
│  │   (Flask + JS)       │         │   (Swagger/curl/SDK)                 │  │
│  │   Port 5000          │         │                                      │  │
│  └──────────┬───────────┘         └──────────────────┬───────────────────┘  │
└─────────────┼────────────────────────────────────────┼──────────────────────┘
              │                                        │
              ▼                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER (FastAPI)                             │
│                              Port 8000                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  POST /api/ai/query                                                   │   │
│  │  • Request validation (Pydantic)                                      │   │
│  │  • Model/reasoning configuration                                      │   │
│  │  • Response serialization                                             │   │
│  │  src/api/routes/ai_query.py:144-263                                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────┬───────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HYBRID QUERY ENGINE                                  │
│                         (LangGraph State Machine)                            │
│  src/api/services/deterministic_engine/agent.py:215-569                      │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        ROUTING LAYER                                    │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────────┐  │ │
│  │  │ Intent          │───▶│ Ambiguity       │───▶│ Action Router      │  │ │
│  │  │ Extraction      │    │ Detection       │    │                    │  │ │
│  │  │ (GPT-5-mini)    │    │ (Hybrid)        │    │ Supported? → Det.  │  │ │
│  │  │                 │    │                 │    │ Complex? → Fallback│  │ │
│  │  └─────────────────┘    └─────────────────┘    └────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                    │                    │                    │               │
│         ┌─────────┘          ┌─────────┘          ┌─────────┘               │
│         ▼                    ▼                    ▼                         │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────────────┐         │
│  │ AMBIGUOUS   │      │DETERMINISTIC│      │   AI FALLBACK       │         │
│  │             │      │   ENGINE    │      │                     │         │
│  │ Return      │      │             │      │ LangGraphAgent      │         │
│  │ clarify     │      │ Code-built  │      │ (GPT-5 + retries)   │         │
│  │ prompt      │      │ pipelines   │      │                     │         │
│  │             │      │ ~80% queries│      │ ~20% queries        │         │
│  └─────────────┘      └──────┬──────┘      └──────────┬──────────┘         │
│                              │                        │                     │
│                              └───────────┬────────────┘                     │
│                                          ▼                                  │
│                              ┌─────────────────────┐                        │
│                              │  Query Executor     │                        │
│                              │  (30s timeout)      │                        │
│                              └──────────┬──────────┘                        │
│                                         │                                   │
│                                         ▼                                   │
│                              ┌─────────────────────┐                        │
│                              │  Response           │                        │
│                              │  Summarizer         │                        │
│                              │  (GPT-5-mini)       │                        │
│                              └─────────────────────┘                        │
└─────────────────────────────────────────┬───────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER (MongoDB)                              │
│                                                                              │
│  Database: government_procurement                                            │
│  Collection: purchase_orders (346,000+ documents)                           │
│  18+ strategic indexes                                                       │
│                                                                              │
│  Document Structure:                                                         │
│  {                                                                           │
│    purchase_order_number, requisition_number, lpa_number,                   │
│    dates: { creation, purchase, fiscal_year, fiscal_year_start },           │
│    department: { name, normalized_name },                                   │
│    supplier: { code, name, qualifications[], zip_code, location{GeoJSON} }, │
│    item: { name, description, quantity, unit_price, total_price },          │
│    classification: { unspsc: { segment, family, class, commodity } },       │
│    acquisition: { type, sub_type, method, sub_method },                     │
│    cal_card, metadata: { import_date, source_file }                         │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Ambiguity Detection System

### 3.1 Problem Statement

The procurement database stores **line items**, not purchase orders. A single PO can have multiple line items:

```
PO #4500123456
├── Doc 1: {item: "Laptop",   total_price: 60000}
├── Doc 2: {item: "Monitor",  total_price: 30000}
└── Doc 3: {item: "Keyboard", total_price: 2500}
```

When a user asks "Top 5 purchase orders by price", there are two valid interpretations:
1. Top 5 individual line items ranked by `item.total_price`
2. Top 5 POs ranked by sum of all their line items

**Without clarification, the system would guess and potentially return wrong results.**

### 3.2 Architecture: Hybrid Ambiguity Detection

We implement a **two-layer detection system** to catch ambiguity reliably:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AMBIGUITY DETECTION PIPELINE                  │
│                                                                  │
│  User Question                                                   │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  LAYER 1: LLM-Based Detection                            │    │
│  │  src/api/services/deterministic_engine/intent_extractor.py   │
│  │                                                          │    │
│  │  • AI evaluates semantic ambiguity                       │    │
│  │  • Sets is_ambiguous, ambiguity_reason, suggestions      │    │
│  │  • Flexible, catches novel patterns                      │    │
│  │  • Non-deterministic (may miss known patterns)           │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  LAYER 2: Deterministic Detection (Safety Net)           │    │
│  │  src/api/services/deterministic_engine/ambiguity_detector.py │
│  │                                                          │    │
│  │  • Pattern-matching for known ambiguity cases            │    │
│  │  • Catches PO vs line-item confusion                     │    │
│  │  • Catches missing metric specifications                 │    │
│  │  • 100% reliable for defined patterns                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Intent Sanitizer (Coordinator)                          │    │
│  │  src/api/services/deterministic_engine/intent_sanitizer.py   │
│  │                                                          │    │
│  │  • Runs both detection layers                            │    │
│  │  • Skips detection on clarification responses            │    │
│  │  • Normalizes intent for downstream processing           │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       ▼                                                          │
│   Ambiguous? ──Yes──▶ Return clarification prompt               │
│       │                                                          │
│       No                                                         │
│       │                                                          │
│       ▼                                                          │
│   Continue to query execution                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Implementation Details

#### Layer 1: LLM-Based Detection (`intent_extractor.py:195-303`)

The intent extraction prompt includes explicit instructions for ambiguity detection:

```python
EXTRACTION_PROMPT = """
==============================================================================
AMBIGUITY DETECTION - THIS IS YOUR MOST IMPORTANT RESPONSIBILITY
==============================================================================

You MUST detect ambiguity when the user's question could reasonably be
interpreted in MULTIPLE WAYS given the data model above. When ambiguous, set:
  - is_ambiguous: true
  - ambiguity_reason: Clear explanation of why it's ambiguous
  - suggested_interpretations: 2-3 specific, actionable rephrased queries
    IMPORTANT: Preserve specific details from the original query

COMMON AMBIGUITY PATTERNS:
1. PURCHASE ORDER vs LINE ITEM: "Top 5 purchase orders by price"
2. MISSING METRIC: "Largest orders" (by spending? quantity? unit price?)
3. TIME PERIOD: "Year 2014" (calendar or fiscal year?)
4. AGGREGATION LEVEL: "Average order value" (per line or per PO?)
...
"""
```

Output schema includes ambiguity fields:

```python
INTENT_SCHEMA = {
    "properties": {
        "is_ambiguous": {"type": "boolean", "default": False},
        "ambiguity_reason": {"type": "string"},
        "suggested_interpretations": {"type": "array", "items": {"type": "string"}},
        # ... other intent fields
    }
}
```

#### Layer 2: Deterministic Detection (`ambiguity_detector.py:82-137`)

Pattern-matching for known ambiguity cases:

```python
def detect_ambiguity(question: str, intent: QueryIntent) -> Tuple[bool, Optional[str], List[str]]:
    """
    Returns: (is_ambiguous, reason, suggested_interpretations)
    """
    text = question.lower()

    # Pattern 1: Purchase Order Grouping Ambiguity
    if action in {QueryAction.TOP_N, QueryAction.BOTTOM_N}:
        mentions_po = any(p in text for p in PO_CONCEPT_PHRASES)
        has_explicit_grouping = any(p in text for p in EXPLICIT_PO_GROUPING)

        if mentions_po and not has_explicit_grouping:
            return (
                True,
                "Your question mentions 'purchase orders' but it's unclear...",
                [
                    f"Show top {limit} individual line items by price",
                    f"Show top {limit} purchase orders by total value",
                ]
            )

    # Pattern 2: Missing Metric Ambiguity
    if action in {QueryAction.TOP_N, QueryAction.BOTTOM_N}:
        has_vague_ranking = any(p in text for p in VAGUE_RANKING_PHRASES)
        has_explicit_metric = any(p in text for p in EXPLICIT_METRIC_PHRASES)

        if has_vague_ranking and not has_explicit_metric:
            return (
                True,
                "I need to clarify what metric you'd like to rank by:",
                ["By total spending", "By quantity ordered", "By unit price"]
            )

    return (False, None, [])
```

#### Intent Sanitizer Coordination (`intent_sanitizer.py:53-107`)

```python
def sanitize_intent(
    question: str,
    intent: QueryIntent,
    is_clarification_response: bool = False
) -> QueryIntent:
    """
    Hybrid approach:
    1. LLM may flag ambiguity during extraction
    2. Deterministic rules act as safety net for known patterns
    """
    # If LLM already flagged it, respect that
    if intent.is_ambiguous:
        return intent

    # Skip detection if user is responding to clarification
    if not is_clarification_response:
        is_ambiguous, reason, suggestions = detect_ambiguity(question, intent)
        if is_ambiguous:
            updated = intent.model_copy(deep=True)
            updated.is_ambiguous = True
            updated.ambiguity_reason = reason
            updated.suggested_interpretations = suggestions
            return updated

    # Continue with intent normalization...
    return updated
```

### 3.4 Clarification Response Format

When ambiguity is detected, the system returns:

```python
{
    "success": False,
    "answer": "Your question mentions 'purchase orders' but it's unclear...\n
               Possible interpretations:\n
               - Show top 5 individual line items by price\n
               - Show top 5 purchase orders by total value",
    "needs_clarification": True,
    "clarification_prompt": "Your question mentions 'purchase orders'...",
    "suggestions": [
        "Show top 5 individual line items by price",
        "Show top 5 purchase orders by total value"
    ],
    "error": "Ambiguous query"
}
```

The UI presents these as clickable options. When the user selects one, it's sent back with `is_clarification_response: true`, bypassing ambiguity detection.

---

## 4. Hybrid Query Engine

### 4.1 LangGraph State Machine

The engine uses LangGraph for orchestration with conditional routing:

```python
# src/api/services/deterministic_engine/agent.py:342-372

class HybridAgentState(TypedDict, total=False):
    question: str
    conversation_history: Optional[List[Dict[str, Any]]]
    intent: Optional[QueryIntent]
    route: Optional[str]  # "deterministic" | "fallback" | "stop"
    response: Optional[Dict[str, Any]]
    error: Optional[str]

def _build_graph(self):
    graph = StateGraph(HybridAgentState)

    graph.add_node("decide_route", self._route_node)
    graph.add_node("deterministic", self._deterministic_node)
    graph.add_node("fallback", self._fallback_node)

    graph.set_entry_point("decide_route")

    # Conditional routing based on intent analysis
    graph.add_conditional_edges(
        "decide_route",
        self._after_route,
        {"deterministic": "deterministic", "fallback": "fallback", "stop": END}
    )

    # Fallback if deterministic fails
    graph.add_conditional_edges(
        "deterministic",
        self._after_deterministic,
        {"fallback": "fallback", "stop": END}
    )

    graph.add_edge("fallback", END)
    return graph.compile()
```

### 4.2 Routing Logic

```python
# src/api/services/deterministic_engine/agent.py:374-415

SUPPORTED_ACTIONS = {
    QueryAction.LIST,         # "Show me orders..."
    QueryAction.COUNT,        # "How many..."
    QueryAction.TOP_N,        # "Top 5 departments..."
    QueryAction.BOTTOM_N,     # "Lowest spending..."
    QueryAction.AGGREGATE,    # "Spending by year..."
    QueryAction.SINGLE_VALUE, # "Total spending..."
    QueryAction.COMPARE,      # "Compare IT vs Non-IT..."
    QueryAction.TREND,        # "Spending trend..."
}

def _route_node(self, state: HybridAgentState) -> HybridAgentState:
    # 1. Extract intent
    intent = self.deterministic_engine.intent_extractor.extract(
        state["question"], conversation_context
    )

    # 2. Check ambiguity (LLM layer)
    if intent.is_ambiguous:
        state["response"] = self._clarification_response(intent)
        state["route"] = "stop"
        return state

    # 3. Apply deterministic ambiguity detection (safety net)
    intent = sanitize_intent(state["question"], intent)
    if intent.is_ambiguous:
        state["response"] = self._clarification_response(intent)
        state["route"] = "stop"
        return state

    # 4. Route based on action type
    if action in self.SUPPORTED_ACTIONS:
        state["route"] = "deterministic"
    else:
        state["route"] = "fallback"

    return state
```

### 4.3 Deterministic Engine Pipeline

```
Intent → Validation → Query Building → Pipeline Validation → Execution → Summarization
```

| Component | File | Responsibility |
|-----------|------|----------------|
| IntentExtractor | `intent_extractor.py` | LLM → structured QueryIntent |
| QueryValidator | `validator.py` | Intent constraints, blocked operators |
| QueryBuilder | `query_builder.py` | Intent → MongoDB aggregation pipeline |
| QueryExecutor | `executor.py` | Execute with timeout, result limits |
| ResponseSummarizer | `summarizer.py` | Results → natural language |

### 4.4 AI Fallback Engine

For unsupported actions or when deterministic fails:

```python
# src/api/services/ai_pipeline_agent/langgraph_agent.py

┌─────────────────────┐
│  generate_pipeline  │◀──────────────────────────┐
│  (GPT-5)            │                           │
└──────────┬──────────┘                           │
           │                                      │
           ▼                                      │
    ┌──────┴──────┐                              │
    │   Valid?    │───No──▶ retry (max 3) ───────┘
    └──────┬──────┘
           │ Yes
           ▼
┌─────────────────────┐
│   run_pipeline      │
│   (MongoDB)         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   summarize         │
│   (GPT-5-mini)      │
└─────────────────────┘
```

---

## 5. Query Building System

### 5.1 Field Mapping Layer

Semantic abstraction between user concepts and database paths:

```python
# src/api/services/deterministic_engine/field_mappings.py

METRIC_MAPPINGS = {
    "spending": "item.total_price",
    "quantity": "item.quantity",
    "unit_price": "item.unit_price",
    "order_count": "__COUNT__",  # Special marker
}

DIMENSION_MAPPINGS = {
    "department": "department.normalized_name",
    "supplier": "supplier.name",
    "fiscal_year": "dates.fiscal_year",
    "fiscal_year_start": "dates.fiscal_year_start",
    "acquisition_type": "acquisition.type",
    "classification": "classification.unspsc.segment.title",
    # ... 20+ more mappings
}
```

### 5.2 Query Builder Methods

```python
# src/api/services/deterministic_engine/query_builder.py

BUILDER_METHODS = {
    QueryAction.LIST: _build_list,           # $match → $project → $limit
    QueryAction.COUNT: _build_count,         # $match → $count
    QueryAction.TOP_N: _build_top_n,         # $match → $group → $sort → $limit
    QueryAction.BOTTOM_N: _build_bottom_n,   # $match → $group → $sort(asc) → $limit
    QueryAction.AGGREGATE: _build_aggregate, # $match → $group
    QueryAction.SINGLE_VALUE: _build_single, # $match → $group(_id: null)
    QueryAction.COMPARE: _build_compare,     # Multi-group with $facet
    QueryAction.TREND: _build_trend,         # $group by time dimension
}
```

Example - Top N Pipeline:

```python
def _build_top_n(self, intent: QueryIntent) -> List[Dict[str, Any]]:
    pipeline = []

    # 1. Filter stage
    if intent.filters:
        pipeline.append({"$match": self._build_match(intent.filters)})

    # 2. Group and aggregate
    pipeline.extend(self._build_group_stages(intent))

    # 3. Sort descending
    pipeline.append({"$sort": {"value": -1}})

    # 4. Limit results
    pipeline.append({"$limit": intent.limit or 10})

    return pipeline
```

---

## 6. Data Model

### 6.1 Document Structure

```javascript
{
  // Identifiers
  "purchase_order_number": "4500123456",
  "requisition_number": "REQ-2014-001",
  "lpa_number": "LPA-001",

  // Temporal
  "dates": {
    "creation": ISODate("2014-03-15"),
    "purchase": ISODate("2014-03-20"),
    "fiscal_year": "2013-2014",      // Display
    "fiscal_year_start": 2013         // Query
  },

  // Entities
  "department": {
    "name": "Department of Motor Vehicles",
    "normalized_name": "DEPT OF MOTOR VEHICLES"
  },
  "supplier": {
    "code": "VENDOR001",
    "name": "Dell Technologies",
    "qualifications": ["Small Business", "DVBE"],
    "zip_code": "95814",
    "location": { "type": "Point", "coordinates": [-121.49, 38.58] }
  },

  // Transaction
  "item": {
    "name": "Laptop Computer",
    "description": "Dell Latitude E7450",
    "quantity": 50,
    "unit_price": 1200.00,
    "total_price": 60000.00
  },

  // Classification (UNSPSC)
  "classification": {
    "unspsc": {
      "segment": { "code": "43", "title": "Information Technology" },
      "family": { "code": "4321", "title": "Computer Equipment" },
      "class": { "code": "432110", "title": "Computers" },
      "commodity": { "code": "43211501", "title": "Notebook computers" }
    }
  },

  // Acquisition
  "acquisition": {
    "type": "IT Goods",
    "sub_type": "Hardware",
    "method": "Competitive",
    "sub_method": "RFP"
  },

  "cal_card": false,
  "metadata": { "import_date": ISODate("2024-01-15") }
}
```

### 6.2 Indexing Strategy

```javascript
// scripts/init-indexes.js - 18+ strategic indexes

// Single-field indexes for filtering
db.purchase_orders.createIndex({"dates.fiscal_year_start": 1})
db.purchase_orders.createIndex({"department.normalized_name": 1})
db.purchase_orders.createIndex({"supplier.name": 1})
db.purchase_orders.createIndex({"acquisition.type": 1})

// Compound indexes for common queries
db.purchase_orders.createIndex({
  "dates.fiscal_year_start": 1,
  "department.normalized_name": 1
})
db.purchase_orders.createIndex({
  "acquisition.type": 1,
  "item.total_price": -1
})

// Text index for search
db.purchase_orders.createIndex({
  "item.name": "text",
  "item.description": "text"
})
```

---

## 7. Request/Response Contract

### 7.1 Request Schema

```python
class NaturalLanguageQueryRequest(BaseModel):
    question: str
    reasoning_effort: str = "medium"  # low | medium | high
    verbosity: str = "medium"         # low | medium | high
    model: str = "gpt-5"
    max_results: int = 100
    conversation_history: Optional[List[Dict]] = None
    is_clarification_response: bool = False
```

### 7.2 Response Schema

```python
# Success response
{
    "success": True,
    "answer": "The total spending in 2014 was $4.52 billion...",
    "pipeline": [...],           # MongoDB aggregation pipeline
    "results": [...],            # Raw query results
    "result_count": 1,
    "response_id": "resp_abc123",
    "reasoning_summary": None,
    "error": None,
    "execution_time_seconds": 0.34,
    "timestamp": "2024-12-15T10:30:00Z"
}

# Clarification response
{
    "success": False,
    "answer": "Your question mentions 'purchase orders'...",
    "needs_clarification": True,
    "clarification_prompt": "...",
    "suggestions": ["Option 1", "Option 2"],
    "error": "Ambiguous query"
}
```

---

## 8. Production Considerations

### 8.1 Performance

| Optimization | Implementation | Impact |
|--------------|----------------|--------|
| Connection pooling | 50 connections, `src/api/dependencies.py` | Reduced latency |
| Query timeout | 30s max, `executor.py` | Prevents runaway queries |
| Result limits | Configurable max (default 100) | Memory protection |
| Singleton agent | Single instance per worker | Avoids re-initialization |
| Strategic indexes | 18+ indexes on common patterns | Query optimization |

### 8.2 Cost Optimization

```
Query Type          Model Used          Cost Level
─────────────────────────────────────────────────
Intent extraction   GPT-5-mini          $ (cheap)
Deterministic path  No LLM              Free
AI fallback         GPT-5               $$$ (expensive)
Summarization       GPT-5-mini          $ (cheap)
```

**Result**: ~80% of queries use deterministic path, reducing LLM costs by ~70%.

### 8.3 Security

- **Input validation**: Pydantic models for all requests
- **Query sanitization**: No raw user input in pipelines
- **Blocked operators**: `$where`, `$function`, `$accumulator` blocked
- **Result limits**: Hard cap prevents data exfiltration
- **Timeout enforcement**: Prevents resource exhaustion

### 8.4 Observability

```python
# Structured logging throughout
logger.info("Extracted intent: %s", intent.action)
logger.info("Built pipeline with %d stages", len(pipeline))
logger.info("Query returned %d results in %.2fs", len(results), execution_time)
logger.warning("Intent extraction failed, falling back: %s", exc)
```

---

## 9. Key Files Reference

### Entry Points
| File | Purpose |
|------|---------|
| `src/api/main.py` | FastAPI app initialization |
| `src/api/routes/ai_query.py` | Main query endpoint |
| `src/web/routes/chat.py` | Web UI endpoints |

### Hybrid Engine
| File | Purpose |
|------|---------|
| `src/api/services/deterministic_engine/agent.py` | HybridQueryEngine, LangGraph orchestration |
| `src/api/services/deterministic_engine/intent_extractor.py` | LLM intent extraction |
| `src/api/services/deterministic_engine/ambiguity_detector.py` | Deterministic ambiguity rules |
| `src/api/services/deterministic_engine/intent_sanitizer.py` | Hybrid ambiguity coordination |
| `src/api/services/deterministic_engine/query_builder.py` | Intent → MongoDB pipeline |
| `src/api/services/deterministic_engine/validator.py` | Safety validation |
| `src/api/services/deterministic_engine/executor.py` | Query execution |
| `src/api/services/deterministic_engine/summarizer.py` | Result summarization |

### AI Fallback
| File | Purpose |
|------|---------|
| `src/api/services/ai_pipeline_agent/langgraph_agent.py` | Retry-enabled AI agent |
| `src/api/services/ai_pipeline_agent/pipeline_generator.py` | LLM query generation |
| `src/api/services/ai_pipeline_agent/validators.py` | Pipeline validation |

### Data Layer
| File | Purpose |
|------|---------|
| `src/importer/schema.py` | Document structure |
| `scripts/init-indexes.js` | Index definitions |

---

## 10. Design Decisions Summary

| Decision | Rationale |
|----------|-----------|
| **Hybrid architecture** | Balance cost/speed (deterministic) with flexibility (AI) |
| **Dual-layer ambiguity detection** | LLM for flexibility + rules for reliability |
| **LangGraph orchestration** | Clean state machine, built-in retry logic |
| **Intent extraction vs direct generation** | Safer than LLM generating queries directly |
| **Field mapping layer** | Decouple user semantics from database schema |
| **Clarification before guessing** | Better UX than wrong results |

---

*Document Version: 2.0 | Includes Ambiguity Detection System | Last Updated: January 2025*
