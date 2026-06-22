<div align="center">

# 🤖 AI-Powered Procurement Assistant

### Production-Ready Conversational AI for Government Procurement Data Analysis

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![GPT-5](https://img.shields.io/badge/GPT--5-Reasoning-00a67e.svg)](https://openai.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-ff4785.svg)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393.svg)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0+-47A248.svg)](https://www.mongodb.com)

**An enterprise-grade LLM-powered assistant that translates natural language queries into MongoDB operations for procurement data analysis**

[Overview](#-overview) • [Features](#-key-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Documentation](#-documentation)

</div>

---

## 📋 Project Overview

> **Objective:** A production-ready AI agent that converts natural language queries into accurate MongoDB queries for California state procurement data analysis.

### ✅ Capabilities

| Capability | Implementation | Status |
|-------------|----------------|--------|
| **Data Preparation** | Complete MongoDB import with optimized schema | ✅ Complete |
| **AI Agent Development** | GPT-5 with LangGraph orchestration | ✅ Complete |
| **Natural Language Processing** | Advanced prompt engineering with chain-of-thought | ✅ Complete |
| **MongoDB Query Generation** | Automated pipeline generation with validation | ✅ Complete |
| **Conversational Interface** | Web-based chat UI with conversation history | ✅ Complete |
| **Complex Query Handling** | Multi-step reasoning with retry logic | ✅ Complete |
| **Evaluation Framework** | 30+ test cases with automated benchmarking | ✅ Complete |
| **Production Ready** | Docker deployment, error handling, monitoring | ✅ Complete |

---

## 🎯 Overview

This project delivers a **production-ready, AI-powered procurement assistant** built around a **hybrid query architecture** — a fast, deterministic engine for the common case, with an LLM agent as an intelligent fallback for the long tail:

- **🧭 Hybrid Query Engine**: A LangGraph router classifies each question and sends it down the cheapest path that can answer it correctly — a deterministic pipeline builder for supported intents, or a GPT-5 agent for everything else
- **⚙️ Deterministic Engine**: Turns an LLM-extracted, structured *intent* into a MongoDB aggregation pipeline with **rule-based code** (no LLM in the query-building or execution loop) — fast, cheap, and reproducible
- **🤖 GPT-5 Fallback Agent**: A second LangGraph state machine that generates pipelines with OpenAI's reasoning models and **self-corrects** through a validate → retry loop
- **🛡️ Two-Layer Ambiguity Detection**: An LLM flags ambiguous questions and a deterministic detector double-checks, asking the user for clarification instead of guessing
- **💬 Conversational Context**: Multi-turn chain-of-thought continuity via the OpenAI Responses API (`previous_response_id`)
- **📊 Comprehensive Evaluation**: Automated benchmarking framework with 30+ test cases

### What Sets This Apart

1. **Hybrid, Cost-Aware Routing**: Most queries never hit the expensive pipeline-generation step — they're answered by deterministic code, reserving the GPT-5 agent for genuinely novel questions
2. **Two Cooperating LangGraph Graphs**: An outer routing graph and an inner self-correcting agent graph — not a single linear prompt chain
3. **Structured Intent, Not Free-Text Prompting**: Questions are parsed into a typed `QueryIntent` model (actions, metrics, dimensions, filters), which a deterministic builder compiles into validated aggregation pipelines
4. **Self-Correction**: The fallback agent validates each pipeline with a live MongoDB dry-run and regenerates on failure (up to 3 attempts)
5. **Production-Grade**: Fully containerized, health-monitored, with pre-execution query validation that blocks unsafe operators (`$where`, `$function`, `$accumulator`)

---

## ✨ Key Features

### 🤖 AI Agent Capabilities

**Natural Language Understanding**
- Interprets complex procurement questions in plain English
- Handles ambiguous queries with clarification strategies
- Maintains conversation context across multiple turns
- Supports follow-up questions and refinements

**Intelligent Query Generation**
- Automatically generates MongoDB aggregation pipelines
- Optimizes queries for performance (covering indexes, minimal stages)
- Validates generated queries before execution
- Self-corrects errors with retry logic

**Advanced Reasoning**
- GPT-5 reasoning effort: `minimal`, `low`, `medium`, `high`
- Chain-of-thought for multi-step analysis
- Verbosity control: `low`, `medium`, `high`
- Configurable result limits and response depth

### 💼 Procurement Analytics

**Supported Query Types**
- ✅ Temporal analysis (spending by quarter, year-over-year trends)
- ✅ Department analysis (top spenders, category breakdowns)
- ✅ Supplier analytics (vendor concentration, qualification analysis)
- ✅ Item analysis (most ordered products, price trends)
- ✅ Geographic analysis (spending by location)
- ✅ Comparative analysis (IT vs NON-IT spending)
- ✅ Statistical aggregations (averages, totals, distributions)

**Example Questions**
```
"What was the total spending in Q2 2014?"
"Which department spent the most on IT goods?"
"Show me the top 10 suppliers by order volume"
"Compare IT and NON-IT spending trends across fiscal years"
"What's the average purchase price for computer equipment?"
"Which quarter had the highest spending?"
"List all purchases over $100,000 from San Francisco suppliers"
```

**Deterministic-First Examples**
```
"Compare spending by department and fiscal year"
"Trend total spending by fiscal year"
"Top 5 suppliers by average unit price in 2014"
"List purchases between 2014-01-01 and 2014-12-31"
"Count orders by acquisition method"
```

### 🏗️ Technical Excellence

**Backend (FastAPI + MongoDB)**
- RESTful API with OpenAPI documentation
- Async I/O for high concurrency
- Connection pooling and query optimization
- Comprehensive error handling
- Health monitoring and metrics

**Query Engine (Hybrid: Deterministic + GPT-5 + LangGraph)**
- LangGraph routing graph: deterministic path vs. AI fallback
- LLM intent extraction into a typed `QueryIntent` model
- Rule-based aggregation-pipeline builder for 8 query actions
- Self-correcting GPT-5 fallback with validate → retry loop
- Mostly LLM-free result summarization (deterministic formatters)

**Frontend (Modern Web)**
- Real-time chat interface
- Conversation history
- Code highlighting for generated queries
- Responsive design (desktop & mobile)
- Dark mode support

**Data Layer (MongoDB)**
- 18+ strategic indexes
- Geospatial capabilities (2dsphere)
- Full-text search with weighted scoring
- Optimized aggregation pipelines
- ~346,000 procurement records

---

## 🏗️ Architecture

### System Design

A natural-language question enters through the FastAPI `ai_query` router, which holds a single
`HybridQueryEngine`. That engine is built on **two cooperating LangGraph state machines**: an
**outer routing graph** that decides *how* to answer, and an **inner agent graph** that handles the
GPT-5 fallback with self-correction.

```
┌─────────────────────────────────────────────────────────────────┐
│         User Interface  (Web Chat / API Clients)                 │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│   FastAPI  ·  POST /api/ai/query  ·  src/api/routes/ai_query.py  │
│           (validation · conversation state · formatting)         │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
╔═════════════════════════════════════════════════════════════════╗
║   HybridQueryEngine — OUTER LangGraph router                     ║
║                                                                   ║
║      ┌──────────────┐                                            ║
║      │ decide_route │  LLM intent extraction (gpt-5-mini) →      ║
║      └──────┬───────┘  typed QueryIntent + 2-layer ambiguity     ║
║             │                                                     ║
║      ┌──────┼───────────────────────────────┐                    ║
║      ▼      ▼                                ▼                    ║
║   "stop"  "deterministic"               "fallback"               ║
║  (clarify) │                                │                    ║
║      │     ▼                                 ▼                    ║
║      │  ┌────────────────┐         ┌────────────────────────┐    ║
║      │  │ deterministic  │         │  GPT-5 Fallback Agent   │   ║
║      │  │     node       │         │  (INNER LangGraph)      │   ║
║      │  │ build → valid. │         │  generate → run ⟲ retry │   ║
║      │  │ → exec → summ. │         │  → summarize            │   ║
║      │  └───────┬────────┘         └───────────┬─────────────┘   ║
║      │          │ (on any failure → fallback)  │                 ║
║      └──────────┴──────────────┬───────────────┘                 ║
╚═════════════════════════════════╪═══════════════════════════════╝
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│   MongoDB · purchase_orders                                      │
│   ~346K line items · 18+ indexes · geospatial · UNSPSC taxonomy  │
└─────────────────────────────────────────────────────────────────┘
```

### How LangGraph Is Used

LangGraph powers **two distinct state graphs**, not a single linear chain. Each is a compiled
`StateGraph` with a typed state (`TypedDict`) and **conditional edges** that branch on the result of
the previous node.

#### Graph 1 — `HybridQueryEngine` (the router)

*Defined in `src/api/services/deterministic_engine/agent.py`.*

| Node | Responsibility |
|------|----------------|
| `decide_route` | Calls the LLM intent extractor (`gpt-5-mini`, JSON mode) to parse the question into a typed `QueryIntent`, runs **two-layer ambiguity detection**, then routes. |
| `deterministic` | Normalizes the intent, builds an aggregation pipeline with rule-based code, validates it, executes it, and summarizes — all without an LLM in the loop (except optional summary). |
| `fallback` | Hands the question to the GPT-5 agent graph (Graph 2). |

```
START ──▶ decide_route ──┬─ route=="stop"           ──▶ END   (ask user to clarify)
                         ├─ route=="deterministic"  ──▶ deterministic ──┬─ "stop"     ──▶ END
                         │                                              └─ "fallback" ──▶ fallback ──▶ END
                         └─ route=="fallback"       ──▶ fallback ───────────────────────────────────▶ END
```

**Routing rules** (in `decide_route`):
- **Ambiguous** (LLM flag *or* the deterministic detector) → `stop`, return a clarification prompt instead of guessing.
- **Supported action** (`LIST`, `COUNT`, `TOP_N`, `BOTTOM_N`, `AGGREGATE`, `SINGLE_VALUE`, `COMPARE`, `TREND`) → `deterministic`.
- **Unrecognized/unsupported** intent, or any error during extraction → `fallback`.

Crucially, the `deterministic` node is **self-defending**: if intent normalization, validation, pipeline-building, or execution fails at *any* step, it silently re-routes to `fallback` rather than surfacing an error — so the user always gets an answer if either engine can produce one.

#### Graph 2 — `LangGraphMongoDBAgent` (the self-correcting fallback)

*Defined in `src/api/services/ai_pipeline_agent/langgraph_agent.py`.*

| Node | Responsibility |
|------|----------------|
| `generate_pipeline` | GPT-5 generates a MongoDB aggregation pipeline (free-form JSON output) via the OpenAI **Responses API**, chaining context with `previous_response_id`. |
| `run_pipeline` | Validates the pipeline with a **live MongoDB dry-run** (1s timeout), then executes it. On failure it clears the pipeline and records the error. |
| `summarize` | Turns results into a natural-language answer, reusing the generation step's response ID for chain-of-thought continuity. |

```
START ──▶ generate_pipeline ──┬─ pipeline ok      ──▶ run_pipeline ──┬─ no error          ──▶ summarize ──▶ END
                              │                                      ├─ error & retries left ──▶ generate_pipeline   ⟲
                              │                                      └─ error & out of tries ──▶ END
                              ├─ no pipeline & retries left ─────────────────────────────────▶ generate_pipeline    ⟲
                              └─ out of tries ──────────────────────────────────────────────▶ END
```

The retry loop (default **3 attempts**) feeds the previous error back into the next generation prompt, so the model learns from its own failed pipeline — this is the "self-correction" that makes the fallback robust on novel or malformed queries.

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **AI Model** | GPT-5 series (Responses API) | Intent extraction (`gpt-5-mini`) & pipeline generation |
| **Agent Framework** | LangGraph | Two state graphs: hybrid router + self-correcting fallback |
| **Deterministic Engine** | Pure Python | Rule-based intent → aggregation-pipeline compilation |
| **Backend** | FastAPI 0.104+ | High-performance async REST API |
| **Database** | MongoDB 7.0+ | Document store with advanced querying |
| **DB Driver** | PyMongo 4.6+ | Python MongoDB driver with connection pooling |
| **Import Pipeline** | Python 3.9+ Pandas | ETL with validation & transformation |
| **Web UI** | Vanilla JS + HTML5 | Responsive chat interface |
| **Deployment** | Docker Compose | Containerized multi-service stack |
| **Storage** | Git LFS | Efficient large file management (156MB CSV) |

### MongoDB Communication Flow

The system communicates with MongoDB through a sophisticated pipeline:

1. **Connection Management**
   - Uses PyMongo driver with connection pooling
   - Single `MongoClient` instance shared across requests
   - Configured in `src/api/dependencies.py`
   - Connection string: `mongodb://admin:password@mongodb:27017`

2. **Query Generation Flow**
   ```
   Deterministic path:
     Question → LLM intent extraction → QueryIntent → rule-based builder
              → validate → PyMongo aggregate → MongoDB → Results

   Fallback path (novel/unsupported queries):
     Question → GPT-5 pipeline generation → dry-run validate ⟲ retry
              → PyMongo aggregate → MongoDB → Results
   ```

3. **MongoDB Integration (both engines)**
   - **Intent Extractor** (`deterministic_engine/intent_extractor.py`): `gpt-5-mini` parses the question into a typed `QueryIntent` (JSON mode)
   - **Query Builder** (`deterministic_engine/query_builder.py`): compiles the intent into an aggregation pipeline with deterministic code (8 action builders)
   - **Pipeline Generator** (`ai_pipeline_agent/pipeline_generator.py`): GPT-5 generates a pipeline directly for fallback cases
   - **Validators**: structural checks plus a **live MongoDB dry-run**; unsafe operators (`$where`, `$function`, `$accumulator`) are blocked
   - **Executors**: run validated pipelines via PyMongo `collection.aggregate()` with a 30s `maxTimeMS`
   - **Error Recovery**: the fallback agent retries with the previous error fed back into the prompt (max 3 attempts)

4. **Direct MongoDB Operations**
   - **Import**: Batch inserts via PyMongo `insert_many()` with 5,000 document batches
   - **Indexing**: Executed via MongoDB shell scripts (`init-indexes.js`)
   - **Queries**: Aggregation pipelines executed through PyMongo
   - **Statistics**: Uses MongoDB native aggregation framework

5. **Connection Configuration**
   ```python
   # FastAPI startup
   client = MongoClient(
       host="mongodb",
       port=27017,
       username="admin",
       password="changeme_secure_password",
       maxPoolSize=50,  # Connection pool
       serverSelectionTimeoutMS=5000
   )
   db = client.government_procurement
   collection = db.purchase_orders
   ```

**Key Features:**
- ✅ Connection pooling for concurrent requests
- ✅ Automatic reconnection on network failures
- ✅ Query timeout protection (90 seconds default)
- ✅ Aggregation pipeline validation before execution
- ✅ Result streaming for large datasets

---

## 🚀 Quick Start

### Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Git** with **Git LFS** installed
- **OpenAI API Key** (for GPT-5)
- **8GB RAM** minimum (16GB recommended)
- **5GB** disk space

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/theflyingdutch789/procurement-agentic-system.git
   cd procurement-agentic-system
   ```

2. **Pull LFS files** (156MB dataset)
   ```bash
   git lfs install
   git lfs pull
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env

   # Edit .env and add your OpenAI API key:
   echo "OPENAI_API_KEY=your_key_here" >> .env
   ```

4. **Run automated setup**
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

   **The setup script will:**
   - ✓ Validate dependencies (Docker, Git LFS)
   - ✓ Start MongoDB container
   - ✓ Import 346K+ records (~10-15 minutes)
   - ✓ Create 18+ optimized indexes
   - ✓ Start API service
   - ✓ Launch web interface
   - ✓ Run validation checks

5. **Verify installation**
   ```bash
   # Check API health
   curl http://localhost:8000/api/health

   # Test AI agent
   curl -X POST http://localhost:8000/api/ai/query \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What was the total spending in 2014?",
       "reasoning_effort": "medium"
     }'
   ```

6. **Access the application**
   - **Web Interface**: http://localhost:8000 (Chat UI)
   - **API Docs**: http://localhost:8000/docs (Swagger)
   - **Alternative Docs**: http://localhost:8000/redoc

### Manual Setup (Alternative)

```bash
# 1. Configure environment
cp .env.example .env
# Add OPENAI_API_KEY to .env

# 2. Start MongoDB and import data (one-time, ~15 min)
docker-compose --profile seed up importer

# 3. Start all services
docker-compose up -d mongodb api web

# 4. Monitor logs
docker-compose logs -f api
```

---

## 💬 Using the AI Assistant

### Web Interface

1. Open http://localhost:8000 in your browser
2. Type your question in natural language
3. Receive instant answers with supporting data
4. View the generated MongoDB query
5. Continue the conversation with follow-ups

**Example Conversation:**
```
You: "What was the total spending in 2014?"
AI: "The total spending in fiscal year 2013-2014 was $2,847,392,156.78"

[Shows generated MongoDB pipeline]

You: "Which department contributed the most to that?"

AI: "The Department of Corrections and Rehabilitation spent $487,234,891.45,
     representing 17.1% of the total 2014 spending."
```

### API Usage

**Basic Query**
```bash
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me the top 5 suppliers by total spending",
    "reasoning_effort": "medium",
    "max_results": 5
  }'
