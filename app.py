from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import re, os
import cx_Oracle
from models import db, FixdConfig, MqdConfig, DbQueueAssign, DbRoutingRules, insert_sample_data
from datetime import datetime, timedelta

app = Flask(__name__, instance_relative_config=True)
CORS(app)  # CORS aktivieren, um Anfragen vom Frontend zu erlauben
app.config.from_pyfile('config.py')
# Configure the app's database URI using an environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///igt.db')

db.init_app(app)

# Stelle sicher, dass der instance-Ordner existiert
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Datenbanktabellen und Testdaten erstellen (innerhalb des App-Kontexts)
# (ACHTUNG: Oracle benötigt DBA-Rechte für CREATE TABLESPACE)
with app.app_context():
    # db.create_all()
    # insert_sample_data()
    pass

@app.route('/')
def index():
    fixd_nodes = FixdConfig.query.all()
    mqd_nodes = MqdConfig.query.all()

    nodes = [
        *[{'link_name': n.link_name} for n in fixd_nodes],
        *[{'link_name': n.link_name} for n in mqd_nodes],
        {'link_name': 'hold'},
        {'link_name': '$log'}
    ]

    # Hardcoded queue assignments MUST BE DEFINED HERE
    HARDCODED_QUEUES = {
        'hold': 'hold',
        '$log': '$log'
    }

    router_links = [n['link_name'] for n in nodes if n['link_name'] != 'Router']

    edges = []

    for link in router_links:
        edges.append({
            'id': f'{link}_to_Router',
            'source': link,
            'target': 'Router',
        })
        edges.append({
            'id': f'Router_to_{link}',
            'source': 'Router',
            'target': link,
        })

    routing_rules = {}
    reverse_routing_rules = {}

    for rule in DbRoutingRules.query.all():
        # Alle IN_LINKs finden (auch bei OR-Kombinationen)
        link_patterns = re.findall(r'IN_LINK\s+(?:=|LIKE)\s*"([^"]+)"', rule.rule)

        queue_name = rule.queue_name
        
        # Check for hardcoded queues first
        if queue_name in HARDCODED_QUEUES.values():
            link_name = [k for k,v in HARDCODED_QUEUES.items() if v == queue_name][0]
        else:
            queue_assignment = DbQueueAssign.query.filter_by(queue_name=queue_name).first()
            if not queue_assignment:
                continue
            link_name = queue_assignment.link_name

        for pattern in link_patterns:
            sql_pattern = pattern.replace('*', '%')
            is_wildcard = '%' in sql_pattern

            # Include both FixdConfig and MqdConfig in the query
            if is_wildcard:
                matching_fixd = FixdConfig.query.filter(FixdConfig.link_name.like(sql_pattern)).all()
                matching_mqd = MqdConfig.query.filter(MqdConfig.link_name.like(sql_pattern)).all()
                matching_links = matching_fixd + matching_mqd
            else:
                matching_fixd = FixdConfig.query.filter_by(link_name=sql_pattern).all()
                matching_mqd = MqdConfig.query.filter_by(link_name=sql_pattern).all()
                matching_links = matching_fixd + matching_mqd

            for link in matching_links:
                # Use correct source and target mapping
                source_link = link.link_name
                target_link = link_name  # From queue assignment

                if source_link not in routing_rules:
                    routing_rules[source_link] = []
                routing_rules[source_link].append({
                    'target': target_link,
                    'order': rule.rule_order,
                    'rule': rule.rule
                })

                # Reverse-Mapping with order
                if target_link not in reverse_routing_rules:
                    reverse_routing_rules[target_link] = []
                reverse_routing_rules[target_link].append({
                    'source': source_link,
                    'order': rule.rule_order,
                    'rule': rule.rule
                })

    all_rules = DbRoutingRules.query.order_by(DbRoutingRules.rule_order).all()

    return render_template('index.html',
                           nodes=nodes,
                           edges=edges,
                           routing_rules=routing_rules,
                           reverse_routing_rules=reverse_routing_rules,
                           all_rules=all_rules)

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
    app.run(debug=True, port=10010, host='0.0.0.0') # eng/st: 10010, prod:10001
