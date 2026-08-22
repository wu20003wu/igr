"""Message list API and filtering helpers."""
from datetime import datetime

from flask import Blueprint, jsonify, request

from models import DbMsg

messages_bp = Blueprint("messages", __name__)


def _message_like_pattern(raw):
    """Convert user/routing-style patterns (*wildcard) to SQL LIKE."""
    if not raw:
        return None
    pattern = raw.replace("*", "%")
    if "%" not in pattern:
        pattern = f"%{pattern}%"
    return pattern


def _parse_datetime_arg(raw):
    if not raw:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _apply_message_filters(query):
    in_link = request.args.get("in_link") or request.args.get("link_name")
    out_link = request.args.get("out_link")
    message_like = _message_like_pattern(request.args.get("message_like"))
    in_time_from = _parse_datetime_arg(request.args.get("in_time_from"))
    in_time_to = _parse_datetime_arg(request.args.get("in_time_to"))

    if in_link:
        query = query.filter(DbMsg.in_link == in_link)
    if out_link:
        query = query.filter(DbMsg.out_link == out_link)
    if message_like:
        query = query.filter(DbMsg.fix_msg.like(message_like))
    if in_time_from:
        query = query.filter(DbMsg.in_time >= in_time_from)
    if in_time_to:
        query = query.filter(DbMsg.in_time <= in_time_to)
    return query


@messages_bp.route("/api/messages")
def get_messages():
    try:
        limit = int(request.args.get("limit", 10))
    except (ValueError, TypeError):
        limit = 10

    limit = min(limit, 100)
    query = _apply_message_filters(DbMsg.query)
    messages = query.order_by(DbMsg.in_time.desc()).limit(limit).all()

    output = []
    for msg in messages:
        output.append(
            {
                "seq_nr": msg.SEQ_NR,
                "msg_src": msg.msg_src,
                "in_link": msg.in_link,
                "in_time": msg.in_time.strftime("%Y-%m-%d %H:%M:%S") if msg.in_time else None,
                "out_link": msg.out_link,
                "out_time": msg.out_time.strftime("%Y-%m-%d %H:%M:%S") if msg.out_time else None,
                "fix_msg": msg.fix_msg,
            }
        )

    return jsonify(output)