```

**With Conversation Context**
```bash
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What about IT goods specifically?",
    "conversation_id": "conv_123",
    "conversation_history": [...],
    "reasoning_effort": "high"
  }'
```

**Advanced Configuration**
```bash
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Complex multi-step analysis query",
    "model": "gpt-5",
    "reasoning_effort": "high",
    "verbosity": "high",
    "max_results": 100
  }'
```

---

## 📚 Documentation

### API Endpoints

Once running, access these services:

| Service | URL | Description |
|---------|-----|-------------|
| **Web Chat** | http://localhost:8000 | Interactive chat interface |
| **Swagger UI** | http://localhost:8000/docs | Interactive API documentation |
| **ReDoc** | http://localhost:8000/redoc | Alternative API documentation |
| **Health Check** | http://localhost:8000/api/health | Service status |
| **AI Query** | POST /api/ai/query | Natural language to MongoDB |
| **MongoDB** | localhost:27017 | Database (credentials in .env) |

### AI Agent Configuration

**GPT-5 Model & Reasoning Configurations**

| Profile | Model | Reasoning Effort | Use Case | Performance |
|---------|-------|------------------|----------|-------------|
| **Fast** | GPT-5-nano | Low | Simple queries, quick lookups | Fastest, cost-effective |
| **Normal** | GPT-5-mini | Low | Standard queries, basic aggregations | Fast, balanced |
| **Medium** | GPT-5 | Medium | Complex analysis, multi-step queries | Balanced, high quality |
| **High** | GPT-5 | High | Advanced reasoning, edge cases | Thorough, best quality |

**Configuration Details:**
- **Fast**: Uses `gpt-5-nano` with `low` reasoning - optimized for speed and cost
- **Normal**: Uses `gpt-5-mini` with `low` reasoning - balanced performance
- **Medium**: Uses `gpt-5` with `medium` reasoning - recommended for most queries
- **High**: Uses `gpt-5` with `high` reasoning - maximum accuracy for complex scenarios

**Verbosity Levels**

| Level | Description | Best For |
|-------|-------------|----------|
| **low** | Concise answers | Quick facts |
| **medium** | Balanced detail | General use |
| **high** | Comprehensive explanations | Learning, analysis |

### Additional Documentation

- **[Technical Architecture](TECHNICAL_ARCHITECTURE.md)**: Deep dive into the hybrid engine, routing, and component design
- **[LangGraph Explained](LANGGRAPH_EXPLAINED.md)**: Both state graphs, nodes, edges, and retry logic
- **[Multi-Tenant Data Strategy](MULTI_TENANT_DATA_STRATEGY.md)**: Scaling the hybrid approach across clients/schemas
- **[MQL Query Examples](MQL_QUERY_EXAMPLES.md)**: Natural-language questions mapped to MongoDB queries
- **[Evaluation System](evaluation/README.md)**: AI agent benchmarking framework (30+ test cases)

---

## 🔌 Main API Endpoint

### POST /api/ai/query

The primary endpoint for natural language queries using GPT-5 and LangGraph.

**Request Body:**
```json
{
  "question": "What was the total spending in 2014?",
  "conversation_id": "optional-conv-id",
  "conversation_history": [],
  "reasoning_effort": "medium",
  "verbosity": "medium",
  "max_results": 10,
  "model": "gpt-5"
}
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `question` | string | ✅ Yes | - | Natural language question |
| `conversation_id` | string | No | null | ID for conversation tracking |
| `conversation_history` | array | No | [] | Previous messages for context |
| `reasoning_effort` | string | No | "medium" | Reasoning level: `minimal`, `low`, `medium`, `high` |
| `verbosity` | string | No | "medium" | Response detail: `low`, `medium`, `high` |
| `max_results` | integer | No | 10 | Max results to return (1-1000) |
| `model` | string | No | "gpt-5" | Model: `gpt-5`, `gpt-5-mini`, `gpt-5-nano` |

