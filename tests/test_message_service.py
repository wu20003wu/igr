"""Unit tests for services.message_service."""
from datetime import datetime

from models import DbMsg, FixdConfig, db
from services.message_service import (
    apply_message_filters,
    build_message_filters,
    list_messages,
    message_like_pattern,
    serialize_message,
)


def test_message_like_pattern_with_wildcard():
    assert message_like_pattern("*35=D*") == "%35=D%"
    assert message_like_pattern("A*") == "A%"


def test_message_like_pattern_without_wildcard():
    assert message_like_pattern("35=D") == "%35=D%"


def test_message_like_pattern_empty():
    assert message_like_pattern(None) is None
    assert message_like_pattern("") is None


def test_build_message_filters_in_link():
    filters = build_message_filters(in_link="A")
    assert filters["in_link"] == "A"
    assert filters["out_link"] is None


def test_build_message_filters_link_name_fallback():
    filters = build_message_filters(link_name="B")
    assert filters["in_link"] == "B"


def test_build_message_filters_in_link_prefers_over_link_name():
    filters = build_message_filters(in_link="A", link_name="B")
    assert filters["in_link"] == "A"


def test_build_message_filters_out_link_and_message_like():
    filters = build_message_filters(out_link="C", message_like="*35=D*")
    assert filters["out_link"] == "C"
    assert filters["message_like"] == "%35=D%"


def test_build_message_filters_time_range():
    filters = build_message_filters(
        in_time_from="2024-01-15T10:00:00",
        in_time_to="2024-01-15 11:30",
    )
    assert filters["in_time_from"] == datetime(2024, 1, 15, 10, 0, 0)
    assert filters["in_time_to"] == datetime(2024, 1, 15, 11, 30)


def test_serialize_message(app_ctx):
    db.session.add(FixdConfig(link_name="A", TEST_MODE=0))
    db.session.commit()

    msg = DbMsg(
        msg_src="SYS",
        in_link="A",
        in_time=datetime(2024, 1, 15, 10, 30, 0),
        out_link=None,
        out_time=None,
        fix_msg="35=D",
    )
    db.session.add(msg)
    db.session.commit()

    serialized = serialize_message(msg)
    assert serialized["seq_nr"] == msg.SEQ_NR
    assert serialized["msg_src"] == "SYS"
    assert serialized["in_link"] == "A"
    assert serialized["in_time"] == "2024-01-15 10:30:00"
    assert serialized["out_link"] is None
    assert serialized["out_time"] is None
    assert serialized["fix_msg"] == "35=D"


def test_list_messages_filters_and_limit(app_ctx):
    db.session.add(FixdConfig(link_name="A", TEST_MODE=0))
    db.session.add(FixdConfig(link_name="B", TEST_MODE=0))
    db.session.commit()

    db.session.add(
        DbMsg(
            msg_src="S1",
            in_link="A",
            in_time=datetime(2024, 1, 15, 10, 0, 0),
            out_link="B",
            out_time=datetime(2024, 1, 15, 10, 0, 5),
            fix_msg="35=D|11=1",
        )
    )
    db.session.add(
        DbMsg(
            msg_src="S2",
            in_link="B",
            in_time=datetime(2024, 1, 15, 11, 0, 0),
            out_link=None,
            out_time=None,
            fix_msg="35=8|11=2",
        )
    )
    db.session.commit()

    only_a = list_messages(limit=10, in_link="A")
    assert len(only_a) == 1
    assert only_a[0]["in_link"] == "A"

    pending = list_messages(limit=10, out_link=None)  # out_link None means no filter
    # apply_message_filters only filters when out_link is truthy
    all_msgs = list_messages(limit=10)
    assert len(all_msgs) == 2

    limited = list_messages(limit=1)
    assert len(limited) == 1
    # newest first
    assert limited[0]["in_link"] == "B"


def test_apply_message_filters_message_like(app_ctx):
    db.session.add(FixdConfig(link_name="A", TEST_MODE=0))
    db.session.commit()
    db.session.add(
        DbMsg(
            msg_src="S",
            in_link="A",
            in_time=datetime(2024, 1, 15, 10, 0, 0),
            fix_msg="8=FIX|35=D|49=X",
        )
    )
    db.session.add(
        DbMsg(
            msg_src="S",
            in_link="A",
            in_time=datetime(2024, 1, 15, 10, 1, 0),
            fix_msg="8=FIX|35=8|49=X",
        )
    )
    db.session.commit()

    filtered = apply_message_filters(DbMsg.query, message_like="%35=D%").all()
    assert len(filtered) == 1
    assert "35=D" in filtered[0].fix_msg
