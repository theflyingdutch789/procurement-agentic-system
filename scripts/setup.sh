#!/bin/bash

# Government Procurement Data - One-Command Setup Script
# This script sets up the entire environment and imports the data

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Government Procurement Data Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is installed${NC}"

# Check if CSV file exists
CSV_FILE="data/purchase_orders_2012_2015.csv"
if [ ! -f "$CSV_FILE" ]; then
    echo -e "${RED}❌ CSV file not found: $CSV_FILE${NC}"
    echo "Please make sure the CSV file is located at $PROJECT_ROOT/$CSV_FILE"
    exit 1
fi

echo -e "${GREEN}✅ CSV file found${NC}"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please review .env and update passwords before production use!${NC}"
else
    echo -e "${GREEN}✅ .env file exists${NC}"
fi

# Create logs directory
mkdir -p logs
echo -e "${GREEN}✅ Logs directory created${NC}"

echo ""
echo "=========================================="
echo "Starting Services"
echo "=========================================="
echo ""

# Start MongoDB first
echo "Starting MongoDB..."
docker-compose up -d mongodb

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to be ready..."
sleep 10

# Check MongoDB health
until docker-compose exec -T mongodb mongosh --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1; do
    echo "Waiting for MongoDB..."
    sleep 5
done

echo -e "${GREEN}✅ MongoDB is ready${NC}"

echo ""
echo "=========================================="
echo "Running Data Import"
echo "=========================================="
echo ""

# Build and run importer
echo "Building importer container..."
docker-compose build importer

echo "Starting data import (this may take 5-15 minutes)..."
docker-compose --profile seed up importer

# Check if import was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Data import completed successfully${NC}"
else
    echo -e "${RED}❌ Data import failed${NC}"
    echo "Check logs in ./logs directory for details"
    exit 1
fi

echo ""
echo "=========================================="
echo "Starting API Service"
echo "=========================================="
echo ""

# Build and start API
echo "Building API container..."
docker-compose build api

echo "Starting API service..."
docker-compose up -d api

# Wait for API to be ready
echo "Waiting for API to be ready..."
sleep 5

# Check API health
API_URL="http://localhost:8000/api/health"
for i in {1..12}; do
    if curl -s "$API_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API is ready${NC}"
        break
    fi
    if [ $i -eq 12 ]; then
        echo -e "${RED}❌ API failed to start${NC}"
        exit 1
    fi
    echo "Waiting for API... ($i/12)"
    sleep 5
done

echo ""
echo "=========================================="
echo "Running Validation"
echo "=========================================="
echo ""

# Run validation (optional)
read -p "Run import validation? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running validation..."
    docker-compose --profile seed run --rm -e MONGO_HOST=mongodb importer python src/validation/validate_import.py
fi

echo ""
echo "=========================================="
echo "Setup Complete! 🎉"
echo "=========================================="
echo ""
echo "Services are now running:"
echo ""
echo "  📊 MongoDB:       localhost:27017"
echo "  🚀 API:           http://localhost:8000"
echo "  📖 API Docs:      http://localhost:8000/docs"
echo "  ❤️  Health Check:  http://localhost:8000/api/health"
echo ""
echo "Quick test:"
echo "  curl http://localhost:8000/api/stats"
echo ""
echo "View logs:"
echo "  docker-compose logs -f api"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo ""
echo "Full cleanup (including data):"
echo "  docker-compose down -v"
echo ""
echo "=========================================="
