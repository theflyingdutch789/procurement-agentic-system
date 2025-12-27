"""
MongoDB Schema Definition for Government Procurement Purchase Orders

This module defines the document structure optimized for LLM text-to-query inference.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime


class PurchaseOrderSchema:
    """
    Defines the MongoDB document schema for purchase orders.

    This schema is optimized for:
    - Natural language queries via LLM
    - Aggregation and analytics
    - Geospatial queries
    - Text search
    """

    @staticmethod
    def create_document(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a MongoDB document from a CSV row.

        Args:
            row: Dictionary containing processed CSV data

        Returns:
            MongoDB document matching the optimized schema
        """
        return {
            # Primary identifiers
            "purchase_order_number": row.get("purchase_order_number"),
            "requisition_number": row.get("requisition_number"),
            "lpa_number": row.get("lpa_number"),

            # Dates - stored as Date objects for range queries
            "dates": {
                "creation": row.get("creation_date"),
                "purchase": row.get("purchase_date"),
                "fiscal_year": row.get("fiscal_year"),  # String format: "2013-2014"
                "fiscal_year_start": row.get("fiscal_year_start")  # Integer: 2013 (for easy querying)
            },

            # Acquisition details - optimized for filtering
            "acquisition": {
                "type": row.get("acquisition_type"),
                "sub_type": row.get("sub_acquisition_type"),
                "method": row.get("acquisition_method"),
                "sub_method": row.get("sub_acquisition_method")
            },

            # Department information
            "department": {
                "name": row.get("department_name"),
                "normalized_name": row.get("department_normalized")
            },

            # Supplier information - embedded document
            "supplier": {
                "code": row.get("supplier_code"),
                "name": row.get("supplier_name"),
                "qualifications": row.get("supplier_qualifications", []),
                "zip_code": row.get("supplier_zip_code"),
                "location": row.get("supplier_location")  # GeoJSON format
            },

            # Item details
            "item": {
                "name": row.get("item_name"),
                "description": row.get("item_description"),
                "quantity": row.get("quantity"),
                "unit_price": row.get("unit_price"),
                "total_price": row.get("total_price")
            },

            # Payment method
            "cal_card": row.get("cal_card"),

            # UNSPSC classification - hierarchical structure
            "classification": {
                "codes": row.get("classification_codes", []),
                "unspsc": {
                    "code": row.get("normalized_unspsc"),
                    "commodity": {
                        "code": row.get("commodity_code"),
                        "title": row.get("commodity_title")
                    },
                    "class": {
                        "code": row.get("class_code"),
                        "title": row.get("class_title")
                    },
                    "family": {
                        "code": row.get("family_code"),
                        "title": row.get("family_title")
                    },
                    "segment": {
                        "code": row.get("segment_code"),
                        "title": row.get("segment_title")
                    }
                }
            },

            # Metadata
            "metadata": {
                "import_date": datetime.utcnow(),
                "source_file": row.get("source_file", "purchase_orders_2012_2015.csv"),
                "data_quality": {
                    "has_location": row.get("supplier_location") is not None,
                    "has_purchase_date": row.get("purchase_date") is not None,
                    "has_unspsc": row.get("normalized_unspsc") is not None and row.get("normalized_unspsc") != ""
                }
            }
        }

    @staticmethod
    def get_collection_name() -> str:
        """Returns the MongoDB collection name."""
        return "purchase_orders"

    @staticmethod
    def get_database_name() -> str:
        """Returns the MongoDB database name."""
        return "government_procurement"

    @staticmethod
    def get_schema_description() -> Dict[str, Any]:
        """
        Returns a human-readable schema description for documentation.
        """
        return {
            "database": "government_procurement",
            "collection": "purchase_orders",
            "description": "California state government purchase order data (2012-2015)",
            "document_structure": {
                "purchase_order_number": "Unique PO identifier (String, indexed, unique)",
                "requisition_number": "Requisition ID (String, indexed)",
                "lpa_number": "License Purchase Agreement number (String, indexed, sparse)",
                "dates": {
                    "creation": "PO creation date (Date, indexed)",
                    "purchase": "Actual purchase date (Date, indexed, sparse)",
                    "fiscal_year": "Fiscal year YYYY-YYYY (String, indexed, e.g. '2013-2014')",
                    "fiscal_year_start": "Fiscal year starting year (Number, indexed, e.g. 2013)"
                },
                "acquisition": {
                    "type": "IT/NON-IT Goods/Services (String, indexed)",
                    "sub_type": "Subcategory (String, indexed, sparse)",
                    "method": "Competitive/Contract/etc (String, indexed)",
                    "sub_method": "Additional method details (String, sparse)"
                },
                "department": {
                    "name": "Full department name (String, indexed, text search)",
                    "normalized_name": "Cleaned department name (String, indexed)"
                },
                "supplier": {
                    "code": "Supplier ID (String, indexed)",
                    "name": "Vendor name (String, indexed, text search)",
                    "qualifications": "Certifications array (Array[String], indexed)",
                    "zip_code": "Location zip (String, indexed)",
                    "location": "GeoJSON Point (2dsphere indexed)"
                },
                "item": {
                    "name": "Short description (String, text search)",
                    "description": "Detailed description (String, text search)",
                    "quantity": "Number of units (Number)",
                    "unit_price": "Price per unit (Number)",
                    "total_price": "Total cost (Number, indexed)"
                },
                "cal_card": "CalCard usage flag (Boolean, indexed)",
                "classification": {
                    "codes": "Classification codes array (Array[String])",
                    "unspsc": "UNSPSC hierarchy (Object, indexed on titles)"
                },
                "metadata": {
                    "import_date": "Import timestamp (Date)",
                    "source_file": "CSV filename (String)",
                    "data_quality": "Quality flags (Object)"
                }
            },
            "indexes": [
                "Compound: fiscal_year + department",
                "Compound: acquisition_type + creation_date",
                "Compound: supplier_name + total_price",
                "Text: item name/description, supplier, department",
                "Geospatial: supplier location (2dsphere)",
                "Single field: PO number, supplier code, total price, etc."
            ],
            "optimization_notes": [
                "Embedded documents for related data (supplier, classification)",
                "Proper Date types for temporal queries",
                "GeoJSON for geospatial queries",
                "Text indexes weighted by importance",
                "Sparse indexes for optional fields"
            ]
        }
