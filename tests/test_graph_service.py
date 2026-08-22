"""Unit tests for services.graph_service.build_graph_view (current algorithm)."""
from models import DbQueueAssign, DbRoutingRules, FixdConfig, MqdConfig, db
from services.graph_service import build_graph_view


def _seed_base_links(app_ctx):
    db.session.add(FixdConfig(link_name="A", TEST_MODE=0))
    db.session.add(FixdConfig(link_name="B", TEST_MODE=1))
    db.session.add(FixdConfig(link_name="AB", TEST_MODE=0))
    db.session.add(FixdConfig(link_name="M0", TEST_MODE=0))  # FK target for MQD queue assign
    db.session.add(MqdConfig(link_name="M0"))
    db.session.commit()


def test_fixd_and_mqd_and_hardcoded_nodes(app_ctx):
    _seed_base_links(app_ctx)

    graph = build_graph_view()
    names = [n["link_name"] for n in graph["nodes"]]

    assert "A" in names
    assert "B" in names
    assert "AB" in names
    assert "M0" in names
    assert "hold" in names
    assert "$log" in names


def test_router_edges_both_directions(app_ctx):
    _seed_base_links(app_ctx)

    graph = build_graph_view()
    edge_ids = {e["id"] for e in graph["edges"]}

    assert "A_to_Router" in edge_ids
    assert "Router_to_A" in edge_ids
    assert "M0_to_Router" in edge_ids
    assert "Router_to_M0" in edge_ids
    assert "hold_to_Router" in edge_ids
    assert "Router_to_hold" in edge_ids
    assert "$log_to_Router" in edge_ids
    assert "Router_to_$log" in edge_ids


def test_direct_in_link_rule_and_queue_assignment(app_ctx):
    _seed_base_links(app_ctx)
    db.session.add(DbQueueAssign(link_name="B", queue_name="Q_B"))
    db.session.add(
        DbRoutingRules(rule_order=1, queue_name="Q_B", rule='IN_LINK = "A"')
    )
    db.session.commit()

    graph = build_graph_view()

    assert "A" in graph["routing_rules"]
    assert graph["routing_rules"]["A"] == [
        {"target": "B", "order": 1, "rule": 'IN_LINK = "A"'}
    ]
    assert graph["reverse_routing_rules"]["B"] == [
        {"source": "A", "order": 1, "rule": 'IN_LINK = "A"'}
    ]


def test_wildcard_in_link_matches_multiple_links(app_ctx):
    _seed_base_links(app_ctx)
    db.session.add(DbQueueAssign(link_name="B", queue_name="Q_B"))
    db.session.add(
        DbRoutingRules(rule_order=2, queue_name="Q_B", rule='IN_LINK LIKE "A*"')
    )
    db.session.commit()

    graph = build_graph_view()

    # A and AB match LIKE A* on FixdConfig
    sources = set(graph["routing_rules"].keys())
    assert "A" in sources
    assert "AB" in sources
    assert graph["routing_rules"]["A"][0]["target"] == "B"
    assert graph["routing_rules"]["AB"][0]["target"] == "B"

    reverse_sources = {entry["source"] for entry in graph["reverse_routing_rules"]["B"]}
    assert reverse_sources == {"A", "AB"}


def test_hardcoded_queue_targets_hold_and_log(app_ctx):
    _seed_base_links(app_ctx)
    db.session.add(
        DbRoutingRules(rule_order=7, queue_name="hold", rule='IN_LINK = "A"')
    )
    db.session.add(
        DbRoutingRules(rule_order=8, queue_name="$log", rule='IN_LINK = "B"')
    )
    db.session.commit()

    graph = build_graph_view()

    assert graph["routing_rules"]["A"][0]["target"] == "hold"
    assert graph["routing_rules"]["B"][0]["target"] == "$log"
    assert graph["reverse_routing_rules"]["hold"][0]["source"] == "A"
    assert graph["reverse_routing_rules"]["$log"][0]["source"] == "B"


def test_missing_queue_assignment_is_ignored(app_ctx):
    _seed_base_links(app_ctx)
    db.session.add(
        DbRoutingRules(rule_order=99, queue_name="Q_MISSING", rule='IN_LINK = "A"')
    )
    db.session.commit()

    graph = build_graph_view()

    assert graph["routing_rules"] == {}
    assert graph["reverse_routing_rules"] == {}


def test_rule_order_preserved_in_maps_and_all_rules(app_ctx):
    _seed_base_links(app_ctx)
    db.session.add(DbQueueAssign(link_name="B", queue_name="Q_B"))
    db.session.add(DbQueueAssign(link_name="A", queue_name="Q_A"))
    db.session.add(
        DbRoutingRules(rule_order=10, queue_name="Q_B", rule='IN_LINK = "A"')
    )
    db.session.add(
        DbRoutingRules(rule_order=3, queue_name="Q_A", rule='IN_LINK = "B"')
    )
    db.session.commit()

    graph = build_graph_view()

    assert [r.rule_order for r in graph["all_rules"]] == [3, 10]
    assert graph["routing_rules"]["A"][0]["order"] == 10
    assert graph["routing_rules"]["B"][0]["order"] == 3


def test_routing_and_reverse_structure_fields(app_ctx):
    _seed_base_links(app_ctx)
    db.session.add(DbQueueAssign(link_name="B", queue_name="Q_B"))
    rule_text = 'IN_LINK = "A"'
    db.session.add(DbRoutingRules(rule_order=1, queue_name="Q_B", rule=rule_text))
    db.session.commit()

    graph = build_graph_view()
    forward = graph["routing_rules"]["A"][0]
    reverse = graph["reverse_routing_rules"]["B"][0]

    assert set(forward.keys()) == {"target", "order", "rule"}
    assert set(reverse.keys()) == {"source", "order", "rule"}
    assert forward["rule"] == rule_text
    assert reverse["rule"] == rule_text
