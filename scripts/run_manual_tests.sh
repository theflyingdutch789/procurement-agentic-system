#!/bin/bash

echo "=========================================="
echo "MANUAL TEST SUITE - Edge Cases & Performance"
echo "=========================================="
echo ""

# Test 1: Negative Prices
echo "TEST 1: Negative Prices (Credits/Returns)"
echo "Question: Show me purchase orders with negative prices"
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me purchase orders with negative prices", "model": "gpt-5", "max_results": 10}' \
  2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Success: {data['success']}\"); print(f\"Results: {data['result_count']}\"); print(f\"Pipeline: {json.dumps(data['pipeline'], indent=2)[:300]}\")"

echo ""
echo "=========================================="
sleep 2

# Test 2: Missing Data
echo "TEST 2: Missing/Null Department Data"
echo "Question: Find purchase orders with missing department information"
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Find purchase orders with missing department information", "model": "gpt-5", "max_results": 10}' \
  2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Success: {data['success']}\"); print(f\"Results: {data['result_count']}\"); print(f\"Answer: {data['answer'][:200] if data['answer'] else 'None'}\")"

echo ""
echo "=========================================="
sleep 2

# Test 3: Large Numbers
echo "TEST 3: Large Number Handling"
echo "Question: Find departments with over $1 billion in total spending"
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Find departments with over $1 billion in total spending", "model": "gpt-5", "max_results": 10}' \
  2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Success: {data['success']}\"); print(f\"Results: {data['result_count']}\"); print(f\"Time: {data['execution_time_seconds']:.2f}s\")"

echo ""
echo "=========================================="
sleep 2

# Test 4: Performance - Simple Count
echo "TEST 4: Performance - Simple Count"
echo "Question: How many line items are in the database?"
START_TIME=$(python3 -c "import time; print(time.time())")
curl -X POST http://localhost:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How many line items are in the database?", "reasoning_effort": "minimal", "model": "gpt-5"}' \
  2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Success: {data['success']}\"); print(f\"Answer: {data['answer'][:150] if data['answer'] else 'None'}\"); print(f\"Exec Time: {data['execution_time_seconds']:.2f}s\")"

echo ""
echo "=========================================="
echo "MANUAL TESTS COMPLETE"
echo "=========================================="
