from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import re
import cx_Oracle
from config import Config  # Neue Import-Zeile

app = Flask(__name__)
# Oracle-Verbindungsstring ersetzen
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///igt.db'
app.config.from_object(Config) 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# früher Node
class FixdConfig(db.Model):
    __tablename__ = 'FIXD_CONFIG'
    link_name = db.Column(db.String(50), primary_key=True)

# früher Rule
class DbRoutingRules(db.Model):
    __tablename__ = 'DB_ROUTING_RULES'
    id = db.Column(db.Integer, db.Sequence('routing_rules_seq'), primary_key=True)
    rule_order = db.Column(db.Integer)
    queue_name = db.Column(db.String(50), db.ForeignKey('DB_QUEUE_ASSIGN.queue_name'))
    rule = db.Column(db.String(100))
    queue_assignment = db.relationship('DbQueueAssign', backref='routing_rules')

# neu: node hat cash, queue = warteschlange, jeder Link hat eine Warteschlange
class DbQueueAssign(db.Model):
    __tablename__ = 'DB_QUEUE_ASSIGN'
    link_name = db.Column(db.String(50), db.ForeignKey('FIXD_CONFIG.link_name'), primary_key=True)
    queue_name = db.Column(db.String(50), unique=True)

# Datenbank erstellen (ACHTUNG: Oracle benötigt DBA-Rechte für CREATE TABLESPACE)
with app.app_context():
    db.create_all()

    if not FixdConfig.query.first():
        links = ['Router', 'A', 'B', 'C', 'AB']
        for l in links:
            db.session.add(FixdConfig(link_name=l))
        
        # Commit nach FixdConfig einfügen
        db.session.commit()  # WICHTIG: Erst Parent-Records committen

        for link in links:
            db.session.add(DbQueueAssign(
                link_name=link,
                queue_name=f'Q_{link}'
            ))

        rules = [
            (1, 'Q_B', 'IN_LINK = "A" OR IN_LINK LIKE "A*"'),
            (2, 'Q_C', 'IN_LINK = "A"'),
            (3, 'Q_A', 'IN_LINK = "C"'),
            (4, 'Q_C', 'IN_LINK = "B" AND MESSAGE LIKE "*35=D"')
        ]
        for r in rules:
            db.session.add(DbRoutingRules(
                rule_order=r[0],
                queue_name=r[1],
                rule=r[2]
            ))

        db.session.commit()

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

if __name__ == '__main__':
    app.run(debug=True)
