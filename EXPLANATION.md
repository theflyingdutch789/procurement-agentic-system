# Procurement Agentic System - Interview Code Walkthrough

## Table of Contents
1. [Opening Statement (30 seconds)](#1-opening-statement)
2. [Project Overview (2 minutes)](#2-project-overview)
3. [Architecture Deep Dive (5 minutes)](#3-architecture-deep-dive)
4. [AI/LLM Integration (5 minutes)](#4-aillm-integration)
5. [What is LangGraph? (IMPORTANT)](#5-what-is-langgraph-deep-dive)
6. [LangGraph Agent Orchestration (5 minutes)](#6-langgraph-agent-orchestration)
7. [Database Design (3 minutes)](#7-database-design)
8. [API Design (3 minutes)](#8-api-design)
9. [Error Handling & Reliability (3 minutes)](#9-error-handling--reliability)
10. [Production Considerations (2 minutes)](#10-production-considerations)
11. [Key Technical Decisions (2 minutes)](#11-key-technical-decisions)
12. [Common Interview Questions](#12-common-interview-questions)

---

## 1. Opening Statement

> "This is a **production-ready AI-powered procurement assistant** that converts natural language questions into MongoDB queries. It analyzes California government procurement data (346K+ records from 2012-2015) and returns answers in natural language. The system uses GPT-5 with LangGraph for agentic orchestration, FastAPI for the backend, and MongoDB as the database."

**Key Differentiators to Mention:**
- Not just a simple chatbot - it's an **agentic system** with retry logic and self-correction
- Handles **multi-turn conversations** with context awareness
- Production-grade with proper error handling, validation, and monitoring

---

## 2. Project Overview

### What Problem Does It Solve?

```
Business Problem:
Procurement analysts need to query millions of purchase orders, but:
- They don't know SQL/MongoDB query syntax
- Writing aggregation pipelines is complex
- Manual analysis is time-consuming

Solution:
Natural Language → AI Agent → MongoDB Query → Natural Language Answer
"What was total IT spending in 2014?" → $1.2 billion across 47,000 orders
```

### Tech Stack Justification

| Component | Technology | Why This Choice |
|-----------|------------|-----------------|
| **AI/LLM** | OpenAI GPT-5 Reasoning API | Best-in-class reasoning for complex query generation |
| **Agent Framework** | LangGraph | Stateful workflows with conditional edges, retry logic |
| **Backend** | FastAPI | Async support, automatic OpenAPI docs, type safety |
| **Database** | MongoDB | Flexible schema for procurement data, powerful aggregation |
| **Frontend** | Flask + Vanilla JS | Simple, lightweight chat interface |
| **Deployment** | Docker Compose | 4 containers, orchestrated with health checks |

### Project Structure (Show This)

```
/procurement-agentic-system-main
├── src/
│   ├── api/                        # FastAPI Backend
│   │   ├── main.py                 # Application entry point
│   │   ├── routes/                 # API endpoints
│   │   │   ├── query_routes.py     # AI query endpoints
│   │   │   └── ...
│   │   └── services/
│   │       └── mongodb_agent/      # THE CORE AGENT SYSTEM
│   │           ├── langgraph_agent.py  # LangGraph orchestration
│   │           ├── agent.py            # Base GPT-5 agent
│   │           ├── pipeline_generator.py
│   │           ├── validators.py
│   │           ├── executor.py
│   │           └── summarizer.py
│   │
│   ├── web/                        # Flask Frontend
│   │   ├── app.py                  # Flask app
│   │   └── templates/              # Chat UI
│   │
│   └── data_import/                # ETL Pipeline
│       └── csv_importer.py         # CSV → MongoDB
│
├── docker-compose.yml              # Container orchestration
├── evaluation/                     # Test cases & benchmarks
└── requirements.txt
```

---

## 3. Architecture Deep Dive

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                              │
│                    (Flask Chat UI - Port 5000)                       │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ POST /api/chat/message
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                              │
│                        (API - Port 8000)                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    POST /api/ai/query                        │    │
│  │  • Validates request (Pydantic)                              │    │
│  │  • Manages conversation state                                 │    │
│  │  • Invokes LangGraph Agent                                   │    │
│  └───────────────────────────────┬─────────────────────────────┘    │
└──────────────────────────────────┼──────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LANGGRAPH AGENT LAYER                            │
│                  (Stateful Workflow Orchestration)                   │
│                                                                       │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│   │   GENERATE   │───▶│     RUN      │───▶│  SUMMARIZE   │          │
│   │   PIPELINE   │    │   PIPELINE   │    │              │          │
│   └──────┬───────┘    └──────┬───────┘    └──────────────┘          │
│          │                   │                                       │
│          │ retry (max 3)     │ retry                                 │
│          └───────────────────┘                                       │
└──────────────────────────────────────────────────────────────────────┘
                    │                       │
                    ▼                       ▼
        ┌───────────────────┐    ┌───────────────────┐
        │   OPENAI GPT-5    │    │     MONGODB       │
        │  Reasoning API    │    │   (Port 27017)    │
        │                   │    │  346K+ documents  │
        │ • Pipeline Gen    │    │  18+ indexes      │
        │ • Summarization   │    │                   │
        └───────────────────┘    └───────────────────┘
```

### Component Responsibilities

**1. FastAPI Layer** (`src/api/main.py`, `routes/query_routes.py`)
- Request validation with Pydantic models
- Dependency injection for MongoDB and Agent instances
- Conversation state management
- CORS, logging, error handling

**2. LangGraph Agent** (`src/api/services/mongodb_agent/langgraph_agent.py`)
- State machine with 3 nodes: generate → run → summarize
- Conditional edges for retry logic
- Maintains attempt counter (max 3 retries)
- Tracks full conversation context

**3. Base Agent** (`src/api/services/mongodb_agent/agent.py`)
- Coordinates specialized services
- Manages OpenAI API calls
- Handles model/reasoning configuration

**4. Specialized Services:**
- **PipelineGenerator**: NL → MongoDB aggregation JSON
- **QueryValidator**: Pre-execution validation + dry-run
- **QueryExecutor**: Actual MongoDB execution
- **AnswerSummarizer**: Results → Natural language

---

## 4. AI/LLM Integration

### GPT-5 Reasoning API Usage

**File: `src/api/services/mongodb_agent/pipeline_generator.py`**

```python
# Key integration pattern
response = self.client.responses.create(
    model=self.model_name,          # "gpt-5", "gpt-5-mini", "gpt-5-nano"
    input=[
        {"role": "system", "content": static_prompt_prefix},
        {"role": "user", "content": dynamic_suffix}
    ],
    reasoning={
        "effort": self.reasoning_effort  # "minimal", "low", "medium", "high"
    },
    previous_response_id=prev_response_id  # For multi-turn context
)
```

**Why OpenAI Responses API (not Chat Completions)?**
- Supports **reasoning effort levels** for complex tasks
- Built-in **response chaining** via `previous_response_id`
- Better for agentic workflows with structured output

### Prompt Engineering Strategy

**File: `src/api/services/mongodb_agent/prompts.py`**

The prompt has two parts:

**1. Static Prefix (Cached at Startup)**
- MongoDB schema documentation
- Field types and value examples
- 17 specific rules for query generation
- Example queries and patterns

**2. Dynamic Suffix (Per Request)**
- User's question
- Conversation history (for context)
- Previous errors (for retry context)

**Critical Rules Example:**
```
Rule 3: Always use $ifNull for price summation
CORRECT: {"$sum": {"$ifNull": ["$item.total_price", 0]}}
WRONG:   {"$sum": "$item.total_price"}

Rule 7: fiscal_year is STRING "2013-2014", not integer
CORRECT: {"$match": {"dates.fiscal_year": "2013-2014"}}
WRONG:   {"$match": {"dates.fiscal_year": 2014}}
```

### Reasoning Effort Levels

| Level | Use Case | Trade-off |
|-------|----------|-----------|
| **minimal** | "Count all orders" | Fastest, cheapest |
| **low** | "Total spending in 2014" | Good balance |
| **medium** | "Top 5 departments by IT spending" | Complex aggregations |
| **high** | "Compare Q1 vs Q2 spending trends" | Best accuracy |

---

## 5. What is LangGraph? (Deep Dive)

> **This section prepares you for: "What is LangGraph and why did you choose it?"**

### The 30-Second Answer

> "LangGraph is a library from LangChain for building **stateful, multi-step AI agent workflows** as graphs. Unlike simple chains that are linear (A → B → C), LangGraph lets me define **nodes** (actions) and **edges** (transitions) with **conditional routing**. This was essential for my retry logic—when a generated query fails, I can loop back to regenerate with error context, which isn't possible with basic chains."

---

### What is LangGraph? (Detailed Explanation)

**LangGraph** is a library built on top of LangChain that enables you to create **stateful, cyclical workflows** for LLM applications. Think of it as a way to build AI agents as **state machines** or **directed graphs**.

#### Core Concepts

```
┌─────────────────────────────────────────────────────────────────┐
│                        LANGGRAPH CONCEPTS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   STATE          A TypedDict that persists across all nodes      │
│   ─────          (question, pipeline, results, attempt, etc.)    │
│                                                                   │
│   NODE           A function that takes state → returns state     │
│   ────           (generate_pipeline, run_pipeline, summarize)    │
│                                                                   │
│   EDGE           Connection between nodes                         │
│   ────           (can be conditional based on state)              │
│                                                                   │
│   GRAPH          The compiled workflow that executes nodes        │
│   ─────          (invoked with initial state, returns final)     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### Simple Code Example

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

# 1. Define State - shared across all nodes
class AgentState(TypedDict):
    question: str
    pipeline: list
    results: list
    answer: str
    attempt: int

# 2. Define Nodes - functions that transform state
def generate_pipeline(state: AgentState) -> AgentState:
    # Call GPT-5 to generate MongoDB pipeline
    state["pipeline"] = call_gpt5(state["question"])
    return state

def run_pipeline(state: AgentState) -> AgentState:
    # Execute pipeline against MongoDB
    state["results"] = execute_mongodb(state["pipeline"])
    return state

def summarize(state: AgentState) -> AgentState:
    # Convert results to natural language
    state["answer"] = call_gpt5_summarize(state["results"])
    return state

# 3. Define Router - determines next node based on state
def route_after_generate(state: AgentState) -> str:
    if state["pipeline"]:
        return "run"           # Success → run pipeline
    elif state["attempt"] < 3:
        return "retry"         # Failure → try again
    else:
        return "stop"          # Give up

# 4. Build Graph
graph = StateGraph(AgentState)

# Add nodes
graph.add_node("generate", generate_pipeline)
graph.add_node("run", run_pipeline)
graph.add_node("summarize", summarize)

# Set entry point
graph.set_entry_point("generate")

# Add conditional edges (THE KEY FEATURE)
graph.add_conditional_edges(
    "generate",              # From this node
    route_after_generate,    # Use this function to decide
    {
        "run": "run",        # If returns "run" → go to "run" node
        "retry": "generate", # If returns "retry" → loop back
        "stop": END          # If returns "stop" → end workflow
    }
)

# Compile and run
app = graph.compile()
result = app.invoke({"question": "Total spending in 2014?", "attempt": 0})
```

---

### Why LangGraph vs Alternatives?

#### Comparison Table

| Approach | Pros | Cons | When to Use |
|----------|------|------|-------------|
| **Simple Function Calls** | Easy, no dependencies | No state persistence, manual error handling | Simple one-shot tasks |
| **LangChain Chains** | Good for linear flows | Can't loop back, limited branching | Sequential pipelines |
| **LangGraph** | Full state machine, conditional routing, cycles | Steeper learning curve | Complex agents with retry logic |
| **Custom State Machine** | Full control | Reinventing the wheel | Very custom requirements |

#### Why I Chose LangGraph for This Project

```
My Requirements:                          How LangGraph Solves It:
─────────────────                         ────────────────────────
1. Retry failed queries                   → Conditional edges loop back
2. Track attempt count                    → State persists across nodes
3. Pass error context to LLM              → State includes error messages
4. Different paths for success/failure    → Router functions decide path
5. Clean separation of concerns           → Each node is independent
6. Easy to add new steps later            → Just add new nodes + edges
```

---

### Visual: LangGraph vs LangChain

**LangChain (Linear Chain):**
```
Question → Generate → Execute → Summarize → Answer
             ↓
         (if fails, whole chain fails)
```

**LangGraph (Graph with Cycles):**
```
                    ┌─────────────────┐
                    │    Question     │
                    └────────┬────────┘
                             ▼
              ┌─────────────────────────────┐
              │         GENERATE            │◀──────┐
              │   (call GPT-5 for query)    │       │
              └─────────────┬───────────────┘       │
                            │                       │
                  ┌─────────┴─────────┐             │
                  ▼                   ▼             │
             [success]            [failure]         │
                  │                   │             │
                  ▼                   ▼             │
              ┌───────┐        ┌────────────┐       │
              │  RUN  │        │ attempt<3? │       │
              └───┬───┘        └─────┬──────┘       │
                  │                  │              │
           ┌──────┴──────┐     ┌─────┴─────┐        │
           ▼             ▼     ▼           ▼        │
      [success]     [failure] [yes]       [no]      │
           │             │     │           │        │
           ▼             │     │           ▼        │
      ┌─────────┐        │     │      ┌────────┐    │
      │SUMMARIZE│        │     │      │  END   │    │
      └────┬────┘        │     │      │(error) │    │
           │             │     │      └────────┘    │
           ▼             │     │                    │
      ┌────────┐         └─────┴────────────────────┘
      │ Answer │               (retry with error context)
      └────────┘
```

---

### Key LangGraph Features I Used

#### 1. TypedDict State

```python
class AgentState(TypedDict):
    question: str              # Never changes
    conversation_history: list # Context from previous turns
    pipeline: list             # Updated by generate node
    results: list              # Updated by run node
    answer: str                # Updated by summarize node
    attempt: int               # Incremented on retry
    last_error: str            # Passed to LLM for context
```

**Why TypedDict?** Type hints + IDE autocomplete + runtime validation

#### 2. Conditional Edges

```python
graph.add_conditional_edges(
    "generate_pipeline",      # Source node
    self._route_after_generate,  # Router function
    {
        "run": "run_pipeline",      # Map return value → target node
        "retry": "generate_pipeline",
        "stop": END
    }
)
```

**The router function:**
```python
def _route_after_generate(self, state: AgentState) -> str:
    if state.get("pipeline"):
        return "run"      # Pipeline exists → execute it
    elif state["attempt"] < 3:
        state["attempt"] += 1
        return "retry"    # No pipeline, but retries left
    else:
        return "stop"     # No pipeline, no retries → give up
```

#### 3. Cycles (Loops)

```python
# This creates a loop: generate → (fail) → generate → (fail) → generate
graph.add_conditional_edges(
    "generate_pipeline",
    router,
    {"retry": "generate_pipeline", ...}  # Points back to itself!
)
```

**Without LangGraph:** Would need manual while loop + state tracking

#### 4. State Persistence Across Nodes

```python
# In generate node
state["last_error"] = "Field 'spending' doesn't exist"
return state

# In next iteration of generate (after retry)
if state.get("last_error"):
    prompt += f"\n\nPrevious error: {state['last_error']}"
```

---

### How It Works in My Code

**File: `src/api/services/mongodb_agent/langgraph_agent.py`**

```python
class LangGraphMongoDBAgent:
    def __init__(self, base_agent: GPT5MongoDBAgent):
        self.base_agent = base_agent
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledGraph:
        graph = StateGraph(AgentState)

        # Three main nodes
        graph.add_node("generate_pipeline", self._generate_pipeline)
        graph.add_node("run_pipeline", self._run_pipeline)
        graph.add_node("summarize", self._summarize)

        # Entry point
        graph.set_entry_point("generate_pipeline")

        # Conditional routing after generation
        graph.add_conditional_edges(
            "generate_pipeline",
            self._after_generate,
            {"run": "run_pipeline", "retry": "generate_pipeline", "stop": END}
        )

        # Conditional routing after execution
        graph.add_conditional_edges(
            "run_pipeline",
            self._after_run,
            {"summarize": "summarize", "retry": "generate_pipeline"}
        )

        # Summarize always ends
        graph.add_edge("summarize", END)

        return graph.compile()

    def query(self, question: str, **kwargs) -> dict:
        # Initial state
        initial_state = {
            "question": question,
            "attempt": 0,
            "pipeline": None,
            "results": None,
            "answer": None,
            **kwargs
        }

        # Invoke the graph - LangGraph handles all routing
        final_state = self.graph.invoke(initial_state)

        return {
            "success": final_state.get("answer") is not None,
            "answer": final_state.get("answer"),
            "pipeline": final_state.get("pipeline"),
            "results": final_state.get("results")
        }
```

---

### Interview Talking Points

**If asked "What is LangGraph?":**

> "LangGraph is a library from the LangChain team for building AI agent workflows as state machines. Instead of linear chains, you define nodes (actions) and edges (transitions) that can be conditional. The key feature is **cycles**—you can loop back to retry failed steps, which is essential for reliable AI agents."

**If asked "Why not just use a while loop?":**

> "I could, but LangGraph gives me:
> 1. **Clean separation** - each node is a single-responsibility function
> 2. **Declarative routing** - the graph structure is explicit, not buried in if-else
> 3. **Built-in state management** - no global variables or context passing
> 4. **Debuggability** - I can visualize the graph and trace state transitions
> 5. **Extensibility** - adding a new step is just adding a node and edge"

**If asked "Show me the retry logic":**

> "Here's the flow: Generate → (check if pipeline exists) → if yes, Run → if no, check attempts < 3 → if yes, loop back to Generate with error in state → if no, stop. The key is that the error message from the failed attempt is in the state, so GPT-5 sees what went wrong and adjusts."

**If asked "What's the learning curve?":**

> "Moderate. If you understand state machines or workflow engines, it's intuitive. The documentation is good, and there are many examples. The hardest part was understanding that nodes must return the full state dict, not just the changed values."

---

### Common Mistakes to Avoid (Show You Understand Deeply)

```python
# WRONG - Node returns only changed value
def generate_pipeline(state):
    return {"pipeline": [...]}  # ❌ Other state fields are lost!

# RIGHT - Node returns full state
def generate_pipeline(state):
    state["pipeline"] = [...]
    return state  # ✅ All fields preserved

# WRONG - Modifying state without returning
def run_pipeline(state):
    state["results"] = execute(state["pipeline"])
    # ❌ Forgot to return state!

# RIGHT
def run_pipeline(state):
    state["results"] = execute(state["pipeline"])
    return state  # ✅
```

---

## 6. LangGraph Agent Orchestration

### State Machine Design

**File: `src/api/services/mongodb_agent/langgraph_agent.py`**

```python
class AgentState(TypedDict):
    question: str                    # Original user question
    conversation_history: list       # Previous turns
    pipeline: list                   # Generated MongoDB pipeline
    results: list                    # Query results
    answer: str                      # Natural language answer
    attempt: int                     # Current retry count (max 3)
    reasoning_summary: str           # GPT-5's internal reasoning
```

### Graph Definition

```python
def _build_graph(self) -> StateGraph:
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("generate_pipeline", self._generate_pipeline)
    graph.add_node("run_pipeline", self._run_pipeline)
    graph.add_node("summarize", self._summarize)

    # Entry point
    graph.set_entry_point("generate_pipeline")

    # Conditional routing
    graph.add_conditional_edges(
        "generate_pipeline",
        self._after_generate,    # Router function
        {
            "run": "run_pipeline",      # Success → execute
            "retry": "generate_pipeline", # Failure → retry
            "stop": END                   # Max attempts → stop
        }
    )

    graph.add_conditional_edges(
        "run_pipeline",
        self._after_run,
        {
            "summarize": "summarize",     # Success → answer
            "retry": "generate_pipeline"  # Failure → regenerate
        }
    )

    graph.add_edge("summarize", END)

    return graph.compile()
```

### Visual State Flow

```
                    ┌──────────────────┐
                    │  START           │
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
            ┌──────▶│ generate_pipeline│◀─────┐
            │       └────────┬─────────┘      │
            │                │                │
            │    success?    │    failure     │
            │    ┌───────────┴───────────┐    │
            │    ▼                       ▼    │
            │  "run"                  "retry" │
            │    │                       │    │
            │    │    attempt < 3?       │    │
            │    │    ┌─────────────────┬┘    │
            │    │    │ yes             │ no  │
            │    │    │                 ▼     │
            │    │    └───────────▶  "stop"   │
            │    │                     │      │
            │    │                     ▼      │
            │    │               ┌─────────┐  │
            │    │               │   END   │  │
            │    │               └─────────┘  │
            │    ▼                            │
            │  ┌──────────────────┐           │
            │  │   run_pipeline   │───────────┘
            │  └────────┬─────────┘  (on error)
            │           │
            │  success? │
            │  ┌────────┴────────┐
            │  ▼                 ▼
            │"summarize"      "retry"
            │  │                 │
            │  ▼                 │
            │┌──────────────────┐│
            ││    summarize     ││
            │└────────┬─────────┘│
            │         │          │
            │         ▼          │
            │   ┌─────────┐      │
            │   │   END   │      │
            │   └─────────┘      │
            │                    │
            └────────────────────┘
```

### Why LangGraph Over Simple Function Calls?

1. **State Persistence**: Tracks attempt count, results, errors across nodes
2. **Conditional Routing**: Dynamic path selection based on outcomes
3. **Built-in Retry Logic**: No manual loop management
4. **Observability**: Can visualize and debug state transitions
5. **Extensibility**: Easy to add new nodes (e.g., caching, logging)

---

## 7. Database Design

### Document Schema

**Collection: `purchase_orders`**

```javascript
{
  // Identifiers
  purchase_order_number: "PO-2014-001",
  requisition_number: "REQ-123",

  // Temporal Data (Critical for queries)
  dates: {
    creation: ISODate("2014-01-15"),
    purchase: ISODate("2014-01-20"),
    fiscal_year: "2013-2014",        // STRING - for grouping
    fiscal_year_start: 2013          // INTEGER - for numeric filters
  },

  // Department
  department: {
    name: "Department of Corrections and Rehabilitation",
    normalized_name: "Corrections & Rehabilitation"
  },

  // Acquisition Classification
  acquisition: {
    type: "IT Goods",      // IT Goods | IT Services | NON-IT Goods | NON-IT Services
    method: "Competitive Bid"
  },

  // Item Details
  item: {
    name: "Windows Server License",
    description: "Microsoft Windows Server 2019...",
    quantity: 10,
    unit_price: 5000.00,
    total_price: 50000.00     // THIS IS THE PRIMARY SPENDING FIELD
  },

  // Supplier Info
  supplier: {
    name: "Microsoft Corp",
    qualifications: ["DVBE", "Small Business"],
    location: {               // GeoJSON for spatial queries
      type: "Point",
      coordinates: [-122.3, 37.8]
    }
  },

  // UNSPSC Classification (Hierarchical)
  classification: {
    unspsc: {
      segment: { code: "43000000", title: "IT" },
      family: { code: "43210000", title: "Software" },
      class: { code: "43211000", title: "Operating Systems" }
    }
  }
}
```

### Index Strategy

**18 indexes for query optimization:**

```javascript
// Compound indexes for common query patterns
{ "dates.fiscal_year": 1, "department.name": 1 }
{ "dates.fiscal_year": 1, "acquisition.type": 1 }
{ "supplier.name": 1, "item.total_price": -1 }

// Text index for full-text search
{ "item.name": "text", "item.description": "text",
  "supplier.name": "text", "department.name": "text" }

// Geospatial index
{ "supplier.location": "2dsphere" }

// Single-field indexes for filtering
{ "dates.fiscal_year": 1 }
{ "department.name": 1 }
{ "acquisition.type": 1 }
```

### Sample Generated Pipeline

**Question:** "What was total IT spending by department in 2014?"

```javascript
[
  { "$match": {
      "dates.fiscal_year": "2013-2014",
      "acquisition.type": { "$in": ["IT Goods", "IT Services"] }
    }
  },
  { "$group": {
      "_id": "$department.name",
      "total_spending": { "$sum": { "$ifNull": ["$item.total_price", 0] } }
    }
  },
  { "$sort": { "total_spending": -1 } },
  { "$limit": 10 }
]
```

---

## 8. API Design

### Primary Endpoint

**POST `/api/ai/query`**

```python
# Request Model (Pydantic)
class NaturalLanguageQueryRequest(BaseModel):
    question: str                              # Required
    conversation_id: Optional[str] = None      # For multi-turn
    conversation_history: Optional[List] = []  # Previous context
    reasoning_effort: str = "medium"           # minimal|low|medium|high
    verbosity: str = "medium"                  # low|medium|high
    max_results: int = 10                      # 1-1000
    model: str = "gpt-5"                       # gpt-5|gpt-5-mini|gpt-5-nano

# Response Model
class AIQueryResponse(BaseModel):
    success: bool
    answer: str                    # "Total spending was $2.8 billion"
    pipeline: List[Dict]           # The generated MongoDB pipeline
    results: List[Dict]            # Raw query results
    result_count: int
    reasoning_summary: Optional[str]  # GPT-5's reasoning (if available)
    execution_time_seconds: float
    timestamp: str
```

### Dependency Injection Pattern

**File: `src/api/routes/query_routes.py`**

```python
# Singleton pattern for resource efficiency
_agent_instance = None

def get_agent(
    mongo_client: MongoClient = Depends(get_mongo_client),
    database: Database = Depends(get_database)
) -> LangGraphMongoDBAgent:
    global _agent_instance
    if _agent_instance is None:
        base_agent = GPT5MongoDBAgent(
            mongo_client=mongo_client,
            database_name=database.name,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model_name="gpt-5",
            reasoning_effort="medium"
        )
        _agent_instance = LangGraphMongoDBAgent(base_agent)
    return _agent_instance

@router.post("/ai/query")
async def ai_query(
    request: NaturalLanguageQueryRequest,
    agent: LangGraphMongoDBAgent = Depends(get_agent)
):
    result = agent.query(
        question=request.question,
        reasoning_effort=request.reasoning_effort,
        conversation_history=request.conversation_history
    )
    return AIQueryResponse(**result)
```

### Multi-Turn Conversation Handling

```python
# In-memory conversation state (would use Redis in production)
_conversation_states: Dict[str, str] = {}  # conversation_id → previous_response_id

@router.post("/ai/query")
async def ai_query(request: NaturalLanguageQueryRequest, ...):
    # Get previous response ID for context
    prev_response_id = None
    if request.conversation_id:
        prev_response_id = _conversation_states.get(request.conversation_id)

    # Query with context
    result = agent.query(
        question=request.question,
        previous_response_id=prev_response_id,  # Chain to previous
        conversation_history=request.conversation_history
    )

    # Store new response ID for next turn
    if request.conversation_id and result.get("response_id"):
        _conversation_states[request.conversation_id] = result["response_id"]

    return result
```

---

## 9. Error Handling & Reliability

### Multi-Layer Validation

**Layer 1: Request Validation (Pydantic)**
```python
class NaturalLanguageQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    max_results: int = Field(default=10, ge=1, le=1000)
    reasoning_effort: str = Field(default="medium")

    @validator('reasoning_effort')
    def validate_effort(cls, v):
        if v not in ["minimal", "low", "medium", "high"]:
            raise ValueError("Invalid reasoning effort")
        return v
```

**Layer 2: Pipeline Validation (Before Execution)**

**File: `src/api/services/mongodb_agent/validators.py`**

```python
class QueryValidator:
    def validate_aggregation_pipeline(self, pipeline: List[Dict]) -> Tuple[bool, str]:
        # 1. Structure check
        if not isinstance(pipeline, list):
            return False, "Pipeline must be a list"

        for stage in pipeline:
            if not isinstance(stage, dict):
                return False, f"Invalid stage: {stage}"

            # Check operator names
            for key in stage.keys():
                if not key.startswith('$'):
                    return False, f"Invalid operator: {key}"

        # 2. Dry-run with 1-second timeout
        try:
            result = self.collection.aggregate(
                pipeline + [{"$limit": 1}],
                maxTimeMS=1000
            )
            list(result)  # Force execution
            return True, None
        except Exception as e:
            return False, str(e)
```

**Layer 3: Execution with Timeout**

**File: `src/api/services/mongodb_agent/executor.py`**

```python
class MongoDBQueryExecutor:
    def execute_aggregation(self, pipeline: List[Dict]) -> Tuple[bool, Any, float]:
        start = time.time()
        try:
            # Add limit if not present
            if not any('$limit' in stage for stage in pipeline):
                pipeline = pipeline + [{"$limit": 100}]

            cursor = self.collection.aggregate(
                pipeline,
                maxTimeMS=30000  # 30-second timeout
            )
            results = list(cursor)

            # Serialize ObjectId, datetime, etc.
            results = self._serialize_results(results)

            return True, results, time.time() - start
        except Exception as e:
            return False, str(e), time.time() - start
```

### LangGraph Retry Logic

```python
def _after_generate(self, state: AgentState) -> str:
    """Route after pipeline generation"""
    if state.get("pipeline"):
        return "run"  # Success → execute
    elif state["attempt"] < 3:
        return "retry"  # Failure → retry
    else:
        return "stop"  # Max attempts → give up

def _after_run(self, state: AgentState) -> str:
    """Route after pipeline execution"""
    if state.get("results") is not None:
        return "summarize"  # Success → answer
    elif state["attempt"] < 3:
        state["attempt"] += 1
        return "retry"  # Failure → regenerate with error context
    else:
        return "stop"
```

### Error Context Feedback

When retry occurs, the error message is fed back to GPT-5:

```python
def _generate_pipeline(self, state: AgentState) -> AgentState:
    # Include previous error in prompt
    error_context = ""
    if state.get("last_error"):
        error_context = f"\n\nPrevious attempt failed: {state['last_error']}\nPlease fix and try again."

    pipeline, response_id, raw, error = self.base_agent.generate_pipeline(
        question=state["question"] + error_context,
        conversation_history=state.get("conversation_history", [])
    )

    state["pipeline"] = pipeline
    state["last_error"] = error
    return state
```

---

## 10. Production Considerations

### Docker Compose Architecture

```yaml
services:
  mongodb:
    image: mongo:7.0
    healthcheck:
      test: mongosh --eval "db.adminCommand('ping')"
      interval: 10s
      retries: 5
    volumes:
      - mongodb_data:/data/db

  importer:
    build: ./src/data_import
    depends_on:
      mongodb:
        condition: service_healthy
    profiles: ["seed"]  # Only runs on explicit profile

  api:
    build: ./src/api
    depends_on:
      mongodb:
        condition: service_healthy
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    healthcheck:
      test: curl -f http://localhost:8000/api/health

  web:
    build: ./src/web
    depends_on:
      api:
        condition: service_healthy
    ports:
      - "5000:5000"
```

### Performance Optimizations

1. **Connection Pooling**
   ```python
   MongoClient(host, maxPoolSize=50, minPoolSize=10)
   ```

2. **Singleton Agent Instance** - Avoids re-initialization per request

3. **Static Prompt Caching** - Schema prefix computed once at startup

4. **Query Limiting** - Auto-append `$limit` stage to prevent full scans

5. **Index Coverage** - 18 indexes covering common query patterns

### Scalability Path

```
Current: Single API container
   ↓
Scale: Multiple Uvicorn workers (API_WORKERS=4)
   ↓
Scale: Load balancer + multiple API containers
   ↓
Scale: MongoDB replica set for read scaling
   ↓
Scale: Redis for conversation state (instead of in-memory)
```

---

## 11. Key Technical Decisions

### Decision 1: LangGraph vs Simple Chain

**Why LangGraph?**
- Need stateful retry logic with context
- Conditional routing based on success/failure
- Easy to visualize and debug state machine
- Extensible for future nodes (caching, logging, etc.)

### Decision 2: GPT-5 Responses API vs Chat Completions

**Why Responses API?**
- Native reasoning effort control
- Built-in response chaining (`previous_response_id`)
- Better structured for agentic workflows

### Decision 3: MongoDB vs PostgreSQL

**Why MongoDB?**
- Flexible schema for varied procurement data
- Powerful aggregation framework (matches natural language patterns)
- Native JSON support (LLM outputs JSON naturally)
- Text and geospatial indexes built-in

### Decision 4: FastAPI vs Flask for API

**Why FastAPI for API, Flask for Web?**
- FastAPI: Async, automatic OpenAPI docs, Pydantic validation
- Flask: Simple, battle-tested for server-rendered UI
- Separation of concerns: API complexity vs UI simplicity

### Decision 5: Validation Before Execution

**Why Pre-validate Pipelines?**
- Fail fast on syntax errors (saves GPT-5 API costs)
- Dry-run catches field name typos
- 1-second timeout prevents expensive mistakes

---

## 12. Common Interview Questions

### Q: "How does the retry logic work?"

**A:** "The LangGraph agent uses conditional edges. After pipeline generation, if it fails, we check `attempt < 3`. If true, we route back to `generate_pipeline` with the error message included in the prompt. GPT-5 sees what went wrong and adjusts. After 3 failures, we stop and return an error to the user."

### Q: "How do you handle multi-turn conversations?"

**A:** "Two mechanisms:
1. We pass `conversation_history` in the prompt so GPT-5 sees previous Q&A
2. We use OpenAI's `previous_response_id` to chain responses, which gives GPT-5 deeper context about what it previously reasoned about."

### Q: "What happens if the generated pipeline is slow?"

**A:** "Three safeguards:
1. Validation dry-runs with 1-second timeout before real execution
2. Execution has 30-second timeout
3. We auto-append `$limit: 100` if not present
4. Strategic indexes cover common query patterns"

### Q: "Why not just use LangChain?"

**A:** "LangGraph (part of LangChain ecosystem) provides the specific feature I needed: stateful workflows with conditional routing. Pure LangChain chains are linear. I needed branching logic for retry handling. LangGraph's graph-based approach maps perfectly to: generate → (success? → execute) → (success? → summarize)"

### Q: "How would you scale this?"

**A:** "Three phases:
1. **Vertical**: Increase Uvicorn workers (currently 4)
2. **Horizontal**: Load balancer + multiple API containers, move conversation state to Redis
3. **Database**: MongoDB replica set, potentially sharding on `dates.fiscal_year` if data grows significantly"

### Q: "What's the most challenging part?"

**A:** "Getting GPT-5 to generate correct MongoDB syntax consistently. Solved by:
1. Comprehensive schema documentation in the prompt
2. 17 specific rules with correct/incorrect examples
3. Error feedback on retry (GPT-5 learns from its mistakes)
4. Validation dry-run to catch issues before execution"

### Q: "How do you test this?"

**A:** "The `evaluation/` directory has 30+ test cases across 4 difficulty levels (Basic, Intermediate, Advanced, Ultra). Each test has:
- Natural language question
- Expected MongoDB pipeline pattern
- Ground truth answer for validation
Tests run with different model/reasoning configurations to find optimal settings."

---

## Quick Reference: Files to Open During Interview

| When Asked About | Open This File |
|------------------|----------------|
| Overall architecture | `docker-compose.yml` |
| Agent orchestration | `src/api/services/mongodb_agent/langgraph_agent.py` |
| GPT-5 integration | `src/api/services/mongodb_agent/pipeline_generator.py` |
| Prompt engineering | `src/api/services/mongodb_agent/prompts.py` |
| Schema design | `src/api/services/mongodb_agent/schema.py` |
| API endpoints | `src/api/routes/query_routes.py` |
| Validation logic | `src/api/services/mongodb_agent/validators.py` |
| Error handling | `src/api/services/mongodb_agent/executor.py` |
| Data model | `src/data_import/csv_importer.py` |
| Test cases | `evaluation/test_cases.json` |

---

## Final Tips for the Interview

1. **Start high-level, drill down on request** - Show the architecture diagram first, then dive into specifics when asked

2. **Show the flow** - Walk through a complete request: User question → API → Agent → GPT-5 → MongoDB → Answer

3. **Highlight the "why"** - For each technical decision, explain the trade-offs considered

4. **Demonstrate error handling** - Show the retry logic and how GPT-5 self-corrects

5. **Know the numbers** - 346K documents, 18 indexes, 3 retry attempts, 30-second timeout

6. **Be ready for "what would you improve?"** -
   - Add caching for common queries
   - Implement rate limiting
   - Add query explanation feature
   - Support for query optimization suggestions

Good luck with your interview!
