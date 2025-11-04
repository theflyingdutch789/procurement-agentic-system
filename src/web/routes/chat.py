"""Chat routes for conversation management and AI queries."""
import sys
import os

from flask import Blueprint, request, jsonify, session

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models.conversation import Conversation
from middleware.auth import login_required
import requests

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')
DEFAULT_MAX_RESULTS = int(os.getenv("CHAT_MAX_RESULTS", "10"))


def init_chat_routes(db):
    """Initialize chat routes with database connection.

    Args:
        db: MongoDB database instance

    Returns:
        Blueprint: Configured chat blueprint
    """
    conversation_model = Conversation(db)

    # Get API service URL from environment or use default
    API_SERVICE_URL = os.getenv('API_SERVICE_URL', 'http://api:8000')

    @chat_bp.route('/conversations', methods=['GET'])
    @login_required
    def get_conversations():
        """Get all conversations for the current user.

        Query parameters:
            include_archived: bool (default: false)
            limit: int (default: 50)

        Returns:
            JSON response with list of conversations
        """
        try:
            user_id = session.get('user_id')
            include_archived = request.args.get('include_archived', 'false').lower() == 'true'
            limit = int(request.args.get('limit', 50))

            conversations = conversation_model.get_user_conversations(
                user_id=user_id,
                include_archived=include_archived,
                limit=limit
            )

            return jsonify({
                "success": True,
                "conversations": conversations,
                "count": len(conversations)
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Failed to get conversations"
            }), 500

    @chat_bp.route('/conversations', methods=['POST'])
    @login_required
    def create_conversation():
        """Create a new conversation.

        Expected JSON body:
        {
            "title": "string" (optional)
        }

        Returns:
            JSON response with created conversation
        """
        try:
            user_id = session.get('user_id')
            print(f"[CREATE_CONVERSATION] user_id from session: {user_id}")
            print(f"[CREATE_CONVERSATION] session contents: {dict(session)}")

            data = request.get_json() or {}

            conversation = conversation_model.create_conversation(
                user_id=user_id,
                title=data.get('title')
            )

            print(f"[CREATE_CONVERSATION] Created conversation: {conversation.get('_id')}")

            return jsonify({
                "success": True,
                "conversation": conversation
            }), 201

        except Exception as e:
            import traceback
            print(f"[CREATE_CONVERSATION] ERROR: {str(e)}")
            print(f"[CREATE_CONVERSATION] Traceback: {traceback.format_exc()}")
            return jsonify({
                "success": False,
                "error": "Failed to create conversation",
                "details": str(e)
            }), 500

    @chat_bp.route('/conversations/<conversation_id>', methods=['GET'])
    @login_required
    def get_conversation(conversation_id):
        """Get a specific conversation with all messages.

        Args:
            conversation_id: Conversation ID

        Returns:
            JSON response with conversation data
        """
        try:
            user_id = session.get('user_id')
            conversation = conversation_model.get_conversation(
                conversation_id=conversation_id,
                user_id=user_id
            )

            if not conversation:
                return jsonify({
                    "success": False,
                    "error": "Conversation not found"
                }), 404

            return jsonify({
                "success": True,
                "conversation": conversation
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Failed to get conversation"
            }), 500

    @chat_bp.route('/conversations/<conversation_id>', methods=['PUT'])
    @login_required
    def update_conversation(conversation_id):
        """Update conversation title.

        Expected JSON body:
        {
            "title": "string"
        }

        Returns:
            JSON response with updated conversation
        """
        try:
            user_id = session.get('user_id')
            data = request.get_json()

            if not data or not data.get('title'):
                return jsonify({
                    "success": False,
                    "error": "Title is required"
                }), 400

            conversation = conversation_model.update_conversation_title(
                conversation_id=conversation_id,
                user_id=user_id,
                title=data['title']
            )

            if not conversation:
                return jsonify({
                    "success": False,
                    "error": "Conversation not found"
                }), 404

            return jsonify({
                "success": True,
                "conversation": conversation
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Failed to update conversation"
            }), 500

    @chat_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
    @login_required
    def delete_conversation(conversation_id):
        """Delete a conversation permanently.

        Args:
            conversation_id: Conversation ID

        Returns:
            JSON response confirming deletion
        """
        try:
            user_id = session.get('user_id')
            success = conversation_model.delete_conversation(
                conversation_id=conversation_id,
                user_id=user_id
            )

            if not success:
                return jsonify({
                    "success": False,
                    "error": "Conversation not found or already deleted"
                }), 404

            return jsonify({
                "success": True,
                "message": "Conversation deleted successfully"
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Failed to delete conversation"
            }), 500

    @chat_bp.route('/conversations/<conversation_id>/archive', methods=['POST'])
    @login_required
    def archive_conversation(conversation_id):
        """Archive a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            JSON response confirming archival
        """
        try:
            user_id = session.get('user_id')
            success = conversation_model.archive_conversation(
                conversation_id=conversation_id,
                user_id=user_id
            )

            if not success:
                return jsonify({
                    "success": False,
                    "error": "Conversation not found"
                }), 404

            return jsonify({
                "success": True,
                "message": "Conversation archived successfully"
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Failed to archive conversation"
            }), 500

    @chat_bp.route('/conversations/<conversation_id>/clear', methods=['POST'])
    @login_required
    def clear_conversation(conversation_id):
        """Clear all messages in a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            JSON response confirming messages cleared
        """
        try:
            user_id = session.get('user_id')
            success = conversation_model.clear_conversation_messages(
                conversation_id=conversation_id,
                user_id=user_id
            )

            if not success:
                return jsonify({
                    "success": False,
                    "error": "Conversation not found"
                }), 404

            return jsonify({
                "success": True,
                "message": "Conversation cleared successfully"
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Failed to clear conversation"
            }), 500

    @chat_bp.route('/query', methods=['POST'])
    @login_required
    def send_query():
        """Send a query to the AI agent and save to conversation.

        Expected JSON body:
        {
            "conversation_id": "string",
            "question": "string",
            "reasoning_effort": "minimal|low|medium|high" (optional, default: medium)
        }

        Returns:
            JSON response with AI agent's response
        """
        try:
            user_id = session.get('user_id')
            data = request.get_json()

            if not data or not data.get('question'):
                return jsonify({
                    "success": False,
                    "error": "Question is required"
                }), 400

            conversation_id = data.get('conversation_id')
            question = data['question']
            reasoning_effort = data.get('reasoning_effort', 'medium')

            # Create new conversation if not provided
            if not conversation_id:
                conversation = conversation_model.create_conversation(user_id=user_id)
                conversation_id = conversation['_id']

            # Verify conversation belongs to user
            existing_conversation = conversation_model.get_conversation(
                conversation_id=conversation_id,
                user_id=user_id
            )

            if not existing_conversation:
                return jsonify({
                    "success": False,
                    "error": "Conversation not found"
                }), 404

            # Build conversation history from existing messages for context
            conversation_history = []
            if existing_conversation and 'messages' in existing_conversation:
                for msg in existing_conversation['messages']:
                    conversation_history.append({
                        'question': msg.get('query', ''),
                        'response': msg.get('response', {})
                    })

            # Determine model and reasoning based on selection
            # Fast option (minimal) uses gpt-5-mini with medium reasoning
            model = data.get("model", "gpt-5")
            if reasoning_effort == "minimal" and model == "gpt-5":
                model = "gpt-5-mini"
                effective_reasoning = "medium"
            else:
                effective_reasoning = reasoning_effort

            # Call GPT-5 AI agent API
            try:
                api_response = requests.post(
                    f"{API_SERVICE_URL}/api/ai/query",
                    json={
                        "question": question,
                        "conversation_id": conversation_id,  # Pass conversation ID for context
                        "conversation_history": conversation_history,  # Pass conversation history for follow-up context
                        "reasoning_effort": effective_reasoning,
                        "model": model,
                        "max_results": DEFAULT_MAX_RESULTS
                    },
                    timeout=60
                )

                if api_response.status_code != 200:
                    return jsonify({
                        "success": False,
                        "error": "AI agent request failed",
                        "details": api_response.text
                    }), 500

                ai_response = api_response.json()

            except requests.exceptions.RequestException as e:
                return jsonify({
                    "success": False,
                    "error": "Failed to connect to AI agent",
                    "details": str(e)
                }), 500

            # Save message to conversation
            updated_conversation = conversation_model.add_message(
                conversation_id=conversation_id,
                user_id=user_id,
                query=question,
                response=ai_response,
                reasoning_effort=reasoning_effort
            )

            if not updated_conversation:
                return jsonify({
                    "success": False,
                    "error": "Failed to save message to conversation"
                }), 500

            return jsonify({
                "success": True,
                "conversation_id": conversation_id,
                "question": question,
                "response": ai_response,
                "reasoning_effort": reasoning_effort
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Failed to process query",
                "details": str(e)
            }), 500

    @chat_bp.route('/stats', methods=['GET'])
    @login_required
    def get_stats():
        """Get conversation statistics for the current user.

        Returns:
            JSON response with statistics
        """
        try:
            user_id = session.get('user_id')
            stats = conversation_model.get_conversation_stats(user_id=user_id)

            return jsonify({
                "success": True,
                "stats": stats
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Failed to get statistics"
            }), 500

    return chat_bp
