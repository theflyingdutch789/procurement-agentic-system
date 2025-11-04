"""Conversation model for managing chat history."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId


class Conversation:
    """Conversation model for managing user chat history."""

    def __init__(self, db):
        """Initialize Conversation model with database connection.

        Args:
            db: MongoDB database instance
        """
        self.collection = db.conversations
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create necessary indexes for conversations collection."""
        self.collection.create_index([("user_id", 1), ("created_at", -1)])
        self.collection.create_index("user_id")

    def create_conversation(self, user_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Create a new conversation for a user.

        Args:
            user_id: User ObjectId as string
            title: Optional conversation title

        Returns:
            dict: Created conversation document
        """
        conversation_doc = {
            "user_id": user_id,
            "title": title or "New Conversation",
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_archived": False
        }

        result = self.collection.insert_one(conversation_doc)
        conversation_doc["_id"] = str(result.inserted_id)

        return conversation_doc

    def get_conversation(self, conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID (user must own the conversation).

        Args:
            conversation_id: Conversation ObjectId as string
            user_id: User ObjectId as string

        Returns:
            dict: Conversation document or None
        """
        try:
            conversation = self.collection.find_one({
                "_id": ObjectId(conversation_id),
                "user_id": user_id
            })
            if conversation:
                conversation["_id"] = str(conversation["_id"])
            return conversation
        except Exception:
            return None

    def get_user_conversations(self, user_id: str, include_archived: bool = False,
                              limit: int = 50) -> List[Dict[str, Any]]:
        """Get all conversations for a user.

        Args:
            user_id: User ObjectId as string
            include_archived: Whether to include archived conversations
            limit: Maximum number of conversations to return

        Returns:
            list: List of conversation documents
        """
        query = {"user_id": user_id}
        if not include_archived:
            query["is_archived"] = False

        conversations = list(self.collection.find(query)
                           .sort("updated_at", -1)
                           .limit(limit))

        for conv in conversations:
            conv["_id"] = str(conv["_id"])

        return conversations

    def add_message(self, conversation_id: str, user_id: str,
                   query: str, response: Dict[str, Any],
                   reasoning_effort: str = "medium") -> Optional[Dict[str, Any]]:
        """Add a message to a conversation.

        Args:
            conversation_id: Conversation ObjectId as string
            user_id: User ObjectId as string
            query: User's query
            response: AI agent's response
            reasoning_effort: Reasoning effort used

        Returns:
            dict: Updated conversation document or None
        """
        message = {
            "id": str(ObjectId()),
            "query": query,
            "response": response,
            "reasoning_effort": reasoning_effort,
            "timestamp": datetime.utcnow()
        }

        try:
            # Update conversation title if it's the first message
            conversation = self.collection.find_one({
                "_id": ObjectId(conversation_id),
                "user_id": user_id
            })

            if not conversation:
                return None

            update_data = {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.utcnow()}
            }

            # Update title if it's "New Conversation"
            if conversation.get("title") == "New Conversation" and conversation.get("messages", []) == []:
                # Generate title from first query (truncate if too long)
                title = query[:50] + "..." if len(query) > 50 else query
                update_data["$set"]["title"] = title

            result = self.collection.find_one_and_update(
                {
                    "_id": ObjectId(conversation_id),
                    "user_id": user_id
                },
                update_data,
                return_document=True
            )

            if result:
                result["_id"] = str(result["_id"])
            return result
        except Exception:
            return None

    def update_conversation_title(self, conversation_id: str, user_id: str,
                                 title: str) -> Optional[Dict[str, Any]]:
        """Update conversation title.

        Args:
            conversation_id: Conversation ObjectId as string
            user_id: User ObjectId as string
            title: New title

        Returns:
            dict: Updated conversation document or None
        """
        try:
            result = self.collection.find_one_and_update(
                {
                    "_id": ObjectId(conversation_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "title": title,
                        "updated_at": datetime.utcnow()
                    }
                },
                return_document=True
            )
            if result:
                result["_id"] = str(result["_id"])
            return result
        except Exception:
            return None

    def archive_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Archive a conversation.

        Args:
            conversation_id: Conversation ObjectId as string
            user_id: User ObjectId as string

        Returns:
            bool: True if archived successfully
        """
        try:
            result = self.collection.update_one(
                {
                    "_id": ObjectId(conversation_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "is_archived": True,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception:
            return False

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation permanently.

        Args:
            conversation_id: Conversation ObjectId as string
            user_id: User ObjectId as string

        Returns:
            bool: True if deleted successfully
        """
        try:
            result = self.collection.delete_one({
                "_id": ObjectId(conversation_id),
                "user_id": user_id
            })
            return result.deleted_count > 0
        except Exception:
            return False

    def clear_conversation_messages(self, conversation_id: str, user_id: str) -> bool:
        """Clear all messages in a conversation and reset title.

        Args:
            conversation_id: Conversation ObjectId as string
            user_id: User ObjectId as string

        Returns:
            bool: True if cleared successfully
        """
        try:
            result = self.collection.update_one(
                {
                    "_id": ObjectId(conversation_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "messages": [],
                        "title": "New Conversation",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception:
            return False

    def get_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about user's conversations.

        Args:
            user_id: User ObjectId as string

        Returns:
            dict: Statistics including total conversations, total messages, etc.
        """
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": None,
                "total_conversations": {"$sum": 1},
                "total_messages": {"$sum": {"$size": "$messages"}},
                "active_conversations": {
                    "$sum": {"$cond": [{"$eq": ["$is_archived", False]}, 1, 0]}
                }
            }}
        ]

        result = list(self.collection.aggregate(pipeline))
        if result:
            stats = result[0]
            stats.pop("_id", None)
            return stats

        return {
            "total_conversations": 0,
            "total_messages": 0,
            "active_conversations": 0
        }
