from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///network.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Node(db.Model):
    id = db.Column(db.String(50), primary_key=True)

class Edge(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    source = db.Column(db.String(50))
    target = db.Column(db.String(50))
    label = db.Column(db.String(50))

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rule_order = db.Column(db.Integer)
    queue_name = db.Column(db.String(50))
    rule = db.Column(db.String(100))

# Datenbank erstellen und Beispieldaten einfügen
with app.app_context():
    db.create_all()
    
    # Nur bei erstmaliger Erstellung Beispieldaten einfügen
    if not Node.query.first():
        nodes = ['Router', 'A', 'B', 'C']
        for n in nodes:
            db.session.add(Node(id=n))
        
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
        
        # Add sample rules
        rules = [
            (1, 'B', 'IN_LINK = "A"'),
            (2, 'C', 'IN_LINK = "A"'),
            (3, 'A', 'IN_LINK = "C"'),
            (4, 'C', 'IN_LINK = "B"')
        ]
        
        for r in rules:
            db.session.add(Rule(
                rule_order=r[0],
                queue_name=r[1],
                rule=r[2]
            ))
        
        db.session.commit()

@app.route('/')
def index():
    nodes = Node.query.all()
    edges = Edge.query.all()
    rules = Rule.query.all()
    
    # Create a dictionary mapping source nodes to their target queues
    routing_rules = {}
    for rule in rules:
        # Extract the IN_LINK value from the rule condition
        import re
        match = re.search(r'IN_LINK\s*=\s*"([^"]+)"', rule.rule)
        if match:
            in_link = match.group(1)
            if in_link not in routing_rules:
                routing_rules[in_link] = []
            routing_rules[in_link].append(rule.queue_name)
    
    return render_template('index.html', 
                         nodes=nodes, 
                         edges=edges, 
                         routing_rules=routing_rules)

if __name__ == '__main__':
    app.run(debug=True) 