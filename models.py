# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Sequence, DateTime
from datetime import datetime
from flask import Flask
from datetime import datetime, timedelta
import random
import re

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///igt.db'
#app.config.from_object(Config) 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()

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
    # id = db.Column(db.Integer, db.Sequence('routing_rules_seq'), primary_key=True)
    rule_order = db.Column(db.Integer, primary_key=True)
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

def insert_sample_data():
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
