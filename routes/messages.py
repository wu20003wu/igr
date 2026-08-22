"""Message list API routes."""
from flask import Blueprint, jsonify, request

from routes.request_helpers import filters_from_request
from services.message_service import list_messages

messages_bp = Blueprint("messages", __name__)


@messages_bp.route("/api/messages")
def get_messages():
    try:
        limit = int(request.args.get("limit", 10))
    except (ValueError, TypeError):
        limit = 10

    return jsonify(list_messages(limit=limit, **filters_from_request()))
