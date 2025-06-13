from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import re
import cx_Oracle
from config import Config  # Neue Import-Zeile
from sqlalchemy import DateTime, Sequence
import random
from datetime import datetime, timedelta

app = Flask(__name__)
# Oracle-Verbindungsstring ersetzen
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///igt.db'
#app.config.from_object(Config) 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

if app.config['SQLALCHEMY_DATABASE_URI'].startswith('oracle'):
    from sqlalchemy.dialects.oracle import TIMESTAMP
    timestamp_type = TIMESTAMP(timezone=False, precision=6)
else:
    timestamp_type = DateTime()

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

# Neue Klasse für Real-Time Messages
class DbMsg(db.Model):
    __tablename__ = 'DB_MSG'
    SEQ_NR = db.Column(db.Integer, Sequence('msg_seq'), primary_key=True)
    msg_src = db.Column(db.String(50), nullable=True)
    in_link = db.Column(db.String(50), db.ForeignKey('FIXD_CONFIG.link_name'), nullable=True)
    in_time = db.Column(timestamp_type, nullable=True)
    out_link = db.Column(db.String(50), db.ForeignKey('FIXD_CONFIG.link_name'), nullable=True)
    out_time = db.Column(timestamp_type, nullable=True)
    
    # Explizite Angabe des ForeignKeys für die Relationship
    fixd_config = db.relationship('FixdConfig', foreign_keys=[in_link], backref='messages')

# Datenbank erstellen (ACHTUNG: Oracle benötigt DBA-Rechte für CREATE TABLESPACE)
with app.app_context():
    db.create_all()

    if not FixdConfig.query.first():
        links = ['A', 'B', 'C', 'AB']
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

        # Beispieldaten für DB_MSG generieren mit echten Routing-Regeln
        # Routing-Regeln aus der Datenbank laden
        routing_rules = {}
        for rule in DbRoutingRules.query.all():
            queue_assignment = DbQueueAssign.query.filter_by(queue_name=rule.queue_name).first()
            if not queue_assignment:
                continue
            
            # IN_LINKs aus der Regel extrahieren
            link_patterns = re.findall(r'IN_LINK\s+(?:=|LIKE)\s*"([^"]+)"', rule.rule)
            for pattern in link_patterns:
                sql_pattern = pattern.replace('*', '%')
                is_wildcard = '%' in sql_pattern
                
                # Passende Links finden
                if is_wildcard:
                    matching_links = FixdConfig.query.filter(FixdConfig.link_name.like(sql_pattern)).all()
                else:
                    matching_links = FixdConfig.query.filter_by(link_name=sql_pattern).all()
                
                for link in matching_links:
                    if link.link_name not in routing_rules:
                        routing_rules[link.link_name] = []
                    routing_rules[link.link_name].append(queue_assignment.link_name)

        # 10 Nachrichten in chronologischer Reihenfolge generieren
        base_time = datetime.now() - timedelta(hours=1)
        time_increment = timedelta(seconds=5)  # 5 Sekunden Abstand zwischen Nachrichten

        for i in range(10):
            # Zeitstempel berechnen
            in_time = base_time + (time_increment * i)
            
            # Realistisches Routing-Verhalten
            if i % 3 == 0:
                in_link = 'A'
                out_link = 'B' if i < 7 else None
            elif i % 3 == 1:
                in_link = 'B'
                out_link = 'C' if i < 8 else None
            else:
                in_link = 'C'
                out_link = 'A' if i < 9 else None

            # Out-Time berechnen wenn vorhanden
            out_time = None
            if out_link:
                processing_time = timedelta(seconds=random.uniform(0.1, 0.9))
                out_time = in_time + processing_time

            db.session.add(DbMsg(
                msg_src=f"System_{i+1}",
                in_link=in_link,
                in_time=in_time,
                out_link=out_link,
                out_time=out_time
            ))

        db.session.commit()

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

@app.route('/')
def index():
    edges = get_edges()
    nodes = FixdConfig.query.all()

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

@app.route('/messages')
def message_stats():
    start_time = request.args.get('start')
    interval_count = int(request.args.get('count', 1))
    
    try:
        start = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        try:
            start = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        except ValueError:
            return jsonify({'error': 'Ungültiges Zeitformat'}), 400

    # Berechne Endzeit für das aktuelle Intervall
    end_time = start + timedelta(seconds=5 * interval_count)
    
    stats = {}
    links = ['A', 'B', 'C', 'AB']
    
    for link in links:
        # Zähle alle Nachrichten seit Startzeit bis zum aktuellen Intervallende
        count = DbMsg.query.filter(
            DbMsg.in_link == link,
            DbMsg.in_time >= start,
            DbMsg.in_time <= end_time
        ).count()
        stats[link] = count

    return jsonify({
        'stats': stats,
        'time_window': end_time.strftime('%H:%M:%S')
    })

if __name__ == '__main__':
    app.run(debug=True)
