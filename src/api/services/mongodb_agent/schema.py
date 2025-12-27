"""
Schema context utilities for the procurement MongoDB collection.
"""


class MongoDBSchemaContext:
    """Provides schema context about the MongoDB collection."""

    SCHEMA_DESCRIPTION = """
    ## Database Schema: government_procurement.purchase_orders

    This collection contains California state government purchase orders from 2012-2015.
    Total documents: ~346,000 purchase order line items

    ### Main Fields:

    **Identifiers:**
    - purchase_order_number (string): Primary PO identifier
    - requisition_number (string): Requisition ID
    - lpa_number (string): Leveraged Procurement Agreement number
    - cal_card (boolean): California Procurement Card flag

    **Dates:**
    - dates.creation (ISODate): Order creation date
    - dates.purchase (ISODate): Purchase date (may be null)
    - dates.fiscal_year (string): Fiscal year in format "YYYY-YYYY" (e.g., "2013-2014")
    - dates.fiscal_year_start (number): Starting fiscal year as integer (e.g., 2013) - USE THIS FOR NUMERIC QUERIES

    **Department:**
    - department.name (string): Full department name
    - department.normalized_name (string): Standardized name for grouping

    **Acquisition:**
    - acquisition.type (string): "IT Goods", "IT Services", "NON-IT Goods", "NON-IT Services"
    - acquisition.sub_type (string): Additional subtype details when provided
    - acquisition.method (string): e.g. "Leveraged Procurement Agreement"
    - acquisition.sub_method (string): More specific contracting approach when provided

    **Item:**
    - item.description (string): Full-text item description
    - item.quantity (number): Quantity ordered
    - item.unit_price (number): Price per unit (USD)
    - item.total_price (number): Total line item price (can be negative for credits/returns)

    **Supplier:**
    - supplier.name (string): Supplier/vendor name
    - supplier.code (string): Unique supplier identifier
    - supplier.address (string): Full address
    - supplier.city (string)
    - supplier.state (string)
    - supplier.zip (string)
    - supplier.location (GeoJSON Point): { type: "Point", coordinates: [lon, lat] }
    - supplier.qualifications (array): e.g. ["DVBE", "Small Business"]

    **Classification (UNSPSC):**
    - classification.unspsc.segment.code (string): e.g. "43000000"
    - classification.unspsc.segment.title (string): e.g. "Information Technology"
    - classification.unspsc.family.code (string): e.g. "43210000"
    - classification.unspsc.family.title (string): e.g. "Software"
    - classification.unspsc.class.code (string)
    - classification.unspsc.class.title (string)
    - classification.unspsc.commodity.code (string)
    - classification.unspsc.commodity.title (string)

    **Metadata:**
    - metadata.source_file (string): Original CSV filename
    - metadata.import_date (ISODate): When imported

    ### Common Query Patterns:

    **Total Spending:**
    [{{"$group": {{"_id": null, "total": {{"$sum": {{"$ifNull": ["$item.total_price", 0]}}}}}}}}, {{"$limit": 1}}]

    **Spending by Department:**
    [{{"$group": {{"_id": "$department.normalized_name", "total": {{"$sum": {{"$ifNull": ["$item.total_price", 0]}}}}}}}}, {{"$sort": {{"total": -1}}}}, {{"$limit": 10}}]

    **Spending by Quarter:**
    [{{"$group": {{"_id": {{"year": {{"$year": "$dates.creation"}}, "quarter": {{"$ceil": {{"$divide": [{{"$month": "$dates.creation"}}, 3]}}}}}}, "total": {{"$sum": {{"$ifNull": ["$item.total_price", 0]}}}}}}}}, {{"$sort": {{"_id.year": 1, "_id.quarter": 1}}}}]

    **Top Suppliers:**
    [{{"$group": {{"_id": "$supplier.name", "total": {{"$sum": {{"$ifNull": ["$item.total_price", 0]}}}}, "count": {{"$sum": 1}}}}}}, {{"$sort": {{"total": -1}}}}, {{"$limit": 10}}]

    ### Important Notes:
    - item.total_price can be null for some records - ALWAYS use {{"$sum": {{"$ifNull": ["$item.total_price", 0]}}}} when summing prices
    - item.total_price can be negative (represents credits, returns, refunds)
    - Always use dates.creation for time-based queries (most reliable)
    - For fiscal year queries, use dates.fiscal_year (STRING like "2012-2013") for grouping/display
    - For fiscal year numeric comparisons, use dates.fiscal_year_start (INTEGER: 2012, 2013, 2014, 2015)
    - For geospatial queries, use $geoNear or $geoWithin on supplier.location
    - Text search: Use $text operator on indexed fields
    - Use $match to filter, $group to aggregate, $sort to order, $limit to restrict results

    ### CRITICAL DATA TYPE RULES:
    - dates.creation is ISODate type - use $year, $month, $dayOfMonth operators
    - dates.purchase is ISODate type - use $year, $month operators
    - dates.fiscal_year is STRING (e.g., "2012-2013") - use for grouping by fiscal year
    - dates.fiscal_year_start is INTEGER (e.g., 2012) - use for numeric comparisons
    - item.total_price is FLOAT/NUMBER - NEVER use as string
    - item.unit_price is FLOAT/NUMBER - NEVER use as string
    - item.quantity is FLOAT/NUMBER - NEVER use as string
    - When filtering by year, use: {{"dates.fiscal_year": "2012-2013"}} OR {{"dates.fiscal_year_start": 2012}}
    - When filtering by price, use: {{"item.total_price": {{"$gt": 1000}}}} (number not "1000")
    """

    @classmethod
    def get_schema(cls) -> str:
        """Return the full schema description."""
        return cls.SCHEMA_DESCRIPTION
