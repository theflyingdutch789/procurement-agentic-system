# Sunday Demo Preparation Plan

## Your Situation
- Demo to CTO on Sunday
- Need to understand Frontend, Backend, AI implementation deeply
- Must be able to run queries and explain MongoDB pipelines live

---

## Day-by-Day Schedule

### Day 1: Wednesday - Architecture Overview & MongoDB Basics
**Goal:** Understand the big picture + be comfortable with MongoDB

#### Morning (2-3 hours)
- [ ] Read this entire study plan
- [ ] Draw the architecture diagram BY HAND (see below)
- [ ] Understand data flow: User → Web → API → AI Agent → MongoDB → Response

#### Afternoon (2-3 hours)
- [ ] Connect to MongoDB via Compass
- [ ] Explore the `purchase_orders` collection - look at 5-10 documents
- [ ] Understand the document schema (see Schema section below)
- [ ] Practice 10 basic MongoDB queries in mongosh

#### Evening (1-2 hours)
- [ ] Write down 5 things you learned today
- [ ] Quiz yourself: Can you explain what each service does?

---

### Day 2: Thursday - Backend Deep Dive (FastAPI + AI Agent)
**Goal:** Understand how queries become MongoDB pipelines

#### Morning (2-3 hours)
- [ ] Read `src/api/main.py` - understand the API structure
- [ ] Read `src/api/routes/ai_query.py` - this is where queries come in
- [ ] Trace a query from API endpoint to response

#### Afternoon (3-4 hours)
- [ ] **CRITICAL**: Read `src/api/services/mongodb_agent/` folder:
  - `agent.py` - Main orchestration
  - `pipeline_generator.py` - How prompts become MongoDB pipelines
  - `prompts.py` - The system prompts sent to GPT
  - `summarizer.py` - How results become human answers
- [ ] Understand the retry logic (max 3 attempts)

#### Evening (1-2 hours)
- [ ] Run 3 queries on the platform, then find the generated pipeline in logs
- [ ] Try to understand why each pipeline stage exists

---

### Day 3: Friday - Frontend + End-to-End Flow
**Goal:** Understand the UI and be able to trace full request cycle

#### Morning (2-3 hours)
- [ ] Read `src/web/app.py` - Flask routes
- [ ] Read `src/web/routes/chat.py` - Chat endpoint
- [ ] Read `src/web/static/js/chat.js` - Frontend JavaScript

#### Afternoon (2-3 hours)
- [ ] Open browser DevTools, watch Network tab while making queries
- [ ] Trace a request: Browser → Flask → FastAPI → OpenAI → MongoDB → Back
- [ ] Understand how the chat history is maintained

#### Evening (2 hours)
- [ ] Practice explaining the architecture out loud (record yourself)
- [ ] Write down the 3 most impressive technical decisions in this project

---

### Day 4: Saturday - Practice Demo + Deep MongoDB
**Goal:** Rehearse the actual demo multiple times

#### Morning (3 hours)
- [ ] Practice Demo Run #1 (see Demo Script below)
- [ ] Note where you stumbled
- [ ] Research those areas

#### Afternoon (3 hours)
- [ ] Practice Demo Run #2
- [ ] Practice switching between Web UI and MongoDB Compass smoothly
- [ ] Practice explaining a MongoDB aggregation pipeline stage by stage

#### Evening (2-3 hours)
- [ ] Practice Demo Run #3 (time yourself - aim for 20-30 min)
- [ ] Prepare for potential questions (see FAQ section)
- [ ] Get good sleep!

---

### Day 5: Sunday - Final Prep & Demo
**Goal:** Confident, smooth demo

#### Before Demo (1-2 hours)
- [ ] Quick review of key talking points
- [ ] Make sure all services are running (`make status`)
- [ ] Have MongoDB Compass open and connected
- [ ] Have browser open to http://localhost:5000
- [ ] Clear chat history for fresh start
- [ ] Deep breaths, you've got this

---

## Architecture Diagram (Draw This By Hand!)

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER                                       │
│                      (Browser @ :5000)                               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FLASK WEB SERVER (Port 5000)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │  app.py     │  │ chat.py     │  │ static/     │                  │
│  │  (routes)   │  │ (chat API)  │  │ (HTML/JS)   │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼ HTTP POST /api/ai/query
┌─────────────────────────────────────────────────────────────────────┐
│                    FASTAPI SERVER (Port 8000)                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    AI Query Route                            │    │
│  │                 /api/ai/query endpoint                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  GPT-5 MongoDB Agent                         │    │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐    │    │
│  │  │ Pipeline      │  │ Executor      │  │ Summarizer    │    │    │
│  │  │ Generator     │  │ (runs query)  │  │ (human answer)│    │    │
│  │  │ (GPT → Mongo) │  │               │  │               │    │    │
│  │  └───────────────┘  └───────────────┘  └───────────────┘    │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
           │                        │                      │
           ▼                        ▼                      ▼
    ┌─────────────┐         ┌─────────────┐        ┌─────────────┐
    │   OpenAI    │         │   MongoDB   │        │   OpenAI    │
    │   GPT API   │         │  (Port 27017)│        │   GPT API   │
    │ (generate   │         │             │        │ (summarize  │
    │  pipeline)  │         │ purchase_   │        │  results)   │
    └─────────────┘         │ orders      │        └─────────────┘
                            │ collection  │
                            └─────────────┘
