"""Message/link statistics API routes."""
from flask import Blueprint, jsonify, request

from routes.request_helpers import filters_from_request
from services.stats_service import (
    get_grouped_stats,
    get_link_stats,
    get_message_stats,
    get_pie_chart_data,
)

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/api/message_stats")
def message_stats():
    return jsonify(get_message_stats())


@stats_bp.route("/api/link_stats")
def link_stats():
    return jsonify(get_link_stats())


@stats_bp.route("/api/pie_chart_data")
def pie_chart_data():
    return jsonify(get_pie_chart_data(group_by=request.args.get("group_by")))


@stats_bp.route("/api/grouped_stats")
def grouped_stats():
    group_by_tag = request.args.get("group_by_tag", "35")
    return jsonify(get_grouped_stats(group_by_tag=group_by_tag, **filters_from_request()))