**Recommended Configurations:**
- **Fast queries**: `model: "gpt-5-nano"`, `reasoning_effort: "low"`
- **Standard queries**: `model: "gpt-5-mini"`, `reasoning_effort: "low"`
- **Complex queries**: `model: "gpt-5"`, `reasoning_effort: "medium"` (default)
- **Advanced queries**: `model: "gpt-5"`, `reasoning_effort: "high"`

**Response:**
```json
{
  "success": true,
  "answer": "The total spending in fiscal year 2013-2014 was $2,847,392,156.78",
  "pipeline": [
    {"$match": {"dates.fiscal_year": {"$regex": "2014"}}},
    {"$group": {"_id": null, "total": {"$sum": "$item.total_price"}}}
  ],
  "results": [
    {"_id": null, "total": 2847392156.78}
  ],
  "result_count": 1,
  "reasoning_summary": "Generated aggregation pipeline to sum all purchase prices...",
  "timestamp": "2025-01-05T10:30:00Z",
  "execution_time_seconds": 2.34
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Query validation failed: Invalid field reference",
  "timestamp": "2025-01-05T10:30:00Z"
}
```

---

## 📊 Data Schema

### Document Structure

The MongoDB schema is optimized for LLM text-to-query inference:

```javascript
{
  // Unique identifier
  purchase_order_number: String,

  // Temporal information
  dates: {
    creation: ISODate,
    purchase: ISODate,
    fiscal_year: String        // Format: "YYYY-YYYY"
  },

  // Acquisition details
  acquisition: {
    type: String,              // IT Goods, NON-IT Goods, IT Services, NON-IT Services
    sub_type: String,
    method: String,            // Competitive, Sole Source, etc.
    sub_method: String
  },

  // Purchasing department
  department: {
    name: String,
    normalized_name: String    // Cleaned, consistent name
  },

  // Supplier information
  supplier: {
    code: String,
    name: String,
    qualifications: [String],  // DVBE, Small Business, etc.
    zip_code: String,
    location: {                // GeoJSON Point (2dsphere indexed)
      type: "Point",
      coordinates: [lon, lat]
    }
  },

  // Item details
  item: {
    name: String,
    description: String,
    quantity: Number,
    unit_price: Number,
    total_price: Number
  },

  // UNSPSC classification
  classification: {
    unspsc: {
      segment: { code: String, title: String },
      family: { code: String, title: String },
      class: { code: String, title: String },
      commodity: { code: String, title: String }
    }
  }
}
```

