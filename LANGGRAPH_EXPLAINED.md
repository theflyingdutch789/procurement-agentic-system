# LangGraph Architecture

This document explains how LangGraph is used in the procurement query system.

## What is LangGraph?

LangGraph is a library for building **stateful, multi-step LLM workflows** as graphs.

- **Nodes** = Functions that process/transform state
- **Edges** = Connections between nodes (can be conditional)
- **State** = Typed data that flows through the graph

## Overview

The system uses **2 LangGraph agents**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER QUERY                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH AGENT #1: HybridQueryEngine                     │
│                    (src/api/services/deterministic_engine/agent.py)          │
│                                                                              │
│   Purpose: Route between fast deterministic path vs slow LLM path            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            ┌──────────────┐               ┌──────────────────────────────────┐
            │ Deterministic │               │  LANGGRAPH AGENT #2:             │
            │    (fast)     │               │  LangGraphMongoDBAgent           │
            │ 1 LLM call:   │               │  (fallback - full LLM)           │
            │ intent only   │               │  iterative gen + retries         │
            └──────────────┘               └──────────────────────────────────┘
```

---

## Agent #1: HybridQueryEngine

**File:** `src/api/services/deterministic_engine/agent.py`

**Purpose:** Smart router that tries fast deterministic path first, falls back to full LLM if needed.

### State Definition

```python
class HybridAgentState(TypedDict, total=False):
    question: str                          # User's query
    conversation_history: Optional[List]   # Previous messages for context
    reasoning_effort: Optional[str]        # GPT-5 reasoning effort (fallback)
    verbosity: Optional[str]               # Answer verbosity (fallback)
    previous_response_id: Optional[str]    # Chain-of-thought continuity
    is_clarification_response: bool        # Skip ambiguity check if true
    intent: Optional[QueryIntent]          # Extracted structured intent
    route: Optional[str]                   # "deterministic" | "fallback" | "stop"
    response: Optional[Dict]               # Final response
    error: Optional[str]                   # Error message if any
```

### Graph Structure

```
                    ┌─────────────────┐
                    │     START       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  decide_route   │ ← Extract intent via LLM
                    │                 │   Check if ambiguous
                    │                 │   Check if action supported
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
    ┌─────────┐      ┌──────────────┐      ┌──────────┐
    │  stop   │      │deterministic │      │ fallback │
    │  (END)  │      │              │      │          │
    └─────────┘      └──────┬───────┘      └────┬─────┘
   (ambiguous -             │                   │
    ask user)               ▼                   │
                    ┌──────────────┐            │
                    │ Can fallback │────────────┘
                    │  if failed   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌─────────────────┐
                    │      END        │
                    └─────────────────┘
```

### Code Implementation

```python
def _build_graph(self):
    graph = StateGraph(HybridAgentState)

    # Define 3 nodes
    graph.add_node("decide_route", self._route_node)
    graph.add_node("deterministic", self._deterministic_node)
    graph.add_node("fallback", self._fallback_node)

    # Set entry point
    graph.set_entry_point("decide_route")

    # Conditional routing after decide_route
    graph.add_conditional_edges(
        "decide_route",
        self._after_route,  # Returns state["route"]
        {
            "deterministic": "deterministic",
            "fallback": "fallback",
            "stop": END,
        },
    )

    # Deterministic can fallback if it fails
    graph.add_conditional_edges(
        "deterministic",
        self._after_deterministic,
        {
            "fallback": "fallback",
            "stop": END,
        },
    )

    # Fallback always ends
    graph.add_edge("fallback", END)

    return graph.compile()
```

### Node Functions

#### 1. decide_route (`_route_node`)

Extracts intent and decides which path to take:

```python
def _route_node(self, state: HybridAgentState) -> HybridAgentState:
    # 1. Extract intent using LLM (gpt-5-mini, JSON mode).
    #    If extraction throws for any reason → fall back to the GPT-5 agent.
    try:
        intent = self.deterministic_engine.intent_extractor.extract(
            state["question"], conversation_context
        )
    except Exception as exc:
        state["error"] = str(exc)
        state["route"] = "fallback"
        return state

    # 2. Ambiguity layer 1 — the LLM itself flagged the question as ambiguous
    if intent.is_ambiguous:
        state["response"] = self._clarification_response(intent)
        state["route"] = "stop"
        return state

    # 3. Ambiguity layer 2 — deterministic safety-net detector
    intent = sanitize_intent(state["question"], intent,
                             is_clarification_response=state.get("is_clarification_response", False))
    if intent.is_ambiguous:
        state["response"] = self._clarification_response(intent)
        state["route"] = "stop"
        return state

    # 4. Route by action: supported → deterministic, else → fallback
    if intent.action not in SUPPORTED_ACTIONS:
        state["route"] = "fallback"
        return state

    state["intent"] = intent
    state["route"] = "deterministic"
    return state
