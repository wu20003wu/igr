from flask import Flask, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import re, os
import cx_Oracle
from models import db, FixdConfig, DbQueueAssign, DbRoutingRules, insert_sample_data

app = Flask(__name__, instance_relative_config=True)
CORS(app)  # CORS aktivieren, um Anfragen vom Frontend zu erlauben
app.config.from_pyfile('config.py')
db.init_app(app)

# Stelle sicher, dass der instance-Ordner existiert
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Datenbanktabellen und Testdaten erstellen (innerhalb des App-Kontexts)
# (ACHTUNG: Oracle benötigt DBA-Rechte für CREATE TABLESPACE)
with app.app_context():
    db.create_all()
    insert_sample_data()

@app.route('/')
def index():
    nodes = FixdConfig.query.all()

    edges = []
    router_links = [n.link_name for n in nodes if n.link_name != 'Router']

    for link in router_links:
        edges.append({
            'id': f'{link}_to_Router',
            'source': link,
            'target': 'Router',
            'label': f'{link} → Router'
        })
        edges.append({
            'id': f'Router_to_{link}',
            'source': 'Router',
            'target': link,
            'label': f'Router → {link}'
        })

    routing_rules = {}
    reverse_routing_rules = {}

    for rule in DbRoutingRules.query.all():
        # Alle IN_LINKs finden (auch bei OR-Kombinationen)
        link_patterns = re.findall(r'IN_LINK\s+(?:=|LIKE)\s*"([^"]+)"', rule.rule)

        queue_assignment = DbQueueAssign.query.filter_by(queue_name=rule.queue_name).first()
        if not queue_assignment:
            continue

        for pattern in link_patterns:
            sql_pattern = pattern.replace('*', '%')
            is_wildcard = '%' in sql_pattern

            if is_wildcard:
                matching_links = FixdConfig.query.filter(
                    FixdConfig.link_name.like(sql_pattern)
                ).all()
            else:
                matching_links = FixdConfig.query.filter_by(
                    link_name=sql_pattern
                ).all()

            for link in matching_links:
                # Routing-Mapping
                if link.link_name not in routing_rules:
                    routing_rules[link.link_name] = []
                routing_rules[link.link_name].append(queue_assignment.link_name)

                # Reverse-Mapping
                if queue_assignment.queue_name not in reverse_routing_rules:
                    reverse_routing_rules[queue_assignment.queue_name] = []
                reverse_routing_rules[queue_assignment.queue_name].append(link.link_name)

    return render_template('index.html',
                           nodes=nodes,
                           edges=edges,
                           routing_rules=routing_rules,
                           reverse_routing_rules=reverse_routing_rules)

def get_edges():
    nodes = FixdConfig.query.all()
    router_links = [n.link_name for n in nodes]
    
    edges = []
    for link in router_links:
        edges.append({
            'id': f'{link}_to_Router',
            'source': link,
            'target': 'Router'
        })
        edges.append({
            'id': f'Router_to_{link}',
            'source': 'Router',
            'target': link
        })
    return edges

if __name__ == '__main__':
    app.run(debug=True, port=10004) # igt port