See **[collection_schemas.json](collection_schemas.json)** for the full field inventory, or query the live `GET /api/ai/schema` endpoint.

---

## ⚡ Performance

### Benchmarks

| Metric | Value | Notes |
|--------|-------|-------|
| **Import Time** | 10-15 min | Full dataset with validation |
| **Database Size** | 1.2-1.8 GB | Includes all indexes |
| **Simple Query** | <100ms | Basic filters & counts |
| **Complex Query** | <500ms | Multi-stage aggregations |
| **GPT-5 Processing** | 2-5s | With medium reasoning |
| **Web Response** | <3s | End-to-end query + answer |
| **Concurrent Users** | 50+ | With single API instance |

### Optimization Strategies

- **Hybrid Routing**: Supported queries skip GPT-5 pipeline generation entirely, answered by deterministic code
- **GPT-5 Reasoning**: Adaptive effort based on query complexity
- **Deterministic Summarization**: Common result shapes are formatted without an LLM call
- **MongoDB Indexes**: 18+ strategic indexes for common query patterns
- **Connection Pooling**: Reused connections for high throughput
- **Async I/O**: Non-blocking request handling with FastAPI
- **Query Validation**: Pre-execution checks prevent invalid queries
- **Result Streaming**: Progressive response for better UX

---

