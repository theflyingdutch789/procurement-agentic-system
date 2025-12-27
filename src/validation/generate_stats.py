#!/usr/bin/env python3
"""
Statistics Generation Script

Generates comprehensive statistics about the imported data.
"""

import os
import sys
import json
from datetime import datetime
from pymongo import MongoClient
from typing import Dict, Any


class StatsGenerator:
    """Generates statistics from MongoDB collection."""

    def __init__(self, mongo_uri: str, database: str, collection: str):
        """
        Initialize stats generator.

        Args:
            mongo_uri: MongoDB connection URI
            database: Database name
            collection: Collection name
        """
        self.client = MongoClient(mongo_uri)
        self.db = self.client[database]
        self.collection = self.db[collection]

    def get_basic_stats(self) -> Dict[str, Any]:
        """Get basic collection statistics."""
        print("Gathering basic statistics...")

        total_docs = self.collection.count_documents({})
        stats_cmd = self.db.command("collstats", self.collection.name)

        return {
            "total_documents": total_docs,
            "total_size_bytes": stats_cmd.get("size", 0),
            "total_size_mb": stats_cmd.get("size", 0) / (1024 ** 2),
            "average_document_size_bytes": stats_cmd.get("avgObjSize", 0),
            "storage_size_mb": stats_cmd.get("storageSize", 0) / (1024 ** 2),
            "total_indexes": stats_cmd.get("nindexes", 0),
            "total_index_size_mb": stats_cmd.get("totalIndexSize", 0) / (1024 ** 2)
        }

    def get_temporal_stats(self) -> Dict[str, Any]:
        """Get temporal distribution statistics."""
        print("Analyzing temporal distribution...")

        # Fiscal year distribution
        fiscal_years = list(self.collection.aggregate([
            {"$group": {
                "_id": "$dates.fiscal_year",
                "count": {"$sum": 1},
                "total_spend": {"$sum": "$item.total_price"}
            }},
            {"$sort": {"_id": 1}}
        ]))

        # Monthly creation date distribution
        monthly = list(self.collection.aggregate([
            {"$match": {"dates.creation": {"$ne": None}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$dates.creation"},
                    "month": {"$month": "$dates.creation"}
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}},
            {"$limit": 50}
        ]))

        return {
            "fiscal_years": fiscal_years,
            "monthly_distribution_sample": monthly[:12]
        }

    def get_acquisition_stats(self) -> Dict[str, Any]:
        """Get acquisition type statistics."""
        print("Analyzing acquisition types...")

        # Acquisition type distribution
        types = list(self.collection.aggregate([
            {"$group": {
                "_id": "$acquisition.type",
                "count": {"$sum": 1},
                "total_spend": {"$sum": "$item.total_price"},
                "avg_price": {"$avg": "$item.total_price"}
            }},
            {"$sort": {"total_spend": -1}}
        ]))

        # Acquisition method distribution
        methods = list(self.collection.aggregate([
            {"$group": {
                "_id": "$acquisition.method",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]))

        return {
            "by_type": types,
            "top_methods": methods
        }

    def get_department_stats(self) -> Dict[str, Any]:
        """Get department statistics."""
        print("Analyzing departments...")

        # Top departments by count
        top_by_count = list(self.collection.aggregate([
            {"$group": {
                "_id": "$department.name",
                "purchase_count": {"$sum": 1},
                "total_spend": {"$sum": "$item.total_price"}
            }},
            {"$sort": {"purchase_count": -1}},
            {"$limit": 15}
        ]))

        # Top departments by spend
        top_by_spend = list(self.collection.aggregate([
            {"$group": {
                "_id": "$department.name",
                "purchase_count": {"$sum": 1},
                "total_spend": {"$sum": "$item.total_price"}
            }},
            {"$sort": {"total_spend": -1}},
            {"$limit": 15}
        ]))

        return {
            "top_by_purchase_count": top_by_count,
            "top_by_total_spend": top_by_spend
        }

    def get_supplier_stats(self) -> Dict[str, Any]:
        """Get supplier statistics."""
        print("Analyzing suppliers...")

        # Total unique suppliers
        unique_suppliers = len(self.collection.distinct("supplier.code"))

        # Top suppliers by spend
        top_suppliers = list(self.collection.aggregate([
            {"$group": {
                "_id": {
                    "code": "$supplier.code",
                    "name": "$supplier.name"
                },
                "purchase_count": {"$sum": 1},
                "total_spend": {"$sum": "$item.total_price"}
            }},
            {"$sort": {"total_spend": -1}},
            {"$limit": 20}
        ]))

        # Supplier qualification distribution
        quals = list(self.collection.aggregate([
            {"$unwind": "$supplier.qualifications"},
            {"$group": {
                "_id": "$supplier.qualifications",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]))

        return {
            "unique_suppliers": unique_suppliers,
            "top_by_spend": top_suppliers,
            "qualifications_distribution": quals
        }

    def get_price_stats(self) -> Dict[str, Any]:
        """Get price statistics."""
        print("Analyzing prices...")

        # Overall price statistics
        price_stats = list(self.collection.aggregate([
            {"$group": {
                "_id": None,
                "min_price": {"$min": "$item.total_price"},
                "max_price": {"$max": "$item.total_price"},
                "avg_price": {"$avg": "$item.total_price"},
                "total_spend": {"$sum": "$item.total_price"}
            }}
        ]))

        # Price ranges
        ranges = list(self.collection.aggregate([
            {
                "$bucket": {
                    "groupBy": "$item.total_price",
                    "boundaries": [0, 100, 1000, 10000, 100000, 1000000, float('inf')],
                    "default": "Unknown",
                    "output": {
                        "count": {"$sum": 1},
                        "total_spend": {"$sum": "$item.total_price"}
                    }
                }
            }
        ]))

        return {
            "overall": price_stats[0] if price_stats else {},
            "by_range": ranges
        }

    def get_location_stats(self) -> Dict[str, Any]:
        """Get location statistics."""
        print("Analyzing locations...")

        # Documents with location
        with_location = self.collection.count_documents({
            "supplier.location": {"$ne": None}
        })

        # Top zip codes
        top_zips = list(self.collection.aggregate([
            {"$group": {
                "_id": "$supplier.zip_code",
                "count": {"$sum": 1},
                "total_spend": {"$sum": "$item.total_price"}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 15}
        ]))

        return {
            "documents_with_location": with_location,
            "top_zip_codes": top_zips
        }

    def get_classification_stats(self) -> Dict[str, Any]:
        """Get UNSPSC classification statistics."""
        print("Analyzing classifications...")

        # Top segments
        segments = list(self.collection.aggregate([
            {"$group": {
                "_id": {
                    "code": "$classification.unspsc.segment.code",
                    "title": "$classification.unspsc.segment.title"
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]))

        # Top families
        families = list(self.collection.aggregate([
            {"$group": {
                "_id": {
                    "code": "$classification.unspsc.family.code",
                    "title": "$classification.unspsc.family.title"
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]))

        return {
            "top_segments": segments,
            "top_families": families
        }

    def generate_all_stats(self) -> Dict[str, Any]:
        """Generate all statistics."""
        print("=" * 80)
        print("GENERATING STATISTICS")
        print("=" * 80)
        print()

        stats = {
            "generated_at": datetime.utcnow().isoformat(),
            "database": self.db.name,
            "collection": self.collection.name,
            "basic": self.get_basic_stats(),
            "temporal": self.get_temporal_stats(),
            "acquisition": self.get_acquisition_stats(),
            "departments": self.get_department_stats(),
            "suppliers": self.get_supplier_stats(),
            "prices": self.get_price_stats(),
            "locations": self.get_location_stats(),
            "classifications": self.get_classification_stats()
        }

        print()
        print("=" * 80)
        print("STATISTICS SUMMARY")
        print("=" * 80)
        print(f"Total Documents:       {stats['basic']['total_documents']:,}")
        print(f"Total Size:            {stats['basic']['total_size_mb']:.2f} MB")
        print(f"Unique Suppliers:      {stats['suppliers']['unique_suppliers']:,}")
        print(f"Total Spend:           ${stats['prices']['overall'].get('total_spend', 0):,.2f}")
        print(f"Average Price:         ${stats['prices']['overall'].get('avg_price', 0):,.2f}")
        print(f"Documents w/ Location: {stats['locations']['documents_with_location']:,}")
        print("=" * 80)

        return stats

    def close(self):
        """Close MongoDB connection."""
        self.client.close()


def main():
    """Main entry point."""
    # Get configuration
    mongo_host = os.getenv("MONGO_HOST", "mongodb")
    mongo_port = os.getenv("MONGO_PORT", "27017")
    mongo_user = os.getenv("MONGO_USERNAME", "admin")
    mongo_pass = os.getenv("MONGO_PASSWORD", "changeme_secure_password")
    mongo_db = os.getenv("MONGO_DATABASE", "government_procurement")
    collection = os.getenv("COLLECTION_NAME", "purchase_orders")

    mongo_uri = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/"

    try:
        generator = StatsGenerator(mongo_uri, mongo_db, collection)
        stats = generator.generate_all_stats()

        # Save to file
        output_file = "/app/logs/import_stats.json"
        with open(output_file, "w") as f:
            json.dump(stats, f, indent=2, default=str)

        print(f"\n✅ Statistics saved to: {output_file}")

        generator.close()
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Statistics generation failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
