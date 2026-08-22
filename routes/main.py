"""Main application page routes."""
from flask import Blueprint, render_template

from services.graph_service import build_graph_view

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    graph = build_graph_view()
    return render_template(
        "index.html",
        nodes=graph["nodes"],
        edges=graph["edges"],
        routing_rules=graph["routing_rules"],
        reverse_routing_rules=graph["reverse_routing_rules"],
        all_rules=graph["all_rules"],
    )


@main_bp.route("/igs")
def igs_page():
    return render_template("igs.html")