## 🧪 Evaluation System

The project includes a comprehensive AI agent evaluation framework with 30+ test cases.

### Quick Evaluation

```bash
# Run full evaluation suite
./scripts/run_eval.sh

# Run with custom profile
python evaluation/eval_system.py \
  --profiles "gpt-5:high:10" "gpt-5-mini:medium:5" \
  --output-dir ./reports/evaluations
```

### Test Categories

- **Basic Queries** (easy): Simple counts, sums, and filters - 95%+ pass rate
- **Intermediate Queries** (medium): Grouping, sorting, joins - 85%+ pass rate
- **Advanced Queries** (hard): Complex aggregations - 70%+ pass rate
- **Ultra Queries** (very hard): Geospatial, temporal analysis - 50%+ pass rate

**See [evaluation/README.md](evaluation/README.md) for complete documentation.**

---

## 💻 Development

### Project Structure

```
procurement-agentic-system/
├── data/                           # Dataset (Git LFS)
│   └── purchase_orders_2012_2015.csv
├── docker/                         # Container definitions
│   ├── Dockerfile.api
│   └── Dockerfile.importer
├── TECHNICAL_ARCHITECTURE.md       # Hybrid engine deep dive
├── LANGGRAPH_EXPLAINED.md          # Both LangGraph state graphs
├── collection_schemas.json         # Full field inventory
├── evaluation/                     # AI evaluation framework
│   ├── README.md
│   ├── eval_system.py
│   ├── test_catalog.py
│   └── ...
├── src/
│   ├── api/                        # FastAPI application
│   │   ├── main.py                 # FastAPI app
│   │   ├── routes/
│   │   │   ├── ai_query.py        # AI agent endpoints
│   │   │   ├── query.py           # Standard query endpoints
│   │   │   └── health.py          # Health checks
│   │   └── services/
│   │       ├── deterministic_engine/   # Hybrid router + rule-based engine
│   │       │   ├── agent.py             # HybridQueryEngine (outer LangGraph)
│   │       │   ├── intent_extractor.py  # LLM → typed QueryIntent
│   │       │   ├── intent_sanitizer.py  # ambiguity coordination
│   │       │   ├── ambiguity_detector.py# deterministic ambiguity safety net
│   │       │   ├── query_builder.py     # intent → aggregation pipeline
│   │       │   ├── field_mappings.py    # enum → MongoDB field paths
│   │       │   ├── validator.py         # intent + pipeline validation
│   │       │   ├── executor.py          # pipeline execution
│   │       │   ├── summarizer.py        # deterministic/LLM answer formatting
│   │       │   └── models/intent.py     # QueryIntent Pydantic models
│   │       ├── ai_pipeline_agent/       # GPT-5 fallback agent
│   │       │   ├── agent.py             # GPT5MongoDBAgent (Responses API)
│   │       │   ├── langgraph_agent.py   # self-correcting inner LangGraph
│   │       │   ├── pipeline_generator.py
│   │       │   ├── executor.py
│   │       │   ├── validators.py
│   │       │   ├── summarizer.py
│   │       │   ├── prompts.py
│   │       │   └── schema.py
│   │       └── shared/                  # Mongo serialization + OpenAI helpers
│   ├── importer/                   # CSV import pipeline
│   └── validation/                 # Data validation
├── src/web/                        # Web interface
│   └── static/
│       ├── index.html              # Chat UI
│       ├── css/
│       └── js/
├── scripts/                        # Automation scripts
│   ├── setup.sh                    # One-command setup
│   ├── run_eval.sh                 # Run evaluations
│   └── init-indexes.js             # MongoDB indexes
├── docker-compose.yml              # Service orchestration
├── .env.example                    # Environment template
└── README.md                       # This file
```

