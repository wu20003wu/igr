"""Message query and filter logic."""
from models import DbMsg
from utils.datetime_parser import parse_datetime_arg


def message_like_pattern(raw):
    """Convert user/routing-style patterns (*wildcard) to SQL LIKE."""
    if not raw:
        return None
    pattern = raw.replace("*", "%")
    if "%" not in pattern:
        pattern = f"%{pattern}%"
    return pattern


def build_message_filters(
    in_link=None,
    link_name=None,
    out_link=None,
    message_like=None,
    in_time_from=None,
    in_time_to=None,
):
    """Normalize raw filter parameters into values ready for apply_message_filters."""
    return {
        "in_link": in_link or link_name,
        "out_link": out_link,
        "message_like": message_like_pattern(message_like),
        "in_time_from": parse_datetime_arg(in_time_from),
        "in_time_to": parse_datetime_arg(in_time_to),
    }


def apply_message_filters(
    query,
    in_link=None,
    out_link=None,
    message_like=None,
    in_time_from=None,
    in_time_to=None,
):
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


def serialize_message(msg):
    return {
        "seq_nr": msg.SEQ_NR,
        "msg_src": msg.msg_src,
        "in_link": msg.in_link,
        "in_time": msg.in_time.strftime("%Y-%m-%d %H:%M:%S") if msg.in_time else None,
        "out_link": msg.out_link,
        "out_time": msg.out_time.strftime("%Y-%m-%d %H:%M:%S") if msg.out_time else None,
        "fix_msg": msg.fix_msg,
    }


def list_messages(limit=10, **filters):
    """Return a serialized list of messages matching the given filters."""
    limit = min(limit, 100)
    query = apply_message_filters(DbMsg.query, **filters)
    messages = query.order_by(DbMsg.in_time.desc()).limit(limit).all()
    return [serialize_message(msg) for msg in messages]


def query_filtered_messages(**filters):
    """Return DbMsg rows matching filters (unordered helper for stats)."""
    return apply_message_filters(DbMsg.query, **filters).all()
