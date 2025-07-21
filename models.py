# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Sequence, DateTime
from flask import Flask
from datetime import datetime, timedelta
import random
import re

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')

db = SQLAlchemy()

if app.config['SQLALCHEMY_DATABASE_URI'].startswith('oracle'):
    from sqlalchemy.dialects.oracle import TIMESTAMP
    timestamp_type = TIMESTAMP(timezone=False) #, precision=6)
else:
    timestamp_type = DateTime()

# früher Node
class FixdConfig(db.Model):
    __tablename__ = 'FIXD_CONFIG'
    link_name = db.Column(db.String(50), primary_key=True)

class MqdConfig(db.Model):  # Neue Tabelle hinzugefügt
    __tablename__ = 'MQD_CONFIG'
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

def insert_sample_data():
    if not FixdConfig.query.first():
        links = ['A', 'B', 'C', 'AB']
        for l in links:
            db.session.add(FixdConfig(link_name=l))
        
        mqds = ['M0', 'M1']
        # Add MQD_CONFIG entries
        for mqd in mqds:
            db.session.add(MqdConfig(link_name=mqd))
        
        db.session.commit()  # Commit both FixdConfig and MqdConfig

        for link in links:
            db.session.add(DbQueueAssign(
                link_name=link,
                queue_name=f'Q_{link}'
            ))

        for mqd in mqds:
            db.session.add(DbQueueAssign(
                link_name=mqd,
                queue_name=f'Q_{mqd}'
            ))

        rules = [
            (1, 'Q_B', 'IN_LINK = "A" OR IN_LINK LIKE "A*"'),
            (2, 'Q_C', 'IN_LINK = "A" AND MESSAGE UNLIKE "*35=D*"'),
            (3, 'Q_A', 'IN_LINK = "C" AND MESSAGE UNLIKE "*ERROR*"'),
            (4, 'Q_C', 'IN_LINK = "B" AND MESSAGE LIKE "*35=D*"'),
            (5, 'Q_M0', 'IN_LINK = "A"'),
            (6, 'Q_M1', 'IN_LINK = "B"'),
            (7, 'hold', 'IN_LINK = "C"'),
            (8, '$log', 'IN_LINK = "B"'),
            (9, 'Q_A', 'IN_LINK = "M0"'),
            (10, 'Q_B', 'IN_LINK = "M1"')
        ]
        for r in rules:
            db.session.add(DbRoutingRules(
                rule_order=r[0],
                queue_name=r[1],
                rule=r[2]
            ))

        db.session.commit()
