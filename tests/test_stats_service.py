"""Unit tests for services.stats_service with deterministic sample data."""
from datetime import datetime, timedelta

from models import DbMsg, FixdConfig, db
from services.message_service import build_message_filters
from services.stats_service import (
    get_grouped_stats,
    get_link_stats,
    get_message_stats,
    get_pie_chart_data,
)


def _add_link(name, test_mode=0):
    db.session.add(FixdConfig(link_name=name, TEST_MODE=test_mode))


def _add_msg(in_link, out_link, in_time, out_time, fix_msg, msg_src="S"):
    db.session.add(
        DbMsg(
            msg_src=msg_src,
            in_link=in_link,
            in_time=in_time,
            out_link=out_link,
            out_time=out_time,
            fix_msg=fix_msg,
        )
    )


def test_message_stats_totals_pending_and_avg(app_ctx):
    _add_link("A")
    _add_link("B")
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    _add_msg("A", "B", t0, t0 + timedelta(seconds=2), "35=D")
    _add_msg("A", "B", t0, t0 + timedelta(seconds=4), "35=D")
    _add_msg("A", None, t0, None, "35=8")  # pending
    db.session.commit()

    stats = get_message_stats()
    assert stats["total_messages"] == 3
    assert stats["pending_messages"] == 1
    assert stats["avg_processing_time_seconds"] == 3.0  # (2+4)/2


def test_message_stats_no_completed_messages(app_ctx):
    _add_link("A")
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    _add_msg("A", None, t0, None, "35=D")
    db.session.commit()

    stats = get_message_stats()
    assert stats["total_messages"] == 1
    assert stats["pending_messages"] == 1
    assert stats["avg_processing_time_seconds"] == 0


def test_link_stats_incoming_outgoing_and_sort(app_ctx):
    _add_link("A", test_mode=1)
    _add_link("B", test_mode=2)
    _add_link("C", test_mode=0)
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    # A: 2 in, 0 out -> total 2
    _add_msg("A", "B", t0, t0 + timedelta(seconds=1), "35=D")
    _add_msg("A", "B", t0, t0 + timedelta(seconds=1), "35=D")
    # B: 0 in from others counted as in_link, 2 out as out_link; also 1 in
    _add_msg("B", "C", t0, t0 + timedelta(seconds=1), "35=8")
    # C: 1 in (from B out), 0 out from C as in_link with out
    db.session.commit()

    stats = get_link_stats()
    by_name = {row["link_name"]: row for row in stats}

    assert by_name["A"]["incoming"] == 2
    assert by_name["A"]["outgoing"] == 0
    assert by_name["A"]["total"] == 2
    assert by_name["A"]["test_mode"] == 1

    assert by_name["B"]["incoming"] == 1
    assert by_name["B"]["outgoing"] == 2
    assert by_name["B"]["total"] == 3

    assert by_name["C"]["incoming"] == 0
    assert by_name["C"]["outgoing"] == 1
    assert by_name["C"]["total"] == 1

    totals = [row["total"] for row in stats]
    assert totals == sorted(totals, reverse=True)


def test_pie_chart_by_link(app_ctx):
    _add_link("A")
    _add_link("B")
    _add_link("C")  # zero traffic -> omitted
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    _add_msg("A", "B", t0, t0 + timedelta(seconds=1), "35=D")
    _add_msg("A", None, t0, None, "35=D")
    db.session.commit()

    pie = get_pie_chart_data()
    # A: 2 in + 0 out = 2; B: 0 in + 1 out = 1
    assert pie["labels"][0] == "A"
    assert pie["data"][0] == 2
    assert "B" in pie["labels"]
    assert "C" not in pie["labels"]


def test_pie_chart_by_test_mode(app_ctx):
    _add_link("A", test_mode=1)
    _add_link("B", test_mode=2)
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    _add_msg("A", "B", t0, t0 + timedelta(seconds=1), "35=D")
    _add_msg("A", None, t0, None, "35=D")
    db.session.commit()

    pie = get_pie_chart_data(group_by="test_mode")
    # mode 1: A in x2 = 2; mode 2: B out x1 = 1
    assert pie["labels"][0] == "Test Mode 1"
    assert pie["data"][0] == 2
    assert "Test Mode 2" in pie["labels"]


def test_grouped_fix_tag_stats(app_ctx):
    _add_link("A")
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    _add_msg("A", None, t0, None, "8=FIX|35=D|49=X")
    _add_msg("A", None, t0, None, "8=FIX|35=D|49=Y")
    _add_msg("A", None, t0, None, "8=FIX|35=8|49=Z")
    db.session.commit()

    grouped = get_grouped_stats(group_by_tag="35")
    assert grouped["labels"][0] == "D"
    assert grouped["data"][0] == 2
    assert grouped["labels"][1] == "8"
    assert grouped["data"][1] == 1


def test_grouped_stats_with_filters(app_ctx):
    _add_link("A")
    _add_link("B")
    t0 = datetime(2024, 1, 15, 10, 0, 0)
    _add_msg("A", None, t0, None, "35=D")
    _add_msg("B", None, t0, None, "35=D")
    _add_msg("B", None, t0, None, "35=8")
    db.session.commit()

    filters = build_message_filters(in_link="B")
    grouped = get_grouped_stats(group_by_tag="35", **filters)
    assert set(zip(grouped["labels"], grouped["data"])) == {("D", 1), ("8", 1)}
