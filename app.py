from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///igt.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# früher Node
class FixdConfig(db.Model):
    __tablename__ = 'FIXD_CONFIG'
    link_name = db.Column(db.String(50), primary_key=True)

class Edge(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    source = db.Column(db.String(50))
    target = db.Column(db.String(50))
    label = db.Column(db.String(50))

# früher Rule
class DbRoutingRules(db.Model):
    __tablename__ = 'DB_ROUTING_RULES'
    id = db.Column(db.Integer, primary_key=True)
    rule_order = db.Column(db.Integer)
    queue_name = db.Column(db.String(50), db.ForeignKey('DB_QUEUE_ASSIGN.queue_name'))
    rule = db.Column(db.String(100))
    queue_assignment = db.relationship('DbQueueAssign', backref='routing_rules')

#neu: node hat cash, queue = warteschlange, jeder Link hat eine Warteschlange
class DbQueueAssign(db.Model):
    __tablename__ = 'DB_QUEUE_ASSIGN'
    link_name = db.Column(db.String(50), db.ForeignKey('FIXD_CONFIG.link_name'), primary_key=True)
    queue_name = db.Column(db.String(50), unique=True)

# Datenbank erstellen und Beispieldaten einfügen
with app.app_context():
    db.create_all()
    
    # Nur bei erstmaliger Erstellung Beispieldaten einfügen
    if not FixdConfig.query.first():
        links = [ 'Router', 'A', 'B', 'C']
        for l in links:
            db.session.add(FixdConfig(link_name=l))
        
        # Add queue assignments (1:1 mapping)
        for link in links:
            db.session.add(DbQueueAssign(
                link_name=link,
                queue_name=f'Q_{link}'
            ))
        
        edges = [
            ('A_to_Router', 'A', 'Router', 'A → Router'),
            ('Router_to_B', 'Router', 'B', 'Router → B'),
            ('B_to_Router', 'B', 'Router', 'B → Router'),
            ('Router_to_C', 'Router', 'C', 'Router → C'),
            ('C_to_Router', 'C', 'Router', 'C → Router'),
            ('Router_to_A', 'Router', 'A', 'Router → A')
        ]
        for e in edges:
            db.session.add(Edge(
                id=e[0],
                source=e[1],
                target=e[2],
                label=e[3]
            ))
        
        # Updated rule references to use actual queue names from DB_QUEUE_ASSIGN
        rules = [
            (1, 'Q_B', 'IN_LINK = "A"'),
            (2, 'Q_C', 'IN_LINK = "A"'),
            (3, 'Q_A', 'IN_LINK = "C"'),
            (4, 'Q_C', 'IN_LINK = "B"')
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
    edges = Edge.query.all()
    rules = DbRoutingRules.query.all()
    
    # Create a dictionary mapping source nodes to their target links
    routing_rules = {}
    for rule in rules:
        # Extract the IN_LINK value from the rule condition
        import re
        match = re.search(r'IN_LINK\s*=\s*"([^"]+)"', rule.rule)
        if match:
            in_link = match.group(1)
            
            # Get the actual link name for the queue
            queue_assignment = DbQueueAssign.query.filter_by(queue_name=rule.queue_name).first()
            if queue_assignment:
                if in_link not in routing_rules:
                    routing_rules[in_link] = []
                routing_rules[in_link].append(queue_assignment.link_name)

    return render_template('index.html', 
                         nodes=nodes, 
                         edges=edges, 
                         routing_rules=routing_rules)

if __name__ == '__main__':
    app.run(debug=True) 