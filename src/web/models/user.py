"""User model for authentication and user management."""
import bcrypt
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId


class User:
    """User model with password hashing and validation."""

    def __init__(self, db):
        """Initialize User model with database connection.

        Args:
            db: MongoDB database instance
        """
        self.collection = db.users
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create necessary indexes for users collection."""
        self.collection.create_index("username", unique=True)
        self.collection.create_index("email", unique=True)

    def create_user(self, username: str, email: str, password: str,
                   full_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new user with hashed password.

        Args:
            username: Unique username
            email: User email address
            password: Plain text password (will be hashed)
            full_name: Optional full name

        Returns:
            dict: Created user document (without password)

        Raises:
            ValueError: If username or email already exists
        """
        # Check if username exists
        if self.collection.find_one({"username": username}):
            raise ValueError("Username already exists")

        # Check if email exists
        if self.collection.find_one({"email": email}):
            raise ValueError("Email already exists")

        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Create user document
        user_doc = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "full_name": full_name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True
        }

        # Insert user
        result = self.collection.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id

        # Return user without password
        return self._sanitize_user(user_doc)

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password.

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            dict: User document (without password) if authenticated, None otherwise
        """
        # Find user by username or email
        user = self.collection.find_one({
            "$or": [
                {"username": username},
                {"email": username}
            ]
        })

        if not user:
            return None

        # Check if account is active
        if not user.get("is_active", True):
            return None

        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user["password_hash"]):
            # Update last login
            self.collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            return self._sanitize_user(user)

        return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID.

        Args:
            user_id: User ObjectId as string

        Returns:
            dict: User document (without password) or None
        """
        try:
            user = self.collection.find_one({"_id": ObjectId(user_id)})
            return self._sanitize_user(user) if user else None
        except Exception:
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username.

        Args:
            username: Username

        Returns:
            dict: User document (without password) or None
        """
        user = self.collection.find_one({"username": username})
        return self._sanitize_user(user) if user else None

    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user information.

        Args:
            user_id: User ObjectId as string
            update_data: Dictionary of fields to update

        Returns:
            dict: Updated user document or None
        """
        # Remove protected fields
        protected_fields = ["_id", "username", "password_hash", "created_at"]
        for field in protected_fields:
            update_data.pop(field, None)

        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()

        try:
            result = self.collection.find_one_and_update(
                {"_id": ObjectId(user_id)},
                {"$set": update_data},
                return_document=True
            )
            return self._sanitize_user(result) if result else None
        except Exception:
            return None

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password.

        Args:
            user_id: User ObjectId as string
            old_password: Current password
            new_password: New password

        Returns:
            bool: True if password changed successfully
        """
        try:
            user = self.collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return False

            # Verify old password
            if not bcrypt.checkpw(old_password.encode('utf-8'), user["password_hash"]):
                return False

            # Hash new password
            new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

            # Update password
            self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "password_hash": new_hash,
                    "updated_at": datetime.utcnow()
                }}
            )
            return True
        except Exception:
            return False

    def delete_user(self, user_id: str) -> bool:
        """Soft delete user by marking as inactive.

        Args:
            user_id: User ObjectId as string

        Returns:
            bool: True if user deactivated successfully
        """
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "is_active": False,
                    "updated_at": datetime.utcnow()
                }}
            )
            return result.modified_count > 0
        except Exception:
            return False

    def _sanitize_user(self, user: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Remove sensitive fields from user document.

        Args:
            user: User document

        Returns:
            dict: Sanitized user document
        """
        if not user:
            return None

        # Convert ObjectId to string
        if "_id" in user:
            user["_id"] = str(user["_id"])

        # Remove password hash
        user.pop("password_hash", None)

        return user
