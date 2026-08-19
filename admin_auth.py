"""Minimal single-admin auth via username/password from env/config."""
from __future__ import annotations

import secrets
from functools import wraps

from flask import current_app, jsonify, session


def is_admin() -> bool:
    return bool(session.get("is_admin"))


def check_credentials(username: str, password: str) -> bool:
    """Validate against the single configured admin (constant-time compare)."""
    expected_user = current_app.config.get("ADMIN_USERNAME") or ""
    expected_pass = current_app.config.get("ADMIN_PASSWORD") or ""
    if not expected_user or not expected_pass:
        return False
    user_ok = secrets.compare_digest(username.strip(), expected_user)
    pass_ok = secrets.compare_digest(password, expected_pass)
    return user_ok and pass_ok


def admin_required(view):
    """Protect a view so only an authenticated admin session can access it."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_admin():
            return jsonify(error="Unauthorized"), 401
        return view(*args, **kwargs)

    return wrapped
