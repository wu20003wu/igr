"""Shared HTTP/request helpers for route modules (no DB/business logic)."""
from flask import request

from services.message_service import build_message_filters


def filters_from_request():
    """Normalize message-filter query args from the current Flask request."""
    return build_message_filters(
        in_link=request.args.get("in_link"),
        link_name=request.args.get("link_name"),
        out_link=request.args.get("out_link"),
        message_like=request.args.get("message_like"),
        in_time_from=request.args.get("in_time_from"),
        in_time_to=request.args.get("in_time_to"),
    )
