"""
Health Check Endpoint

Provides service health status and database connectivity checks.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from pymongo.database import Database

from src.api.models.purchase_order import HealthResponse
from src.api.dependencies import get_database, get_collection_name

router = APIRouter(tags=["Health"])


@router.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check if the API service and database are running properly"
)
async def health_check(
    db: Database = Depends(get_database),
    collection_name: str = Depends(get_collection_name)
):
    """
    Health check endpoint.

    Returns:
        Service health status including database connectivity
    """
    try:
        # Ping database
        db.command("ping")
        database_connected = True

        # Get document count
        collection = db[collection_name]
        document_count = collection.count_documents({})

        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            database_connected=database_connected,
            database_name=db.name,
            collection_name=collection_name,
            document_count=document_count
        )

    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            database_connected=False,
            database_name=db.name,
            collection_name=collection_name,
            document_count=None
        )
