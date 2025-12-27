"""Authentication middleware for protecting routes."""
from functools import wraps
from flask import session, jsonify, request
from typing import Callable, Any


def login_required(f: Callable) -> Callable:
    """Decorator to require authentication for routes.

    Args:
        f: Flask route function

    Returns:
        Wrapped function that checks authentication
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if 'user_id' not in session:
            return jsonify({
                "success": False,
                "error": "Authentication required",
                "code": "AUTH_REQUIRED"
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def get_current_user() -> str:
    """Get the current authenticated user ID from session.

    Returns:
        str: User ID from session

    Raises:
        ValueError: If no user is authenticated
    """
    user_id = session.get('user_id')
    if not user_id:
        raise ValueError("No authenticated user")
    return user_id


def optional_auth(f: Callable) -> Callable:
    """Decorator for routes that work with or without authentication.

    Args:
        f: Flask route function

    Returns:
        Wrapped function
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # Just pass through - route can check session itself
        return f(*args, **kwargs)
    return decorated_function
