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
        links = ['Router', 'A', 'B', 'C', 'AB']
        for l in links:
            db.session.add(FixdConfig(link_name=l))
        
        # Add queue assignments (1:1 mapping)
        for link in links:
            db.session.add(DbQueueAssign(
                link_name=link,
                queue_name=f'Q_{link}'
            ))
        
        # Updated rule references to use actual queue names from DB_QUEUE_ASSIGN
        rules = [
            (1, 'Q_B', 'IN_LINK = "A" OR IN_LINK LIKE "A*"'),
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
    
    # Dynamische Edge-Generierung
    edges = []
    router_links = [n.link_name for n in nodes if n.link_name != 'Router']
    
    for link in router_links:
        # Edge TO Router
        edges.append({
            'id': f'{link}_to_Router',
            'source': link,
            'target': 'Router',
            'label': f'{link} → Router'
        })
        
        # Edge FROM Router
        edges.append({
            'id': f'Router_to_{link}',
            'source': 'Router',
            'target': link,
            'label': f'Router → {link}'
        })
    
    # Manuelle Edges hinzufügen (falls benötigt)
    # edges.append({'id': 'custom', 'source': 'A', 'target': 'B', 'label': 'Custom'})

    # Create a dictionary mapping source nodes to their target links
    routing_rules = {}
    for rule in DbRoutingRules.query.all():
        # Updated regex to handle both equality and LIKE conditions
        import re
        match = re.search(r'IN_LINK\s+(?:=|LIKE)\s*"([^*"]+)\*?"', rule.rule)
        if match:
            base_link = match.group(1)
            
            # Determine if it's a wildcard pattern
            is_wildcard = '*' in rule.rule
            
            # Get the actual link name for the queue
            queue_assignment = DbQueueAssign.query.filter_by(queue_name=rule.queue_name).first()
            if queue_assignment:
                # Find all links that match the pattern
                if is_wildcard:
                    matching_links = FixdConfig.query.filter(
                        FixdConfig.link_name.startswith(base_link)
                    ).all()
                else:
                    matching_links = FixdConfig.query.filter_by(link_name=base_link).all()
                
                # Add all matching links to routing rules
                for link in matching_links:
                    if link.link_name not in routing_rules:
                        routing_rules[link.link_name] = []
                    routing_rules[link.link_name].append(queue_assignment.link_name)

    return render_template('index.html', 
                         nodes=nodes, 
                         edges=edges, 
                         routing_rules=routing_rules)

if __name__ == '__main__':
    app.run(debug=True) 