```

---

## Document Schema (Memorize This!)

```javascript
{
  "_id": ObjectId("..."),

  // Purchase Order Info
  "po_number": "PO123456",
  "requisition_number": "REQ789",
  "lpa_number": "7-12-70-26",

  // Dates
  "dates": {
    "creation_date": ISODate("2013-08-27"),
    "purchase_date": ISODate("2013-08-27"),
    "fiscal_year": "2013-2014"
  },

  // Department
  "department": {
    "name": "Consumer Affairs, Department of",
    "normalized_name": "CONSUMER AFFAIRS"
  },

  // Supplier
  "supplier": {
    "code": "1740272",
    "name": "Pitney Bowes",
    "zip_code": "94105",
    "qualifications": null
  },

  // Item Details
  "item": {
    "name": "USB Cable",
    "description": "USB 3.0 Cable 6ft",
    "quantity": 10,
    "unit_price": 5.99,
    "total_price": 59.90
  },

  // Classification (UNSPSC)
  "classification": {
    "code": "43211706",
    "normalized_unspsc": "43211706",
    "commodity_title": "USB cables",
    "class_code": "4321",
    "class_title": "Computer cables",
    "family_code": "43",
    "family_title": "IT Components",
    "segment_code": "43",
    "segment_title": "IT Equipment"
  },

  // Acquisition
  "acquisition": {
    "type": "IT Goods",
    "sub_type": null,
    "method": "WSCA/Coop",
    "sub_method": null
  },

  // Flags
  "cal_card": false  // CalCard = California procurement card
}
```

---

## 10 MongoDB Practice Queries (Run These!)

```javascript
// 1. Count all documents
db.purchase_orders.countDocuments()

// 2. Find one document (see the schema)
db.purchase_orders.findOne()

// 3. Total spending
db.purchase_orders.aggregate([
  { $group: { _id: null, total: { $sum: "$item.total_price" } } }
])

// 4. Spending by fiscal year
db.purchase_orders.aggregate([
  { $group: { _id: "$dates.fiscal_year", total: { $sum: "$item.total_price" } } },
  { $sort: { _id: 1 } }
])

// 5. Top 5 departments by spending
db.purchase_orders.aggregate([
  { $group: { _id: "$department.normalized_name", total: { $sum: "$item.total_price" } } },
  { $sort: { total: -1 } },
  { $limit: 5 }
])

// 6. Top 5 suppliers
db.purchase_orders.aggregate([
  { $group: { _id: "$supplier.name", total: { $sum: "$item.total_price" } } },
  { $sort: { total: -1 } },
  { $limit: 5 }
])