```

#### 2. deterministic (`_deterministic_node`)

Fast path - builds and executes the pipeline with rule-based code (no LLM pipeline generation; intent was already extracted by the route node, and summarization is deterministic for common result shapes):

```python
def _deterministic_node(self, state: HybridAgentState) -> HybridAgentState:
    intent = state["intent"]

    # 1. Validate intent
    valid, error = self.validator.validate_intent(intent)
    if not valid:
        state["route"] = "fallback"
        return state

    # 2. Build MongoDB pipeline programmatically
    pipeline = self.query_builder.build(intent)

    # 3. Validate pipeline
    valid, error = self.validator.validate_pipeline(pipeline)
    if not valid:
        state["route"] = "fallback"
        return state

    # 4. Execute pipeline
    results = self.executor.execute(pipeline)

    # 5. Summarize results
    answer = self.summarizer.summarize(results, intent)

    state["response"] = {"answer": answer, "results": results}
    state["route"] = "stop"
    return state
```

#### 3. fallback (`_fallback_node`)

Calls the full LLM agent (Agent #2):

```python
def _fallback_node(self, state: HybridAgentState) -> HybridAgentState:
    result = self.fallback_agent.query(
        question=state["question"],
        conversation_history=state.get("conversation_history"),
    )
    state["response"] = result
    return state
```

### Supported Actions (Deterministic Path)

```python
SUPPORTED_ACTIONS = {
    QueryAction.LIST,        # "Show me purchases from..."
    QueryAction.COUNT,       # "How many orders..."
    QueryAction.TOP_N,       # "Top 5 departments..."
    QueryAction.BOTTOM_N,    # "Bottom 10 suppliers..."
    QueryAction.AGGREGATE,   # "Total spending by..."
    QueryAction.COMPARE,     # "Compare IT vs Non-IT..."
    QueryAction.TREND,       # "Spending trend over time..."
    QueryAction.SINGLE_VALUE # "What was total spending?"
}
```

---

## Agent #2: LangGraphMongoDBAgent

**File:** `src/api/services/ai_pipeline_agent/langgraph_agent.py`

**Purpose:** Full LLM-powered pipeline generation with automatic retries on failure.

### State Definition

```python
class AgentState(TypedDict, total=False):
    question: str                          # User's query
    conversation_history: Optional[List]   # Previous messages
    attempt: int                           # Current attempt number
    max_attempts: int                      # Default: 3
    reasoning_effort: str                  # GPT-5 reasoning effort
    verbosity: str                         # Answer verbosity
    pipeline: Optional[List]               # Generated MongoDB pipeline
    pipeline_response_id: Optional[str]    # Response ID from generation step
    latest_response: Optional[Any]         # Raw OpenAI response object
    previous_error: Optional[str]          # Error from last attempt (for retry)
    previous_response_id: Optional[str]    # For conversation continuity
    results: Optional[List]                # Query results
    answer: Optional[str]                  # Final answer
    error: Optional[str]                   # Terminal error if all retries fail
    reasoning_summary: Optional[str]       # Model's reasoning summary
    response_id: Optional[str]             # Final response ID (chain-of-thought)
```

### Graph Structure

```
                    ┌─────────────────┐
                    │     START       │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │    generate_pipeline     │◄─────────┐
              │                          │          │
              │  LLM generates MongoDB   │          │
              │  aggregation pipeline    │          │
              └────────────┬─────────────┘          │
                           │                        │
              ┌────────────┴────────────┐           │
              │                         │           │
              ▼                         ▼           │
         ┌─────────┐            ┌─────────────┐     │
         │  stop   │            │ run_pipeline│     │
         │  (END)  │            │             │     │
         └─────────┘            └──────┬──────┘     │
        (max retries                   │            │
         exceeded)         ┌───────────┴────────┐   │
                           │                    │   │
                           ▼                    ▼   │
                    ┌────────────┐         ┌───────┴───┐
                    │ summarize  │         │   retry   │
                    │            │         │           │
                    │ LLM creates│         │ Pass error│
                    │ answer     │         │ to LLM    │
                    └─────┬──────┘         └───────────┘
                          │
                          ▼
                    ┌─────────┐
                    │   END   │
                    └─────────┘
```

### Code Implementation

```python
def _build_graph(self):
    graph = StateGraph(AgentState)

    # Define 3 nodes
    graph.add_node("generate_pipeline", self._generate_pipeline_node)
    graph.add_node("run_pipeline", self._run_pipeline_node)
    graph.add_node("summarize", self._summarize_node)

    # Set entry point
    graph.set_entry_point("generate_pipeline")

    # After generate: run, retry, or stop
    graph.add_conditional_edges(
        "generate_pipeline",
        self._after_generate,
        {
            "run": "run_pipeline",
            "retry": "generate_pipeline",  # Loop back for retry!
            "stop": END,
        },
    )

    # After run: summarize, retry, or stop
    graph.add_conditional_edges(
        "run_pipeline",
        self._after_run,
        {
            "summarize": "summarize",
            "retry": "generate_pipeline",  # Loop back with error context!
            "stop": END,
        },
    )

    # Summarize always ends
    graph.add_edge("summarize", END)

    return graph.compile()
