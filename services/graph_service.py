"""Graph/routing view construction for the IGR index page."""
import re

from models import DbQueueAssign, DbRoutingRules, FixdConfig, MqdConfig

# Hardcoded queue assignments (queue_name -> link_name)
_HARDCODED_QUEUES = {
    "hold": "hold",
    "$log": "$log",
}


def build_nodes(fixd_nodes, mqd_nodes):
    """Build graph node dicts from FIXD/MQD configs plus hardcoded hold/$log."""
    return [
        *[{"link_name": n.link_name} for n in fixd_nodes],
        *[{"link_name": n.link_name} for n in mqd_nodes],
        {"link_name": "hold"},
        {"link_name": "$log"},
    ]


def build_router_edges(nodes):
    """Generate bidirectional Router <-> link edges with existing id/source/target."""
    router_links = [n["link_name"] for n in nodes if n["link_name"] != "Router"]
    edges = []
    for link in router_links:
        edges.append(
            {
                "id": f"{link}_to_Router",
                "source": link,
                "target": "Router",
            }
        )
        edges.append(
            {
                "id": f"Router_to_{link}",
                "source": "Router",
                "target": link,
            }
        )
    return edges


def resolve_queue_target(queue_name):
    """
    Resolve a rule queue_name to its target link_name.

    Returns None when there is no hardcoded mapping and no DbQueueAssign row
    (current behavior: skip the rule).
    """
    if queue_name in _HARDCODED_QUEUES.values():
        return [k for k, v in _HARDCODED_QUEUES.items() if v == queue_name][0]

    queue_assignment = DbQueueAssign.query.filter_by(queue_name=queue_name).first()
    if not queue_assignment:
        return None
    return queue_assignment.link_name


def find_matching_links(pattern):
    """
    Match an IN_LINK pattern against FixdConfig and MqdConfig.

    Converts '*' to '%' and uses exact lookup or SQL LIKE as before.
    """
    sql_pattern = pattern.replace("*", "%")
    is_wildcard = "%" in sql_pattern

    if is_wildcard:
        matching_fixd = FixdConfig.query.filter(
            FixdConfig.link_name.like(sql_pattern)
        ).all()
        matching_mqd = MqdConfig.query.filter(
            MqdConfig.link_name.like(sql_pattern)
        ).all()
        return matching_fixd + matching_mqd

    matching_fixd = FixdConfig.query.filter_by(link_name=sql_pattern).all()
    matching_mqd = MqdConfig.query.filter_by(link_name=sql_pattern).all()
    return matching_fixd + matching_mqd


def build_routing_maps(rules):
    """
    Build forward routing_rules and reverse_routing_rules from DbRoutingRules.

    Preserves entry structure: target/source, order, rule text.
    """
    routing_rules = {}
    reverse_routing_rules = {}

    for rule in rules:
        # Alle IN_LINKs finden (auch bei OR-Kombinationen)
        link_patterns = re.findall(r'IN_LINK\s+(?:=|LIKE)\s*"([^"]+)"', rule.rule)

        target_link = resolve_queue_target(rule.queue_name)
        if target_link is None:
            continue

        for pattern in link_patterns:
            matching_links = find_matching_links(pattern)

            for link in matching_links:
                source_link = link.link_name

                if source_link not in routing_rules:
                    routing_rules[source_link] = []
                routing_rules[source_link].append(
                    {
                        "target": target_link,
                        "order": rule.rule_order,
                        "rule": rule.rule,
                    }
                )

                if target_link not in reverse_routing_rules:
                    reverse_routing_rules[target_link] = []
                reverse_routing_rules[target_link].append(
                    {
                        "source": source_link,
                        "order": rule.rule_order,
                        "rule": rule.rule,
                    }
                )

    return routing_rules, reverse_routing_rules


def build_graph_view():
    """Orchestrate graph construction for the index template."""
    fixd_nodes = FixdConfig.query.all()
    mqd_nodes = MqdConfig.query.all()
    nodes = build_nodes(fixd_nodes, mqd_nodes)
    edges = build_router_edges(nodes)

    rules = DbRoutingRules.query.all()
    routing_rules, reverse_routing_rules = build_routing_maps(rules)

    all_rules = DbRoutingRules.query.order_by(DbRoutingRules.rule_order).all()

    return {
        "nodes": nodes,
        "edges": edges,
        "routing_rules": routing_rules,
        "reverse_routing_rules": reverse_routing_rules,
        "all_rules": all_rules,
    }
