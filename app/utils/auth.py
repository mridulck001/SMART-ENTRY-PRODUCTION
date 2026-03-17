"""
Lightweight token-based admin authentication.
In production, replace with Flask-Login or JWT.
"""
import hashlib
import hmac
import os
from functools import wraps

from flask import request, jsonify, current_app, session


def _hash_password(password: str) -> str:
    salt = current_app.config['SECRET_KEY'].encode()
    return hmac.new(salt, password.encode(), hashlib.sha256).hexdigest()


def admin_required(f):
    """Decorator: protect admin endpoints with session-based auth."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({
                'status': 'error',
                'message': 'Admin authentication required.',
            }), 401
        return f(*args, **kwargs)
    return decorated