```

### Retry Logic (Key Feature)

The agent automatically retries up to 3 times, passing the error back to the LLM:

```python
def _after_generate(self, state: AgentState) -> str:
    if state.get("pipeline"):
        return "run"  # Success → run the pipeline
    if state.get("attempt", 0) >= state.get("max_attempts", 3):
        return "stop"  # Max retries → give up
    return "retry"  # Try again

def _after_run(self, state: AgentState) -> str:
    if state.get("error"):
        if state.get("attempt", 0) >= state.get("max_attempts", 3):
            return "stop"  # Max retries → give up
        return "retry"  # Pipeline failed → retry with error context
    return "summarize"  # Success → create answer
```

**Error context is passed to the LLM on retry:**

```python
def _generate_pipeline_node(self, state: AgentState) -> AgentState:
    attempt = state.get("attempt", 0) + 1
    state["attempt"] = attempt

    pipeline, response_id, latest_response, error = self.base._generate_pipeline_attempt(
        question=state["question"],
        conversation_history=state.get("conversation_history"),
        previous_error=state.get("previous_error"),          # ← Error from last attempt!
        previous_response_id=state.get("previous_response_id"),
        reasoning_effort=state.get("reasoning_effort", self.base.reasoning_effort),
    )

    state["pipeline"] = pipeline
    state["pipeline_response_id"] = response_id
    state["latest_response"] = latest_response
    state["previous_response_id"] = response_id  # Chain context into next call
    state["error"] = error
    state["previous_error"] = error              # Save for next retry
    return state
```

---

## Complete Flow Example

### Example 1: Fast Path (Deterministic)

**Query:** "Top 5 departments by spending"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HybridQueryEngine (Agent #1)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   decide_route:                                                              │
│   ├── Extract intent → { action: TOP_N, group_by: department }              │
│   ├── Ambiguous? NO                                                          │
│   ├── Action supported? YES (TOP_N ∈ SUPPORTED_ACTIONS)                     │
│   └── route = "deterministic"                                                │
│                                                                              │
│   deterministic:                                                             │
│   ├── Build pipeline → [{ $group }, { $sort }, { $limit }]                  │
│   ├── Validate → OK                                                          │
│   ├── Execute → [{ _id: "Health Care", value: 50B }, ...]                   │
│   └── Summarize → "1. Health Care: $50B ..."                                │
│                                                                              │
│   ✅ DONE (fast path: 1 intent-extraction LLM call, no pipeline generation) │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Example 2: Slow Path (Fallback with Retry)

**Query:** "Explain the spending patterns across departments"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HybridQueryEngine (Agent #1)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   decide_route:                                                              │
│   ├── Extract intent → { action: UNKNOWN }                                   │
│   ├── Action not in SUPPORTED_ACTIONS                                        │
│   └── route = "fallback"                                                     │
│                                                                              │
│   fallback: → Calls LangGraphMongoDBAgent (Agent #2)                        │
│                                                                              │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      LangGraphMongoDBAgent (Agent #2)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   generate_pipeline (attempt 1):                                             │
│   └── LLM generates pipeline → [{ $matchh: ... }]  ← typo!                  │
│                                                                              │
│   run_pipeline:                                                              │
│   └── Execute → Error: "unknown operator $matchh"                           │
│                                                                              │
│   generate_pipeline (attempt 2):  ← RETRY with error context!               │
│   └── LLM sees error, fixes pipeline → [{ $match: ... }]                    │
│                                                                              │
│   run_pipeline:                                                              │
│   └── Execute → Success!                                                     │
│                                                                              │
│   summarize:                                                                 │
│   └── LLM creates natural language answer                                    │
│                                                                              │
│   ✅ DONE (fallback path with 1 self-correcting retry)                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Why LangGraph?

| Feature | Without LangGraph | With LangGraph |
|---------|-------------------|----------------|
| **Retry logic** | Manual loops, messy code | Clean conditional edges with cycles |
| **State management** | Pass dictionaries manually | Typed state flows automatically |
| **Branching** | Nested if/else statements | Visual graph structure |
| **Error recovery** | Try/catch spaghetti | Edges handle failures gracefully |
| **Debugging** | Hard to trace execution flow | Can visualize and trace graph |
| **Extending** | Refactor large portions | Simply add new node + edge |

---

## Key LangGraph Concepts

| Concept | Description | Example |
|---------|-------------|---------|
| `StateGraph(State)` | Creates graph with typed state | `StateGraph(HybridAgentState)` |
| `add_node(name, func)` | Adds a processing step | `graph.add_node("decide_route", self._route_node)` |
| `add_edge(a, b)` | Unconditional: always go from a → b | `graph.add_edge("summarize", END)` |
| `add_conditional_edges` | Route based on function return value | See code examples above |
| `set_entry_point(name)` | Define where graph starts | `graph.set_entry_point("decide_route")` |
| `END` | Special terminal node | Ends the graph execution |
| `compile()` | Build the runnable graph | `app = graph.compile()` |
| `invoke(state)` | Run the graph with initial state | `result = app.invoke({"question": "..."})` |
