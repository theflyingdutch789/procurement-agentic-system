.PHONY: help build rebuild start stop restart up down logs status clean seed eval benchmark eval-quick install-eval-deps

# Default target
help:
	@echo "Procurement Agentic System - Makefile Commands"
	@echo "==============================================="
	@echo ""
	@echo "Docker Commands:"
	@echo "  make build       - Build Docker containers"
	@echo "  make rebuild     - Force rebuild Docker containers (no cache)"
	@echo "  make start       - Start all services"
	@echo "  make stop        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make down        - Stop and remove containers"
	@echo "  make logs        - View logs (all services)"
	@echo "  make logs-api    - View API logs"
	@echo "  make logs-web    - View Web logs"
	@echo "  make status      - Show container status"
	@echo "  make clean       - Stop containers and remove volumes"
	@echo ""
	@echo "Data Commands:"
	@echo "  make seed        - Import data from CSV into MongoDB"
	@echo ""
	@echo "Evaluation Commands:"
	@echo "  make install-eval-deps  - Install evaluation dependencies"
	@echo "  make eval               - Run full evaluation suite"
	@echo "  make eval-quick         - Run quick evaluation (single profile)"
	@echo "  make benchmark          - Run GPT-5 model benchmark comparison"
	@echo ""
	@echo "Combined Commands:"
	@echo "  make all         - Build, start, and seed data"
	@echo "  make dev         - Rebuild and start with logs"
	@echo ""

# =============================================================================
# Docker Commands
# =============================================================================

build:
	@echo "Building Docker containers..."
	docker-compose build

rebuild:
	@echo "Rebuilding Docker containers (no cache)..."
	docker-compose build --no-cache

start up:
	@echo "Starting services..."
	docker-compose up -d
	@echo ""
	@echo "Services started:"
	@echo "  Web UI:  http://localhost:5000"
	@echo "  API:     http://localhost:8000"
	@echo "  MongoDB: localhost:27017"

stop:
	@echo "Stopping services..."
	docker-compose stop

down:
	@echo "Stopping and removing containers..."
	docker-compose down

restart:
	@echo "Restarting services..."
	docker-compose down
	docker-compose up -d
	@echo ""
	@echo "Services restarted:"
	@echo "  Web UI:  http://localhost:5000"
	@echo "  API:     http://localhost:8000"

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-web:
	docker-compose logs -f web

logs-mongo:
	docker-compose logs -f mongodb

status:
	@echo "Container Status:"
	@echo "================="
	docker-compose ps

clean:
	@echo "Stopping containers and removing volumes..."
	docker-compose down -v
	@echo "Cleaning up logs..."
	rm -rf logs/*.log 2>/dev/null || true
	@echo "Done."

# =============================================================================
# Data Commands
# =============================================================================

seed:
	@echo "Importing data from CSV..."
	docker-compose --profile seed up importer
	@echo "Data import complete."

# =============================================================================
# Evaluation Commands
# =============================================================================

install-eval-deps:
	@echo "Installing evaluation dependencies..."
	pip install -r evaluation/requirements.txt

eval:
	@echo "Running full evaluation suite..."
	@echo "================================"
	@mkdir -p reports/evaluations
	python evaluation/eval_system.py \
		--mongo-uri "mongodb://admin:changeme_secure_password@localhost:27017" \
		--database government_procurement \
		--collection purchase_orders \
		--api-url http://localhost:8000 \
		--output-dir ./reports/evaluations

eval-quick:
	@echo "Running quick evaluation (GPT-4o, medium reasoning)..."
	@mkdir -p reports/evaluations
	python evaluation/eval_system.py \
		--mongo-uri "mongodb://admin:changeme_secure_password@localhost:27017" \
		--database government_procurement \
		--collection purchase_orders \
		--api-url http://localhost:8000 \
		--model gpt-4o \
		--reasoning-effort medium \
		--max-results 10 \
		--output-dir ./reports/evaluations

benchmark:
	@echo "Running GPT-5 Model Benchmark..."
	@echo "================================"
	@mkdir -p benchmark_results
	@mkdir -p reports/evaluations
	python evaluation/benchmark_gpt5.py --output-dir ./benchmark_results

# =============================================================================
# Combined Commands
# =============================================================================

all: build start seed
	@echo ""
	@echo "Setup complete!"
	@echo "  Web UI:  http://localhost:5000"
	@echo "  API:     http://localhost:8000"

dev: rebuild
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	docker-compose logs -f

# =============================================================================
# Health Checks
# =============================================================================

health:
	@echo "Checking service health..."
	@echo ""
	@echo "API Health:"
	@curl -s http://localhost:8000/api/health | python -m json.tool 2>/dev/null || echo "  API not responding"
	@echo ""
	@echo "Web Health:"
	@curl -s http://localhost:5000/health | python -m json.tool 2>/dev/null || echo "  Web not responding"

# =============================================================================
# Environment Setup
# =============================================================================

env:
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example..."; \
		cp .env.example .env; \
		echo "Done. Please edit .env and add your OPENAI_API_KEY"; \
	else \
		echo ".env file already exists"; \
	fi
