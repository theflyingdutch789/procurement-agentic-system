"""Authentication routes for user registration and login."""
from flask import Blueprint, request, jsonify, session
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models.user import User
from middleware.auth import login_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def init_auth_routes(db):
    """Initialize authentication routes with database connection.

    Args:
        db: MongoDB database instance

    Returns:
        Blueprint: Configured authentication blueprint
    """
    user_model = User(db)

    @auth_bp.route('/register', methods=['POST'])
    def register():
        """Register a new user.

        Expected JSON body:
        {
            "username": "string",
            "email": "string",
            "password": "string",
            "full_name": "string" (optional)
        }

        Returns:
            JSON response with user data or error
        """
        try:
            data = request.get_json()

            # Validate required fields
            if not data or not data.get('username') or not data.get('email') or not data.get('password'):
                return jsonify({
                    "success": False,
                    "error": "Username, email, and password are required"
                }), 400

            # Validate password length
            if len(data['password']) < 6:
                return jsonify({
                    "success": False,
                    "error": "Password must be at least 6 characters"
                }), 400

            # Validate email format (basic check)
            if '@' not in data['email']:
                return jsonify({
                    "success": False,
                    "error": "Invalid email format"
                }), 400

            # Create user
            user = user_model.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                full_name=data.get('full_name')
            )

            # Set session
            session['user_id'] = user['_id']
            session['username'] = user['username']

            return jsonify({
                "success": True,
                "user": user,
                "message": "Registration successful"
            }), 201

        except ValueError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 400
        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Registration failed"
            }), 500

    @auth_bp.route('/login', methods=['POST'])
    def login():
        """Authenticate user and create session.

        Expected JSON body:
        {
            "username": "string",  // Can be username or email
            "password": "string"
        }

        Returns:
            JSON response with user data or error
        """
        try:
            data = request.get_json()

            # Validate required fields
            if not data or not data.get('username') or not data.get('password'):
                return jsonify({
                    "success": False,
                    "error": "Username and password are required"
                }), 400

            # Authenticate user
            user = user_model.authenticate(
                username=data['username'],
                password=data['password']
            )

            if not user:
                return jsonify({
                    "success": False,
                    "error": "Invalid username or password"
                }), 401

            # Set session
            session['user_id'] = user['_id']
            session['username'] = user['username']

            return jsonify({
                "success": True,
                "user": user,
                "message": "Login successful"
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Login failed"
            }), 500

    @auth_bp.route('/logout', methods=['POST'])
    @login_required
    def logout():
        """Logout user and clear session.

        Returns:
            JSON response confirming logout
        """
        session.clear()
        return jsonify({
            "success": True,
            "message": "Logout successful"
        }), 200

    @auth_bp.route('/me', methods=['GET'])
    @login_required
    def get_current_user():
        """Get current authenticated user information.

        Returns:
            JSON response with user data
        """
        try:
            user_id = session.get('user_id')
            user = user_model.get_user_by_id(user_id)

            if not user:
                session.clear()
                return jsonify({
                    "success": False,
                    "error": "User not found"
                }), 404

            return jsonify({
                "success": True,
                "user": user
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Failed to get user information"
            }), 500

    @auth_bp.route('/check', methods=['GET'])
    def check_auth():
        """Check if user is authenticated.

        Returns:
            JSON response with authentication status
        """
        if 'user_id' in session:
            return jsonify({
                "success": True,
                "authenticated": True,
                "user_id": session.get('user_id'),
                "username": session.get('username')
            }), 200
        else:
            return jsonify({
                "success": True,
                "authenticated": False
            }), 200

    @auth_bp.route('/change-password', methods=['POST'])
    @login_required
    def change_password():
        """Change user password.

        Expected JSON body:
        {
            "old_password": "string",
            "new_password": "string"
        }

        Returns:
            JSON response confirming password change
        """
        try:
            data = request.get_json()
            user_id = session.get('user_id')

            if not data or not data.get('old_password') or not data.get('new_password'):
                return jsonify({
                    "success": False,
                    "error": "Old password and new password are required"
                }), 400

            if len(data['new_password']) < 6:
                return jsonify({
                    "success": False,
                    "error": "New password must be at least 6 characters"
                }), 400

            success = user_model.change_password(
                user_id=user_id,
                old_password=data['old_password'],
                new_password=data['new_password']
            )

            if not success:
                return jsonify({
                    "success": False,
                    "error": "Failed to change password. Check your old password."
                }), 400

            return jsonify({
                "success": True,
                "message": "Password changed successfully"
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Failed to change password"
            }), 500

    return auth_bp
