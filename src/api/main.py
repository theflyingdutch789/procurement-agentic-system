"""
FastAPI Application for Government Procurement Data API

Provides RESTful endpoints for querying California state government
purchase order data (2012-2015) optimized for LLM text-to-query inference.
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.api.routes import health, query, ai_query
from src.api.dependencies import close_mongo_connection, get_mongo_client
from src.api.models.purchase_order import ErrorResponse


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting up FastAPI application...")
    try:
        # Test MongoDB connection
        client = get_mongo_client()
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application...")
    close_mongo_connection()
    logger.info("MongoDB connection closed")


# Create FastAPI application
app = FastAPI(
    title="Government Procurement Data API",
    description="""
    RESTful API for querying California state government purchase order data (2012-2015).

    ## Features

    - **Natural Language Queries**: Query using natural language (optimized for LLM integration)
    - **Advanced MongoDB Queries**: Full MongoDB query syntax support
    - **Aggregation Pipelines**: Complex analytics and data aggregation
    - **Text Search**: Full-text search across items, suppliers, and departments
    - **Statistics**: Comprehensive database and data statistics

    ## Data Overview

    - **Source**: California state government purchase orders (2012-2015)
    - **Records**: ~346,000 purchase orders
    - **Coverage**: IT/Non-IT goods and services across all state departments
    - **Classifications**: UNSPSC standard product/service codes
    - **Geospatial**: Supplier location data with coordinates

    ## Optimizations

    - Indexed fields for fast queries
    - Text search with weighted relevance
    - Geospatial queries for location-based analysis
    - Embedded documents for related data
    """,
    version="1.0.0",
    contact={
        "name": "Procurement Data Team",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(health.router)
app.include_router(query.router)
app.include_router(ai_query.router)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            success=False,
            error="Validation Error",
            detail=str(exc),
            timestamp=datetime.utcnow()
        ).model_dump(mode='json')
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            error="Internal Server Error",
            detail=str(exc),
            timestamp=datetime.utcnow()
        ).model_dump(mode='json')
    )


# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="API Root",
    description="Get API information and available endpoints"
)
async def root():
    """
    Root endpoint providing API information.
    """
    return {
        "name": "Government Procurement Data API",
        "version": "1.0.0",
        "description": "API for querying California state government purchase orders (2012-2015)",
        "documentation": "/docs",
        "health_check": "/api/health",
        "endpoints": {
            "natural_language_query": "POST /api/query/natural",
            "advanced_query": "POST /api/query/advanced",
            "aggregation": "POST /api/query/aggregate",
            "text_search": "GET /api/search",
            "statistics": "GET /api/stats"
        },
        "features": [
            "Natural language queries (LLM-optimized)",
            "Advanced MongoDB query syntax",
            "Aggregation pipelines",
            "Full-text search",
            "Geospatial queries",
            "Comprehensive statistics"
        ],
        "data_summary": {
            "source": "California State Government",
            "time_period": "2012-2015",
            "record_count": "~346,000 purchase orders",
            "categories": ["IT Goods", "IT Services", "NON-IT Goods", "NON-IT Services"]
        }
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=os.getenv("API_RELOAD", "false").lower() == "true"
    )
