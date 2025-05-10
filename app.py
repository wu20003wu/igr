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
    routing_targets = db.Column(db.Text)  # Store JSON array

# Datenbank erstellen und Beispieldaten einfügen
with app.app_context():
    db.create_all()
    
    # Nur bei erstmaliger Erstellung Beispieldaten einfügen
    if not Node.query.first():
        nodes = ['Router', 'A', 'B', 'C']
        for n in nodes:
            db.session.add(Node(id=n))
        
        edges = [
            ('A_to_Router', 'A', 'Router', 'A → Router', '["Router_to_B", "Router_to_C"]'),
            ('Router_to_B', 'Router', 'B', 'Router → B', '[]'),
            ('B_to_Router', 'B', 'Router', 'B → Router', '["Router_to_C"]'),
            ('Router_to_C', 'Router', 'C', 'Router → C', '[]'),
            ('C_to_Router', 'C', 'Router', 'C → Router', '["Router_to_A"]'),
            ('Router_to_A', 'Router', 'A', 'Router → A', '[]')
        ]
        
        for e in edges:
            db.session.add(Edge(
                id=e[0],
                source=e[1],
                target=e[2],
                label=e[3],
                routing_targets=e[4]
            ))
        
        db.session.commit()

@app.route('/')
def index():
    nodes = Node.query.all()
    edges = Edge.query.all()
    return render_template('index.html', nodes=nodes, edges=edges)

if __name__ == '__main__':
    app.run(debug=True) 