### Local Development

```bash
# Install dependencies
pip install -r src/api/requirements.txt
pip install -r evaluation/requirements.txt

# Run API locally (requires MongoDB)
cd src/api
uvicorn main:app --reload --port 8000

# Run tests
python -m pytest tests/

# Run evaluation
python evaluation/eval_system.py --profiles "gpt-5:high:10"
```

### Environment Variables

Key configuration in `.env`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_api_key_here

# MongoDB Configuration
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_DATABASE=government_procurement
MONGO_USERNAME=admin
MONGO_PASSWORD=changeme_secure_password

# API Configuration
API_PORT=8000
API_WORKERS=4
LOG_LEVEL=INFO

# Import Configuration
BATCH_SIZE=5000
CSV_FILE_PATH=/data/purchase_orders_2012_2015.csv
```

---

## 🚢 Deployment

### Docker Compose (Production)

```bash
# Start all services
docker-compose up -d mongodb api web

# View logs
docker-compose logs -f api

# Scale API workers
docker-compose up -d --scale api=4

# Stop services
docker-compose down

# Full cleanup (including data)
docker-compose down -v
```

### Re-importing Data

```bash
# Stop API (keep MongoDB running)
docker-compose stop api

# Run importer with seed profile
docker-compose --profile seed up importer