// 7. Count by acquisition type
db.purchase_orders.aggregate([
  { $group: { _id: "$acquisition.type", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])

// 8. CalCard usage count
db.purchase_orders.countDocuments({ cal_card: true })

// 9. Orders over $100,000
db.purchase_orders.find({ "item.total_price": { $gt: 100000 } }).limit(5)

// 10. Average order value by department
db.purchase_orders.aggregate([
  { $group: { _id: "$department.normalized_name", avgOrder: { $avg: "$item.total_price" } } },
  { $sort: { avgOrder: -1 } },
  { $limit: 10 }
])
```

---

## Demo Script (Practice This!)

### Opening (2 min)
"This is a procurement analytics platform that lets users query California government purchase order data using natural language. It uses AI to convert questions into MongoDB queries."

### Part 1: Show the Data (3 min)
1. Open MongoDB Compass
2. Show the `purchase_orders` collection
3. Show one document, explain key fields:
   - "Each document is a purchase order line item"
   - "We have dates, department info, supplier info, item details, and classification codes"
   - "346,000 records covering 2012-2015"

### Part 2: Simple Query Demo (5 min)
1. Go to Web UI (localhost:5000)
2. Ask: "How many purchase orders are in the database?"
3. Show the answer
4. **KEY MOMENT**: Go to Compass and run:
   ```javascript
   db.purchase_orders.countDocuments()
   ```
5. Show it matches!

### Part 3: Complex Query Demo (5 min)
1. Ask: "What are the top 5 departments by spending?"
2. Show the answer
3. **KEY MOMENT**: Go to Compass and run:
   ```javascript
   db.purchase_orders.aggregate([
     { $group: { _id: "$department.normalized_name", total: { $sum: "$item.total_price" } } },
     { $sort: { total: -1 } },
     { $limit: 5 }
   ])
   ```
4. Explain each stage:
   - `$group` - groups by department, sums the spending
   - `$sort` - orders by total descending
   - `$limit` - takes top 5

### Part 4: Architecture Explanation (5 min)
"Let me explain how this works under the hood..."

1. **Frontend** (Flask + HTML/JS)
   - "User enters question in chat interface"
   - "JavaScript sends POST request to backend"

2. **Backend** (FastAPI)
   - "API receives the natural language question"
   - "Passes it to our AI Agent"

3. **AI Agent** (The magic)
   - "Sends question + schema info to OpenAI GPT"
   - "GPT generates a MongoDB aggregation pipeline"
   - "We validate and execute the pipeline"
   - "Results go back to GPT to generate human-readable answer"

4. **Why this is powerful**
   - "Non-technical users can query complex data"
   - "No SQL/MongoDB knowledge needed"
   - "Conversational - can ask follow-up questions"

### Part 5: Technical Decisions (3 min)
"A few architectural decisions I want to highlight..."

1. **MongoDB over SQL**: "Document model matches procurement data naturally - nested supplier, classification info"

2. **Aggregation Pipelines**: "More powerful than simple queries - can do grouping, sorting, facets, lookups"

3. **Two-step AI process**:
   - "First call: Generate pipeline"
   - "Second call: Summarize results"
   - "This separation gives us better control and accuracy"

4. **Retry Logic**: "If a generated pipeline fails, we send the error back to GPT to self-correct (up to 3 times)"

### Closing (2 min)
"Questions?"

---

## Potential CTO Questions & Answers

### Q: "Why MongoDB instead of PostgreSQL?"
**A:** "The procurement data has nested structures - supplier info, classification hierarchies, item details. Document model handles this naturally without complex joins. Also, the aggregation framework is powerful for analytics queries."

### Q: "How do you handle prompt injection?"
**A:** "The generated pipelines go through a validator that checks for dangerous operations. We also use a limited MongoDB user that can only read from the specific collection."

### Q: "What happens if the AI generates a wrong query?"
**A:** "We have a retry mechanism. If the query fails or returns unexpected results, we send the error back to GPT with context, and it attempts to self-correct. Max 3 attempts."

### Q: "How would you scale this?"
**A:** "Several options:
- MongoDB sharding for data scale
- Redis caching for repeated queries
- Queue system (Celery) for async processing
- Kubernetes for horizontal API scaling"

### Q: "What's the cost of running this?"
**A:** "Main cost is OpenAI API. Each query makes 2 API calls (pipeline generation + summarization). With GPT-4, roughly $0.01-0.05 per query depending on complexity."

### Q: "How accurate is it?"
**A:** "We have an evaluation suite with 20+ test cases covering basic to advanced queries. Current pass rate is around 85-90% depending on the model used."

### Q: "What would you improve?"
**A:** "Three things:
1. Query caching - same questions shouldn't hit the AI again
2. Better error messages for users when queries fail
3. Support for more complex visualizations in the frontend"

---

## Key Technical Terms to Know

| Term | What It Means |
|------|---------------|
| **Aggregation Pipeline** | MongoDB's way of processing data in stages ($match → $group → $sort) |
| **UNSPSC** | Universal product classification code system |
| **CalCard** | California's government procurement credit card |
| **FastAPI** | Modern Python web framework (async, type hints, auto-docs) |
| **Flask** | Simple Python web framework (used for frontend) |
| **LangGraph** | Framework for building AI agent workflows |
| **Fiscal Year** | California's fiscal year runs July 1 - June 30 |

---

## Files to Read (Priority Order)

1. `src/api/services/mongodb_agent/agent.py` - **MOST IMPORTANT**
2. `src/api/services/mongodb_agent/pipeline_generator.py` - How queries are made
3. `src/api/services/mongodb_agent/prompts.py` - The AI instructions
4. `src/api/routes/ai_query.py` - API endpoint
5. `src/web/routes/chat.py` - Frontend chat handler
6. `src/web/static/js/chat.js` - Browser JavaScript
7. `docker-compose.yml` - How services connect

---

## Confidence Builders

Remember:
- You BUILT this (with AI assistance, but you made decisions)
- The CTO wants you to succeed - he gave you a second chance
- Understanding comes from doing - run those queries!
- It's okay to say "Let me check that" during the demo
- Enthusiasm and clarity beat perfection

---

## Emergency Phrases If You Get Stuck

- "That's a great question, let me show you in the code..."
- "The way I approached this was..."
- "Let me verify that in MongoDB real quick..."
- "I'd need to look at the specific implementation, but the concept is..."

---

## Sunday Morning Checklist

- [ ] Slept well
- [ ] `make status` shows all healthy
- [ ] MongoDB Compass connected
- [ ] Browser open to localhost:5000
- [ ] This document open for reference
- [ ] Phone on silent
- [ ] Water bottle ready
- [ ] Deep breath - you've prepared for this!

---

Good luck! You've got this. 💪
