#!/usr/bin/env python3
"""
Import Validation Script

Validates the MongoDB import by:
- Checking document counts
- Verifying data quality
- Testing sample queries
- Checking indexes
"""

import os
import sys
from datetime import datetime
from pymongo import MongoClient
from typing import Dict, Any, List


class ImportValidator:
    """Validates MongoDB import quality and completeness."""

    def __init__(self, mongo_uri: str, database: str, collection: str):
        """
        Initialize validator.

        Args:
            mongo_uri: MongoDB connection URI
            database: Database name
            collection: Collection name
        """
        self.client = MongoClient(mongo_uri)
        self.db = self.client[database]
        self.collection = self.db[collection]
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "database": database,
            "collection": collection,
            "checks": {},
            "warnings": [],
            "errors": [],
            "passed": False
        }

    def check_document_count(self, expected_min: int = 900000) -> bool:
        """Check if document count meets expectations."""
        print("Checking document count...")
        count = self.collection.count_documents({})

        self.results["checks"]["document_count"] = {
            "actual": count,
            "expected_min": expected_min,
            "passed": count >= expected_min
        }

        if count < expected_min:
            self.results["errors"].append(
                f"Document count ({count:,}) is less than expected minimum ({expected_min:,})"
            )
            print(f"  ❌ FAILED: {count:,} documents (expected >= {expected_min:,})")
            return False
        else:
            print(f"  ✅ PASSED: {count:,} documents")
            return True

    def check_indexes(self, expected_min: int = 15) -> bool:
        """Check if indexes are created."""
        print("Checking indexes...")
        indexes = list(self.collection.list_indexes())
        index_count = len(indexes)

        self.results["checks"]["indexes"] = {
            "count": index_count,
            "expected_min": expected_min,
            "names": [idx["name"] for idx in indexes],
            "passed": index_count >= expected_min
        }

        if index_count < expected_min:
            self.results["warnings"].append(
                f"Index count ({index_count}) is less than expected ({expected_min})"
            )
            print(f"  ⚠️  WARNING: Only {index_count} indexes (expected >= {expected_min})")
            return False
        else:
            print(f"  ✅ PASSED: {index_count} indexes created")
            for idx in indexes[:5]:
                print(f"     - {idx['name']}")
            if index_count > 5:
                print(f"     ... and {index_count - 5} more")
            return True

    def check_data_quality(self) -> bool:
        """Check data quality metrics."""
        print("Checking data quality...")

        # Check for required fields
        total = self.collection.count_documents({})

        # Documents with purchase_order_number
        with_po = self.collection.count_documents({"purchase_order_number": {"$exists": True, "$ne": None}})
        po_percent = (with_po / total * 100) if total > 0 else 0

        # Documents with creation date
        with_date = self.collection.count_documents({"dates.creation": {"$exists": True, "$ne": None}})
        date_percent = (with_date / total * 100) if total > 0 else 0

        # Documents with total price
        with_price = self.collection.count_documents({"item.total_price": {"$exists": True, "$ne": None}})
        price_percent = (with_price / total * 100) if total > 0 else 0

        # Documents with location
        with_location = self.collection.count_documents({"supplier.location": {"$exists": True, "$ne": None}})
        location_percent = (with_location / total * 100) if total > 0 else 0

        self.results["checks"]["data_quality"] = {
            "total_documents": total,
            "with_po_number": {"count": with_po, "percent": po_percent},
            "with_creation_date": {"count": with_date, "percent": date_percent},
            "with_total_price": {"count": with_price, "percent": price_percent},
            "with_location": {"count": with_location, "percent": location_percent},
            "passed": po_percent > 90 and date_percent > 90 and price_percent > 90
        }

        print(f"  Purchase Order Numbers: {with_po:,} ({po_percent:.1f}%)")
        print(f"  Creation Dates:         {with_date:,} ({date_percent:.1f}%)")
        print(f"  Total Prices:           {with_price:,} ({price_percent:.1f}%)")
        print(f"  Locations:              {with_location:,} ({location_percent:.1f}%)")

        if po_percent < 90 or date_percent < 90 or price_percent < 90:
            self.results["errors"].append("Data quality check failed: critical fields below 90% threshold")
            print("  ❌ FAILED: Critical fields below 90%")
            return False
        else:
            print("  ✅ PASSED: Data quality acceptable")
            return True

    def check_sample_queries(self) -> bool:
        """Test sample queries to ensure indexes and data work correctly."""
        print("Testing sample queries...")

        queries = [
            {
                "name": "Filter by acquisition type",
                "query": {"acquisition.type": "IT Goods"},
                "expected_min": 1000
            },
            {
                "name": "Filter by fiscal year",
                "query": {"dates.fiscal_year": "2013-2014"},
                "expected_min": 1000
            },
            {
                "name": "Price range query",
                "query": {"item.total_price": {"$gt": 10000, "$lt": 100000}},
                "expected_min": 1000
            },
            {
                "name": "Department regex",
                "query": {"department.name": {"$regex": "Transportation", "$options": "i"}},
                "expected_min": 100
            }
        ]

        all_passed = True
        query_results = []

        for q in queries:
            try:
                count = self.collection.count_documents(q["query"])
                passed = count >= q["expected_min"]

                query_results.append({
                    "name": q["name"],
                    "count": count,
                    "expected_min": q["expected_min"],
                    "passed": passed
                })

                if passed:
                    print(f"  ✅ {q['name']}: {count:,} results")
                else:
                    print(f"  ❌ {q['name']}: {count:,} results (expected >= {q['expected_min']:,})")
                    all_passed = False

            except Exception as e:
                print(f"  ❌ {q['name']}: FAILED - {e}")
                query_results.append({
                    "name": q["name"],
                    "error": str(e),
                    "passed": False
                })
                all_passed = False

        self.results["checks"]["sample_queries"] = {
            "results": query_results,
            "passed": all_passed
        }

        return all_passed

    def check_text_search(self) -> bool:
        """Test text search functionality."""
        print("Testing text search...")

        try:
            # Test text search
            results = list(self.collection.find(
                {"$text": {"$search": "computer"}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(10))

            passed = len(results) > 0

            self.results["checks"]["text_search"] = {
                "test_query": "computer",
                "result_count": len(results),
                "passed": passed
            }

            if passed:
                print(f"  ✅ PASSED: Text search returned {len(results)} results")
                return True
            else:
                self.results["warnings"].append("Text search returned no results")
                print("  ⚠️  WARNING: Text search returned no results")
                return False

        except Exception as e:
            self.results["errors"].append(f"Text search failed: {str(e)}")
            print(f"  ❌ FAILED: {e}")
            return False

    def run_all_checks(self) -> bool:
        """Run all validation checks."""
        print("=" * 80)
        print("RUNNING IMPORT VALIDATION")
        print("=" * 80)
        print()

        checks = [
            self.check_document_count(),
            self.check_indexes(),
            self.check_data_quality(),
            self.check_sample_queries(),
            self.check_text_search()
        ]

        print()
        print("=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)

        all_passed = all(checks)
        self.results["passed"] = all_passed

        if all_passed:
            print("✅ ALL CHECKS PASSED")
        else:
            print("❌ SOME CHECKS FAILED")

        if self.results["errors"]:
            print(f"\nErrors ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"  - {error}")

        if self.results["warnings"]:
            print(f"\nWarnings ({len(self.results['warnings'])}):")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")

        print("=" * 80)
        return all_passed

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
        validator = ImportValidator(mongo_uri, mongo_db, collection)
        passed = validator.run_all_checks()
        validator.close()

        sys.exit(0 if passed else 1)

    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