# Restart API
docker-compose up -d api
```

### Health Monitoring

```bash
# Check all services
docker-compose ps

# Check API health
curl http://localhost:8000/api/health

# MongoDB connection
docker-compose exec mongodb mongosh \
  -u admin -p changeme_secure_password \
  --authenticationDatabase admin
```

---

## 🔧 Troubleshooting

### Common Issues

**OpenAI API Key Not Set**
```bash
# Error: "OPENAI_API_KEY not found"
# Solution:
echo "OPENAI_API_KEY=your_key_here" >> .env
docker-compose restart api
```

**Import Fails**
```bash
# Check importer logs
docker-compose --profile seed logs importer

# Verify CSV file exists
ls -lh data/purchase_orders_2012_2015.csv

# Restart import (drops existing data)
docker-compose --profile seed up --force-recreate importer
```

**API Not Responding**
```bash
# Check API logs
docker-compose logs --tail=100 api

# Restart API
docker-compose restart api

# Check health endpoint
curl -v http://localhost:8000/api/health
```

**MongoDB Connection Issues**
```bash
# Check MongoDB status
docker-compose ps mongodb

# View MongoDB logs
docker-compose logs mongodb

# Restart MongoDB
docker-compose restart mongodb
```

**GPT-5 Rate Limits**
```bash
# Error: "Rate limit exceeded"
# Solution: Use lower reasoning effort or implement request queuing
# Or: Upgrade OpenAI API tier
```

---

## 🎯 Project Deliverables

### ✅ Feature Checklist

- [x] **GitHub Repository**: https://github.com/theflyingdutch789/procurement-agentic-system
- [x] **Well-Documented Code**: Comprehensive inline documentation and README
- [x] **MongoDB Integration**: Complete data import with optimized schema
- [x] **AI Agent**: GPT-5 powered with LangGraph orchestration
- [x] **Natural Language Queries**: Full conversational interface
- [x] **Complex Query Handling**: Multi-step reasoning with validation
- [x] **Web Interface**: Modern chat UI with real-time responses
- [x] **Evaluation Framework**: 30+ automated test cases
- [x] **Production Ready**: Docker deployment, error handling, monitoring

---

## 🏆 Key Innovations

1. **Hybrid Deterministic + LLM Architecture**: A LangGraph router answers supported queries with fast, reproducible, rule-based code and reserves the GPT-5 agent for the long tail — cutting cost and latency without sacrificing coverage

2. **Two Cooperating LangGraph Graphs**: An outer routing state machine and an inner self-correcting agent, each with typed state and conditional edges

3. **Structured Intent Compilation**: Questions become a typed `QueryIntent` model that a deterministic builder compiles into validated MongoDB aggregation pipelines — no free-text prompt-to-query guessing on the happy path

4. **Self-Correction**: The fallback agent dry-runs each pipeline against MongoDB and regenerates from its own error (up to 3 attempts)

5. **Clarify Instead of Guess**: Two-layer ambiguity detection (LLM + deterministic) asks the user a follow-up rather than returning a confidently-wrong answer

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📊 Dataset Information

- **Source**: California State Government Purchase Orders (Kaggle)
- **Time Period**: 2012-2015 (4 fiscal years)
- **Record Count**: ~346,000 purchase orders
- **Categories**: IT Goods, IT Services, NON-IT Goods, NON-IT Services
- **Coverage**: All California state departments
- **Classification**: UNSPSC (United Nations Standard Products and Services Code)
- **Geolocation**: Supplier locations with lat/lon coordinates

---

## 🙏 Acknowledgments

- California State Government for providing open procurement data via Kaggle
- OpenAI for GPT-5 Reasoning API
- LangChain team for LangGraph framework
- FastAPI framework for high-performance API development
- MongoDB for flexible document storage and powerful aggregation capabilities

---

<div align="center">

**Built with 🧠 — LLM-Powered Conversational AI**

**Production-Ready • LLM-Powered • Conversational AI**

[Report Bug](https://github.com/theflyingdutch789/procurement-agentic-system/issues) • [Request Feature](https://github.com/theflyingdutch789/procurement-agentic-system/issues)

</div>
