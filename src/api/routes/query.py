"""
Query Endpoints

Provides natural language and advanced query capabilities for purchase orders.
"""

import time
from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from src.api.models.purchase_order import (
    NaturalLanguageQueryRequest,
    AdvancedQueryRequest,
    AggregationRequest,
    QueryResponse,
    StatsResponse,
    ErrorResponse
)
from src.api.dependencies import get_database, get_collection_name
from src.api.utils import parse_natural_language_query

router = APIRouter(prefix="/api", tags=["Queries"])


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to JSON-serializable format."""
    if isinstance(doc, dict):
        return {k: serialize_doc(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    elif isinstance(doc, (ObjectId, bytes)):
        return str(doc)
    elif isinstance(doc, datetime):
        return doc.isoformat()
    else:
        return doc


@router.post(
    "/query/natural",
    response_model=QueryResponse,
    summary="Natural Language Query",
    description="Query purchase orders using natural language (optimized for LLM integration)"
)
async def natural_language_query(
    request: NaturalLanguageQueryRequest,
    db: Database = Depends(get_database),
    collection_name: str = Depends(get_collection_name)
):
    """
    Execute a natural language query against the purchase orders collection.

    This endpoint is designed to work with LLM text-to-query systems.

    Examples:
    - "Show me all IT goods over $50,000"
    - "Find purchases by the Department of Transportation in 2014"
    - "Top 10 suppliers by total spend"
    """
    start_time = time.time()

    try:
        collection = db[collection_name]

        # Parse natural language to MongoDB query
        mongo_query = parse_natural_language_query(request.query)

        # Execute query
        cursor = collection.find(
            mongo_query.get("filter", {}),
            mongo_query.get("projection")
        )

        # Apply sorting if specified
        if mongo_query.get("sort"):
            cursor = cursor.sort(list(mongo_query["sort"].items()))

        # Get total count
        total = collection.count_documents(mongo_query.get("filter", {}))

        # Apply pagination
        cursor = cursor.skip(request.skip).limit(request.limit)

        # Execute and convert to list
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)

        execution_time = (time.time() - start_time) * 1000

        return QueryResponse(
            success=True,
            count=len(results),
            total=total,
            limit=request.limit,
            skip=request.skip,
            data=results,
            execution_time_ms=execution_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@router.post(
    "/query/advanced",
    response_model=QueryResponse,
    summary="Advanced MongoDB Query",
    description="Execute direct MongoDB queries with full control over filter, projection, and sort"
)
async def advanced_query(
    request: AdvancedQueryRequest,
    db: Database = Depends(get_database),
    collection_name: str = Depends(get_collection_name)
):
    """
    Execute an advanced MongoDB query.

    Allows full MongoDB query syntax including:
    - Complex filters with operators ($gt, $gte, $in, $regex, etc.)
    - Field projections
    - Custom sorting
    - Pagination
    """
    start_time = time.time()

    try:
        collection = db[collection_name]

        # Execute query
        cursor = collection.find(request.filter, request.projection)

        # Apply sorting
        if request.sort:
            cursor = cursor.sort(list(request.sort.items()))

        # Get total count
        total = collection.count_documents(request.filter)

        # Apply pagination
        cursor = cursor.skip(request.skip).limit(request.limit)

        # Execute and convert to list
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)

        execution_time = (time.time() - start_time) * 1000

        return QueryResponse(
            success=True,
            count=len(results),
            total=total,
            limit=request.limit,
            skip=request.skip,
            data=results,
            execution_time_ms=execution_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@router.post(
    "/query/aggregate",
    summary="MongoDB Aggregation",
    description="Execute MongoDB aggregation pipelines for complex analytics"
)
async def aggregation_query(
    request: AggregationRequest,
    db: Database = Depends(get_database),
    collection_name: str = Depends(get_collection_name)
):
    """
    Execute a MongoDB aggregation pipeline.

    Enables complex analytics such as:
    - Grouping and aggregation
    - Statistical calculations
    - Data transformation
    - Multi-stage processing
    """
    start_time = time.time()

    try:
        collection = db[collection_name]

        # Execute aggregation
        results = list(collection.aggregate(request.pipeline))

        # Serialize all documents (handles datetime, ObjectId, etc.)
        serialized_results = [serialize_doc(doc) for doc in results]

        execution_time = (time.time() - start_time) * 1000

        return {
            "success": True,
            "count": len(serialized_results),
            "data": serialized_results,
            "execution_time_ms": execution_time
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Aggregation failed: {str(e)}")


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Database Statistics",
    description="Get comprehensive statistics about the purchase orders database"
)
async def get_stats(
    db: Database = Depends(get_database),
    collection_name: str = Depends(get_collection_name)
):
    """
    Get database and collection statistics.

    Includes:
    - Document counts
    - Storage size
    - Index information
    - Data distribution (fiscal years, departments, suppliers)
    - Price statistics
    """
    try:
        collection = db[collection_name]

        # Basic stats
        total_docs = collection.count_documents({})
        stats = db.command("collstats", collection_name)

        # Get indexes
        indexes = [
            {"name": idx["name"], "keys": idx["key"]}
            for idx in collection.list_indexes()
        ]

        # Get fiscal years
        fiscal_years = collection.distinct("dates.fiscal_year")
        fiscal_years = [fy for fy in fiscal_years if fy]

        # Get acquisition types
        acquisition_types = collection.distinct("acquisition.type")
        acquisition_types = [at for at in acquisition_types if at]

        # Top 10 departments by purchase count
        top_departments = list(collection.aggregate([
            {"$group": {
                "_id": "$department.name",
                "purchase_count": {"$sum": 1},
                "total_spend": {"$sum": "$item.total_price"}
            }},
            {"$sort": {"purchase_count": -1}},
            {"$limit": 10}
        ]))

        # Top 10 suppliers by total spend
        top_suppliers = list(collection.aggregate([
            {"$group": {
                "_id": "$supplier.name",
                "total_spend": {"$sum": "$item.total_price"},
                "purchase_count": {"$sum": 1}
            }},
            {"$sort": {"total_spend": -1}},
            {"$limit": 10}
        ]))

        # Price statistics
        price_stats = list(collection.aggregate([
            {"$group": {
                "_id": None,
                "min_price": {"$min": "$item.total_price"},
                "max_price": {"$max": "$item.total_price"},
                "avg_price": {"$avg": "$item.total_price"},
                "total_spend": {"$sum": "$item.total_price"}
            }}
        ]))

        price_statistics = price_stats[0] if price_stats else {}
        price_statistics.pop("_id", None)

        return StatsResponse(
            success=True,
            database=db.name,
            collection=collection_name,
            total_documents=total_docs,
            total_size_mb=stats.get("size", 0) / (1024 ** 2),
            average_document_size_bytes=stats.get("avgObjSize", 0),
            indexes=indexes,
            fiscal_years=sorted(fiscal_years),
            acquisition_types=sorted(acquisition_types),
            top_departments=top_departments,
            top_suppliers=top_suppliers,
            price_statistics=price_statistics
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get(
    "/search",
    summary="Text Search",
    description="Full-text search across item names, descriptions, suppliers, and departments"
)
async def text_search(
    q: str = Query(..., description="Search query string"),
    limit: int = Query(100, ge=1, le=10000),
    skip: int = Query(0, ge=0),
    db: Database = Depends(get_database),
    collection_name: str = Depends(get_collection_name)
):
    """
    Perform full-text search using MongoDB text indexes.

    Searches across:
    - Item names (weighted 10x)
    - Item descriptions (weighted 5x)
    - Supplier names (weighted 3x)
    - Department names (weighted 2x)
    """
    start_time = time.time()

    try:
        collection = db[collection_name]

        # Execute text search
        cursor = collection.find(
            {"$text": {"$search": q}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})])

        # Get total count
        total = collection.count_documents({"$text": {"$search": q}})

        # Apply pagination
        cursor = cursor.skip(skip).limit(limit)

        # Execute and convert to list
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)

        execution_time = (time.time() - start_time) * 1000

        return QueryResponse(
            success=True,
            count=len(results),
            total=total,
            limit=limit,
            skip=skip,
            data=results,
            execution_time_ms=execution_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text search failed: {str(e)}")
