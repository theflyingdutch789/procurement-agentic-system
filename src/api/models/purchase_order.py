"""
Pydantic Models for Purchase Order API

These models provide request/response validation and OpenAPI documentation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# Request Models

class NaturalLanguageQueryRequest(BaseModel):
    """Request model for natural language queries."""
    query: str = Field(
        ...,
        description="Natural language query (e.g., 'Show me all IT purchases over $10,000 in 2014')",
        example="Show me all IT goods purchased by the Department of Corrections in 2014"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of results to return"
    )
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip (for pagination)"
    )


class AdvancedQueryRequest(BaseModel):
    """Request model for advanced MongoDB queries."""
    filter: Dict[str, Any] = Field(
        default_factory=dict,
        description="MongoDB query filter",
        example={"acquisition.type": "IT Goods", "item.total_price": {"$gt": 10000}}
    )
    projection: Optional[Dict[str, int]] = Field(
        default=None,
        description="Fields to include/exclude",
        example={"item.name": 1, "supplier.name": 1, "item.total_price": 1}
    )
    sort: Optional[Dict[str, int]] = Field(
        default=None,
        description="Sort specification (1 for ascending, -1 for descending)",
        example={"item.total_price": -1}
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of results"
    )
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip"
    )


class AggregationRequest(BaseModel):
    """Request model for MongoDB aggregation pipelines."""
    pipeline: List[Dict[str, Any]] = Field(
        ...,
        description="MongoDB aggregation pipeline stages",
        example=[
            {"$group": {"_id": "$supplier.name", "total_spend": {"$sum": "$item.total_price"}}},
            {"$sort": {"total_spend": -1}},
            {"$limit": 10}
        ]
    )


# Response Models

class LocationModel(BaseModel):
    """GeoJSON Point location."""
    type: str = "Point"
    coordinates: List[float] = Field(..., description="[longitude, latitude]")


class DateInfoModel(BaseModel):
    """Date information for a purchase order."""
    creation: Optional[datetime] = None
    purchase: Optional[datetime] = None
    fiscal_year: Optional[str] = None


class AcquisitionModel(BaseModel):
    """Acquisition details."""
    type: Optional[str] = None
    sub_type: Optional[str] = None
    method: Optional[str] = None
    sub_method: Optional[str] = None


class DepartmentModel(BaseModel):
    """Department information."""
    name: Optional[str] = None
    normalized_name: Optional[str] = None


class SupplierModel(BaseModel):
    """Supplier information."""
    code: Optional[str] = None
    name: Optional[str] = None
    qualifications: List[str] = []
    zip_code: Optional[str] = None
    location: Optional[LocationModel] = None


class ItemModel(BaseModel):
    """Item details."""
    name: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None


class ClassificationModel(BaseModel):
    """UNSPSC classification."""
    codes: List[str] = []
    unspsc: Optional[Dict[str, Any]] = None


class MetadataModel(BaseModel):
    """Document metadata."""
    import_date: Optional[datetime] = None
    source_file: Optional[str] = None
    data_quality: Optional[Dict[str, bool]] = None


class PurchaseOrderResponse(BaseModel):
    """Response model for a purchase order document."""
    id: str = Field(..., alias="_id", description="MongoDB document ID")
    purchase_order_number: Optional[str] = None
    requisition_number: Optional[str] = None
    lpa_number: Optional[str] = None
    dates: Optional[DateInfoModel] = None
    acquisition: Optional[AcquisitionModel] = None
    department: Optional[DepartmentModel] = None
    supplier: Optional[SupplierModel] = None
    item: Optional[ItemModel] = None
    cal_card: Optional[bool] = None
    classification: Optional[ClassificationModel] = None
    metadata: Optional[MetadataModel] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class QueryResponse(BaseModel):
    """Generic query response with pagination info."""
    success: bool = True
    count: int = Field(..., description="Number of documents returned")
    total: Optional[int] = Field(None, description="Total documents matching query")
    limit: int
    skip: int
    data: List[Dict[str, Any]]
    execution_time_ms: float = Field(..., description="Query execution time in milliseconds")


class StatsResponse(BaseModel):
    """Database statistics response."""
    success: bool = True
    database: str
    collection: str
    total_documents: int
    total_size_mb: float
    average_document_size_bytes: float
    indexes: List[Dict[str, Any]]
    fiscal_years: List[str]
    acquisition_types: List[str]
    top_departments: List[Dict[str, Any]]
    top_suppliers: List[Dict[str, Any]]
    price_statistics: Dict[str, float]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status: 'healthy' or 'unhealthy'")
    timestamp: datetime
    database_connected: bool
    database_name: str
    collection_name: str
    document_count: Optional[int] = None
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
