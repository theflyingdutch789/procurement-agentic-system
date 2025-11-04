#!/usr/bin/env python3
"""
CSV to MongoDB Import Script for Government Procurement Data

This script imports purchase order data from CSV into MongoDB with:
- Batch processing for performance
- Progress tracking
- Error handling and logging
- Data transformation and validation
"""

import os
import sys
import logging
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import pandas as pd
from pymongo import MongoClient, errors
from tqdm import tqdm

# Import local modules
from src.importer.transformers import DataTransformer, DataValidator
from src.importer.schema import PurchaseOrderSchema


# Configure logging
def setup_logging(log_level: str = "INFO"):
    """Configure logging with file and console handlers."""
    log_dir = Path("/app/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


class CSVImporter:
    """Handles CSV import to MongoDB with batch processing."""

    def __init__(
        self,
        mongo_uri: str,
        database: str,
        collection: str,
        batch_size: int = 5000
    ):
        """
        Initialize the importer.

        Args:
            mongo_uri: MongoDB connection URI
            database: Database name
            collection: Collection name
            batch_size: Number of documents per batch
        """
        self.mongo_uri = mongo_uri
        self.database_name = database
        self.collection_name = collection
        self.batch_size = batch_size
        self.logger = logging.getLogger(__name__)

        # Connect to MongoDB
        self.logger.info(f"Connecting to MongoDB at {mongo_uri.split('@')[-1]}...")
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
        self.db = self.client[database]
        self.collection = self.db[collection]

        # Verify connection
        try:
            self.client.admin.command('ping')
            self.logger.info("Successfully connected to MongoDB")
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            raise

        # Stats
        self.stats = {
            "total_rows": 0,
            "processed": 0,
            "inserted": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None,
            "errors": []
        }

    def read_csv(self, csv_path: str, chunk_size: int = 10000) -> pd.DataFrame:
        """
        Read CSV file with chunking for large files.

        Args:
            csv_path: Path to CSV file
            chunk_size: Number of rows per chunk

        Returns:
            Complete DataFrame
        """
        self.logger.info(f"Reading CSV file: {csv_path}")

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        # Get file size for progress
        file_size = os.path.getsize(csv_path)
        self.logger.info(f"File size: {file_size / (1024**2):.2f} MB")

        # Read CSV in chunks and concatenate
        chunks = []
        for chunk in tqdm(
            pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False),
            desc="Reading CSV",
            unit="chunk"
        ):
            chunks.append(chunk)

        df = pd.concat(chunks, ignore_index=True)
        self.logger.info(f"Loaded {len(df):,} rows from CSV")

        return df

    def transform_batch(
        self,
        rows: List[Dict[str, Any]],
        source_file: str
    ) -> List[Dict[str, Any]]:
        """
        Transform a batch of CSV rows to MongoDB documents.

        Args:
            rows: List of dictionaries from CSV
            source_file: Source filename

        Returns:
            List of MongoDB documents
        """
        documents = []
        source_filename = os.path.basename(source_file)

        for row in rows:
            try:
                # Transform the row
                transformed = DataTransformer.transform_row(row, source_filename)

                # Create MongoDB document
                document = PurchaseOrderSchema.create_document(transformed)

                # Validate document
                is_valid, validation_errors = DataValidator.validate_document(document)

                if is_valid:
                    documents.append(document)
                else:
                    self.stats["skipped"] += 1
                    if len(self.stats["errors"]) < 100:  # Limit error storage
                        self.stats["errors"].append({
                            "row": row.get("Purchase Order Number", "Unknown"),
                            "errors": validation_errors
                        })

            except Exception as e:
                self.stats["failed"] += 1
                self.logger.warning(f"Failed to transform row: {e}")
                if len(self.stats["errors"]) < 100:
                    self.stats["errors"].append({
                        "row": row.get("Purchase Order Number", "Unknown"),
                        "error": str(e)
                    })

        return documents

    def insert_batch(self, documents: List[Dict[str, Any]]) -> int:
        """
        Insert a batch of documents into MongoDB.

        Args:
            documents: List of MongoDB documents

        Returns:
            Number of documents inserted
        """
        if not documents:
            return 0

        try:
            result = self.collection.insert_many(documents, ordered=False)
            return len(result.inserted_ids)
        except errors.BulkWriteError as bwe:
            # Some documents were inserted, some failed
            inserted = bwe.details.get('nInserted', 0)
            write_errors = bwe.details.get('writeErrors', [])
            self.logger.warning(
                f"Bulk write error: {inserted} inserted, "
                f"{len(write_errors)} failed"
            )
            # Log first 3 errors for debugging
            for error in write_errors[:3]:
                self.logger.error(f"Sample error: {error}")
            return inserted
        except Exception as e:
            self.logger.error(f"Failed to insert batch: {e}")
            return 0

    def import_csv(self, csv_path: str):
        """
        Main import function.

        Args:
            csv_path: Path to CSV file
        """
        self.logger.info("=" * 80)
        self.logger.info("STARTING CSV IMPORT")
        self.logger.info("=" * 80)

        self.stats["start_time"] = datetime.now()

        # Read CSV
        df = self.read_csv(csv_path)
        self.stats["total_rows"] = len(df)

        # Convert to list of dictionaries
        rows = df.to_dict('records')

        # Process in batches
        total_batches = (len(rows) + self.batch_size - 1) // self.batch_size
        self.logger.info(f"Processing {len(rows):,} rows in {total_batches} batches")

        with tqdm(total=len(rows), desc="Importing", unit="docs") as pbar:
            for i in range(0, len(rows), self.batch_size):
                batch = rows[i:i + self.batch_size]

                # Transform batch
                documents = self.transform_batch(batch, csv_path)

                # Insert batch
                inserted = self.insert_batch(documents)

                # Update stats
                self.stats["processed"] += len(batch)
                self.stats["inserted"] += inserted

                # Update progress bar
                pbar.update(len(batch))

        self.stats["end_time"] = datetime.now()
        self.print_stats()

    def print_stats(self):
        """Print import statistics."""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        self.logger.info("=" * 80)
        self.logger.info("IMPORT COMPLETE")
        self.logger.info("=" * 80)
        self.logger.info(f"Total rows in CSV:    {self.stats['total_rows']:,}")
        self.logger.info(f"Rows processed:       {self.stats['processed']:,}")
        self.logger.info(f"Documents inserted:   {self.stats['inserted']:,}")
        self.logger.info(f"Documents skipped:    {self.stats['skipped']:,}")
        self.logger.info(f"Documents failed:     {self.stats['failed']:,}")
        self.logger.info(f"Duration:             {duration:.2f} seconds")
        self.logger.info(f"Rate:                 {self.stats['inserted']/duration:.0f} docs/sec")
        self.logger.info("=" * 80)

        if self.stats["errors"]:
            self.logger.warning(f"First 10 errors:")
            for i, error in enumerate(self.stats["errors"][:10], 1):
                self.logger.warning(f"  {i}. {error}")

    def close(self):
        """Close MongoDB connection."""
        self.client.close()
        self.logger.info("MongoDB connection closed")


