#!/bin/bash
#
# Run AI Query System Evaluation
#
# Usage:
#   ./run_eval.sh
#
# The script will automatically load OPENAI_API_KEY from .env file

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=================================================="
echo "  AI Query System Evaluation Runner"
echo "=================================================="
echo ""

# Check if .env file exists
if [ ! -f "$REPO_ROOT/.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create a .env file with OPENAI_API_KEY"
    exit 1
fi

echo -e "${BLUE}✓ Found .env file${NC}"
echo "  OpenAI API key will be loaded from .env"

# Check if services are running
echo ""
echo "Checking services..."

if ! docker-compose ps mongodb | grep -q "Up"; then
    echo -e "${RED}✗ MongoDB is not running${NC}"
    echo "  Start it with: docker-compose up -d mongodb"
    exit 1
fi
echo "✓ MongoDB is running"

if ! docker-compose ps web | grep -q "Up"; then
    echo -e "${RED}✗ Web service is not running${NC}"
    echo "  Start it with: docker-compose up -d web"
    exit 1
fi
echo "✓ Web service is running"

# Check if Python dependencies are installed
echo ""
echo "Checking Python dependencies..."
if ! python3 -c "import pymongo, requests, openai" 2>/dev/null; then
    echo -e "${YELLOW}⚠ Installing required dependencies...${NC}"
    pip install -q -r "$REPO_ROOT/evaluation/requirements.txt"
fi
echo "✓ Dependencies installed"

# Create output directory
OUTPUT_DIR="$REPO_ROOT/reports/evaluations"
mkdir -p "$OUTPUT_DIR"
API_URL="${EVAL_API_URL:-http://localhost:8000}"
MAX_RESULTS="${EVAL_MAX_RESULTS:-10}"
REASONING="${EVAL_REASONING_EFFORT:-medium}"
REQUEST_TIMEOUT="${EVAL_REQUEST_TIMEOUT:-180}"

# Run evaluation
echo ""
echo "=================================================="
echo "  Starting Evaluation"
echo "=================================================="
echo ""

python3 "$REPO_ROOT/evaluation/eval_system.py" \
    --mongo-uri "mongodb://admin:changeme_secure_password@localhost:27017" \
    --database "government_procurement" \
    --collection "purchase_orders" \
    --api-url "$API_URL" \
    --output-dir "$OUTPUT_DIR" \
    --max-results "$MAX_RESULTS" \
    --reasoning-effort "$REASONING" \
    --request-timeout "$REQUEST_TIMEOUT"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=================================================="
    echo "  Evaluation PASSED"
    echo "==================================================${NC}"
else
    echo -e "${RED}=================================================="
    echo "  Evaluation FAILED"
    echo "==================================================${NC}"
fi

echo ""
echo "Results saved to: $OUTPUT_DIR"
echo ""

exit $EXIT_CODE
