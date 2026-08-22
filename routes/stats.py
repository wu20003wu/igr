"""Message/link statistics API routes."""
import re

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from models import DbMsg, FixdConfig, db
from routes.messages import _apply_message_filters

stats_bp = Blueprint("stats", __name__)


def extract_tag_value(fix_string, tag):
    """Extracts the value of a given tag from a FIX string."""
    pattern = f"(?:^|\\|){tag}=([^|]+)"
    match = re.search(pattern, fix_string)
    if match:
        return match.group(1)
    return None


@stats_bp.route("/api/message_stats")
def message_stats():
    total_msgs = db.session.query(func.count(DbMsg.SEQ_NR)).scalar()
    pending_msgs = DbMsg.query.filter(DbMsg.out_link.is_(None)).count()

    completed_msgs = DbMsg.query.filter(DbMsg.out_time.isnot(None)).all()
    if completed_msgs:
        total_processing_time = sum(
            [
                (msg.out_time - msg.in_time).total_seconds()
                for msg in completed_msgs
                if msg.in_time and msg.out_time
            ]
        )
        avg_processing_time = (
            total_processing_time / len(completed_msgs) if len(completed_msgs) > 0 else 0
        )
    else:
        avg_processing_time = 0

    return jsonify(
        {
            "total_messages": total_msgs,
            "pending_messages": pending_msgs,
            "avg_processing_time_seconds": round(avg_processing_time, 2),
        }
    )


@stats_bp.route("/api/link_stats")
def link_stats():
    all_links_with_modes = db.session.query(FixdConfig.link_name, FixdConfig.TEST_MODE).all()
    link_to_mode_map = dict(all_links_with_modes)

    incoming_stats = dict(
        db.session.query(DbMsg.in_link, func.count(DbMsg.in_link)).group_by(DbMsg.in_link).all()
    )

    outgoing_stats = dict(
        db.session.query(DbMsg.out_link, func.count(DbMsg.out_link))
        .filter(DbMsg.out_link.isnot(None))
        .group_by(DbMsg.out_link)
        .all()
    )

    stats_data = []
    for link_name in sorted(link_to_mode_map.keys()):
        incoming = incoming_stats.get(link_name, 0)
        outgoing = outgoing_stats.get(link_name, 0)
        stats_data.append(
            {
                "link_name": link_name,
                "test_mode": link_to_mode_map.get(link_name),
                "incoming": incoming,
                "outgoing": outgoing,
                "total": incoming + outgoing,
            }
        )

    stats_data.sort(key=lambda x: x["total"], reverse=True)
    return jsonify(stats_data)


@stats_bp.route("/api/pie_chart_data")
def pie_chart_data():
    """Provides data for the pie chart, showing message totals per link."""
    group_by = request.args.get("group_by")

    if group_by == "test_mode":
        incoming_stats = dict(
            db.session.query(FixdConfig.TEST_MODE, func.count(DbMsg.SEQ_NR))
            .join(FixdConfig, DbMsg.in_link == FixdConfig.link_name)
            .group_by(FixdConfig.TEST_MODE)
            .all()
        )

        outgoing_stats = dict(
            db.session.query(FixdConfig.TEST_MODE, func.count(DbMsg.SEQ_NR))
            .join(FixdConfig, DbMsg.out_link == FixdConfig.link_name)
            .filter(DbMsg.out_link.isnot(None))
            .group_by(FixdConfig.TEST_MODE)
            .all()
        )

        all_test_modes = {mode for mode, in db.session.query(FixdConfig.TEST_MODE).distinct()}

        mode_totals = {}
        for mode in all_test_modes:
            total = incoming_stats.get(mode, 0) + outgoing_stats.get(mode, 0)
            if total > 0:
                mode_totals[f"Test Mode {mode}"] = total

        sorted_modes = sorted(mode_totals.items(), key=lambda item: item[1], reverse=True)
        labels = [item[0] for item in sorted_modes]
        data = [item[1] for item in sorted_modes]
        return jsonify({"labels": labels, "data": data})

    incoming_stats = dict(
        db.session.query(DbMsg.in_link, func.count(DbMsg.in_link)).group_by(DbMsg.in_link).all()
    )

    outgoing_stats = dict(
        db.session.query(DbMsg.out_link, func.count(DbMsg.out_link))
        .filter(DbMsg.out_link.isnot(None))
        .group_by(DbMsg.out_link)
        .all()
    )

    link_totals = {}
    all_link_names = {link.link_name for link in FixdConfig.query.all()}

    for link_name in all_link_names:
        total = incoming_stats.get(link_name, 0) + outgoing_stats.get(link_name, 0)
        if total > 0:
            link_totals[link_name] = total

    sorted_links = sorted(link_totals.items(), key=lambda item: item[1], reverse=True)
    labels = [item[0] for item in sorted_links]
    data = [item[1] for item in sorted_links]
    return jsonify({"labels": labels, "data": data})


@stats_bp.route("/api/grouped_stats")
def grouped_stats():
    """Provides message stats grouped by a specified FIX tag, optionally filtered."""
    group_by_tag = request.args.get("group_by_tag", "35")
    messages = _apply_message_filters(DbMsg.query).all()

    stats = {}
    for msg in messages:
        if msg.fix_msg:
            value = extract_tag_value(msg.fix_msg, group_by_tag)
            if value:
                stats[value] = stats.get(value, 0) + 1

    sorted_stats = sorted(stats.items(), key=lambda item: item[1], reverse=True)
    labels = [item[0] for item in sorted_stats]
    data = [item[1] for item in sorted_stats]
    return jsonify({"labels": labels, "data": data})
