# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Sequence, DateTime
from datetime import datetime, timedelta
import random
import os

db = SQLAlchemy()

_database_uri = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///igt.db")
if _database_uri.startswith("oracle"):
    from sqlalchemy.dialects.oracle import TIMESTAMP

    timestamp_type = TIMESTAMP(timezone=False)  # , precision=6)
else:
    timestamp_type = DateTime()


# früher Node
class FixdConfig(db.Model):
    __tablename__ = "FIXD_CONFIG"
    link_name = db.Column(db.String(50), primary_key=True)
    TEST_MODE = db.Column(db.Integer, nullable=False, default=0)


class MqdConfig(db.Model):  # Neue Tabelle hinzugefügt
    __tablename__ = "MQD_CONFIG"
    link_name = db.Column(db.String(50), primary_key=True)


# früher Rule
class DbRoutingRules(db.Model):
    __tablename__ = "DB_ROUTING_RULES"
    # id = db.Column(db.Integer, db.Sequence('routing_rules_seq'), primary_key=True)
    rule_order = db.Column(db.Integer, primary_key=True)
    queue_name = db.Column(db.String(50), db.ForeignKey("DB_QUEUE_ASSIGN.queue_name"))
    rule = db.Column(db.String(100))
    queue_assignment = db.relationship("DbQueueAssign", backref="routing_rules")


# neu: node hat cash, queue = warteschlange, jeder Link hat eine Warteschlange
class DbQueueAssign(db.Model):
    __tablename__ = "DB_QUEUE_ASSIGN"
    link_name = db.Column(db.String(50), db.ForeignKey("FIXD_CONFIG.link_name"), primary_key=True)
    queue_name = db.Column(db.String(50), unique=True)


# Neue Klasse für Real-Time Messages
class DbMsg(db.Model):
    __tablename__ = "DB_MSG"
    SEQ_NR = db.Column(db.Integer, Sequence("msg_seq"), primary_key=True)
    msg_src = db.Column(db.String(50), nullable=True)
    in_link = db.Column(db.String(50), db.ForeignKey("FIXD_CONFIG.link_name"), nullable=True)
    in_time = db.Column(timestamp_type, nullable=True)
    out_link = db.Column(db.String(50), db.ForeignKey("FIXD_CONFIG.link_name"), nullable=True)
    out_time = db.Column(timestamp_type, nullable=True)
    fix_msg = db.Column(db.String(2048), nullable=True)

    # Relationships to FixdConfig
    in_link_relation = db.relationship(
        "FixdConfig", foreign_keys=[in_link], backref="incoming_messages"
    )
    out_link_relation = db.relationship(
        "FixdConfig", foreign_keys=[out_link], backref="outgoing_messages"
    )


def insert_sample_data():
    if not FixdConfig.query.first():
        fixd_links = ["A", "B", "C", "AB"]
        mqd_links = ["M0", "M1"]
        all_links = fixd_links + mqd_links

        for link in all_links:
            db.session.add(FixdConfig(link_name=link, TEST_MODE=random.randint(0, 3)))

        # Add MQD_CONFIG entries
        for mqd in mqd_links:
            db.session.add(MqdConfig(link_name=mqd))

        db.session.commit()

        for link in all_links:
            db.session.add(DbQueueAssign(link_name=link, queue_name=f"Q_{link}"))

        rules = [
            (1, "Q_B", 'IN_LINK = "A" OR IN_LINK LIKE "A*"'),
            (2, "Q_C", 'IN_LINK = "A" AND MESSAGE UNLIKE "*35=D*"'),
            (3, "Q_A", 'IN_LINK = "C" AND MESSAGE UNLIKE "*ERROR*"'),
            (4, "Q_C", 'IN_LINK = "B" AND MESSAGE LIKE "*35=D*"'),
            (5, "Q_M0", 'IN_LINK = "A"'),
            (6, "Q_M1", 'IN_LINK = "B"'),
            (7, "hold", 'IN_LINK = "C"'),
            (8, "$log", 'IN_LINK = "B"'),
            (9, "Q_A", 'IN_LINK = "M0"'),
            (10, "Q_B", 'IN_LINK = "M1"'),
        ]
        for r in rules:
            db.session.add(DbRoutingRules(rule_order=r[0], queue_name=r[1], rule=r[2]))

        db.session.commit()
        # 100 Nachrichten in chronologischer Reihenfolge generieren, mit diversifizierter Verteilung
        base_time = datetime.now() - timedelta(hours=1)

        all_link_names = [link.link_name for link in FixdConfig.query.all()]
        # Define weights to create a more diverse distribution of messages per link
        # 'A' and 'B' are high-traffic, 'C' and 'AB' medium, 'M0' and 'M1' low.
        link_weights = [0.3, 0.3, 0.15, 0.15, 0.05, 0.05]

        for i in range(100):  # Generate 100 messages
            # Increment time randomly to make it more realistic
            time_increment = timedelta(seconds=random.randint(1, 10))
            in_time = base_time + time_increment
            base_time = in_time  # Update base time for the next message

            # Choose in_link based on weights
            in_link = random.choices(all_link_names, weights=link_weights, k=1)[0]

            # Determine out_link, making sure it's not the same as in_link
            out_link = None
            out_time = None
            if random.random() > 0.2:  # 80% chance it has been routed
                possible_out_links = [l for l in all_link_names if l != in_link]
                # Also use weights for out_link selection for more realism
                possible_weights = [link_weights[all_link_names.index(l)] for l in possible_out_links]

                if possible_out_links:
                    out_link = random.choices(possible_out_links, weights=possible_weights, k=1)[0]
                    processing_time = timedelta(seconds=random.uniform(0.1, 1.5))
                    out_time = in_time + processing_time

            order_prefix = random.choice(["OMS", "ORS"])
            side = random.choice(["1", "2"])
            ord_type = random.choice(["1", "2"])
            symbol = random.choice(["EUR/USD", "AAPL", "MSFT"])
            client_id = random.choice(["CLIENT_A", "CLIENT_B", "CLIENT_C"])
            on_behalf_of = random.choice(["PBA", "PBB"])

            common_tags = (
                f"11={order_prefix}{i}|"
                f"54={side}|"
                f"40={ord_type}|"
                f"55={symbol}|"
                f"109={client_id}|"
                f"115={on_behalf_of}"
            )

            if random.random() < 0.5:
                # New Order Single
                fix_msg = f"8=FIX.4.2|9=123|35=D|49=SENDERCOMP|56=TARGETCOMP|34=1|52={in_time.strftime('%Y%m%d-%H:%M:%S')}|{common_tags}"
            else:
                # Execution Report for a trade
                exec_type = random.choice(["1", "2"])  # 1=Partial fill, 2=Fill
                fix_msg = f"8=FIX.4.2|9=123|35=8|49=SENDERCOMP|56=TARGETCOMP|34=1|52={in_time.strftime('%Y%m%d-%H:%M:%S')}|{common_tags}|150={exec_type}"

            db.session.add(
                DbMsg(
                    msg_src=f"System_{random.choice(['A', 'B', 'C'])}",  # Random source system
                    in_link=in_link,
                    in_time=in_time,
                    out_link=out_link,
                    out_time=out_time,
                    fix_msg=fix_msg,
                )
            )

        db.session.commit()
