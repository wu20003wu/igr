"""Statistics calculation and query logic."""
from sqlalchemy import func

from models import DbMsg, FixdConfig, db
from services.message_service import query_filtered_messages
from utils.fix_parser import extract_tag_value


def _get_incoming_counts_by_link():
    return dict(
        db.session.query(DbMsg.in_link, func.count(DbMsg.in_link)).group_by(DbMsg.in_link).all()
    )


def _get_outgoing_counts_by_link():
    return dict(
        db.session.query(DbMsg.out_link, func.count(DbMsg.out_link))
        .filter(DbMsg.out_link.isnot(None))
        .group_by(DbMsg.out_link)
        .all()
    )


def _get_incoming_counts_by_test_mode():
    return dict(
        db.session.query(FixdConfig.TEST_MODE, func.count(DbMsg.SEQ_NR))
        .join(FixdConfig, DbMsg.in_link == FixdConfig.link_name)
        .group_by(FixdConfig.TEST_MODE)
        .all()
    )


def _get_outgoing_counts_by_test_mode():
    return dict(
        db.session.query(FixdConfig.TEST_MODE, func.count(DbMsg.SEQ_NR))
        .join(FixdConfig, DbMsg.out_link == FixdConfig.link_name)
        .filter(DbMsg.out_link.isnot(None))
        .group_by(FixdConfig.TEST_MODE)
        .all()
    )


def _combine_totals(keys, incoming, outgoing, *, omit_zero=False):
    """Sum incoming + outgoing per key; optionally drop zero totals."""
    totals = {}
    for key in keys:
        total = incoming.get(key, 0) + outgoing.get(key, 0)
        if omit_zero and total <= 0:
            continue
        totals[key] = total
    return totals


def _labels_and_data_sorted_desc(totals):
    """Convert {label: count} to pie/grouped chart payload sorted by count desc."""
    sorted_items = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return {
        "labels": [item[0] for item in sorted_items],
        "data": [item[1] for item in sorted_items],
    }


def get_message_stats():
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

    return {
        "total_messages": total_msgs,
        "pending_messages": pending_msgs,
        "avg_processing_time_seconds": round(avg_processing_time, 2),
    }


def get_link_stats():
    link_to_mode_map = dict(
        db.session.query(FixdConfig.link_name, FixdConfig.TEST_MODE).all()
    )
    incoming = _get_incoming_counts_by_link()
    outgoing = _get_outgoing_counts_by_link()

    stats_data = []
    for link_name in sorted(link_to_mode_map.keys()):
        in_count = incoming.get(link_name, 0)
        out_count = outgoing.get(link_name, 0)
        stats_data.append(
            {
                "link_name": link_name,
                "test_mode": link_to_mode_map.get(link_name),
                "incoming": in_count,
                "outgoing": out_count,
                "total": in_count + out_count,
            }
        )

    stats_data.sort(key=lambda x: x["total"], reverse=True)
    return stats_data


def get_pie_chart_data(group_by=None):
    """Provides data for the pie chart, showing message totals per link."""
    if group_by == "test_mode":
        incoming = _get_incoming_counts_by_test_mode()
        outgoing = _get_outgoing_counts_by_test_mode()
        all_test_modes = {mode for mode, in db.session.query(FixdConfig.TEST_MODE).distinct()}
        raw_totals = _combine_totals(all_test_modes, incoming, outgoing, omit_zero=True)
        mode_totals = {f"Test Mode {mode}": total for mode, total in raw_totals.items()}
        return _labels_and_data_sorted_desc(mode_totals)

    incoming = _get_incoming_counts_by_link()
    outgoing = _get_outgoing_counts_by_link()
    all_link_names = {link.link_name for link in FixdConfig.query.all()}
    link_totals = _combine_totals(all_link_names, incoming, outgoing, omit_zero=True)
    return _labels_and_data_sorted_desc(link_totals)


def get_grouped_stats(group_by_tag="35", **filters):
    """Message stats grouped by a FIX tag, optionally filtered."""
    messages = query_filtered_messages(**filters)

    stats = {}
    for msg in messages:
        if msg.fix_msg:
            value = extract_tag_value(msg.fix_msg, group_by_tag)
            if value:
                stats[value] = stats.get(value, 0) + 1

    return _labels_and_data_sorted_desc(stats)