def main():
    """Main entry point."""
    # Get configuration from environment
    mongo_host = os.getenv("MONGO_HOST", "mongodb")
    mongo_port = os.getenv("MONGO_PORT", "27017")
    mongo_user = os.getenv("MONGO_USERNAME", "admin")
    mongo_pass = os.getenv("MONGO_PASSWORD", "changeme_secure_password")
    mongo_db = os.getenv("MONGO_DATABASE", "government_procurement")
    collection = os.getenv("COLLECTION_NAME", "purchase_orders")
    csv_file = os.getenv("CSV_FILE_PATH", "/data/purchase_orders_2012_2015.csv")
    batch_size = int(os.getenv("BATCH_SIZE", "5000"))
    log_level = os.getenv("LOG_LEVEL", "INFO")

    # Setup logging
    logger = setup_logging(log_level)

    # Build MongoDB URI
    mongo_uri = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/"

    logger.info("Configuration:")
    logger.info(f"  MongoDB: {mongo_host}:{mongo_port}")
    logger.info(f"  Database: {mongo_db}")
    logger.info(f"  Collection: {collection}")
    logger.info(f"  CSV File: {csv_file}")
    logger.info(f"  Batch Size: {batch_size:,}")

    try:
        # Create importer
        importer = CSVImporter(
            mongo_uri=mongo_uri,
            database=mongo_db,
            collection=collection,
            batch_size=batch_size
        )

        # Import CSV
        importer.import_csv(csv_file)

        # Verify import
        doc_count = importer.collection.count_documents({})
        logger.info(f"\nVerification: Collection contains {doc_count:,} documents")

        # Close connection
        importer.close()

        logger.info("\n✅ Import completed successfully!")
        sys.exit(0)

    except Exception as e:
        logger.error(f"\n❌ Import failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
