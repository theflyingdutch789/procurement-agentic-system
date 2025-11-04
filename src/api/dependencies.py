"""
FastAPI Dependencies

Provides dependency injection for database connections and configuration.
"""

import os
from typing import Generator
from pymongo import MongoClient
from pymongo.database import Database

# Global MongoDB client (initialized on startup)
_mongo_client: MongoClient = None


def get_mongo_client() -> MongoClient:
    """Get or create MongoDB client."""
    global _mongo_client

    if _mongo_client is None:
        mongo_host = os.getenv("MONGO_HOST", "mongodb")
        mongo_port = os.getenv("MONGO_PORT", "27017")
        mongo_user = os.getenv("MONGO_USERNAME", "admin")
        mongo_pass = os.getenv("MONGO_PASSWORD", "changeme_secure_password")

        mongo_uri = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/"
        _mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

    return _mongo_client


def get_database() -> Database:
    """
    Dependency to get MongoDB database.

    Returns:
        Database instance
    """
    client = get_mongo_client()
    db_name = os.getenv("MONGO_DATABASE", "government_procurement")
    return client[db_name]


def get_collection_name() -> str:
    """
    Dependency to get collection name from environment.

    Returns:
        Collection name string
    """
    return os.getenv("COLLECTION_NAME", "purchase_orders")


def close_mongo_connection():
    """Close MongoDB connection on shutdown."""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
