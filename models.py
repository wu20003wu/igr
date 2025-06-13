# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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

def insert_sample_data():
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