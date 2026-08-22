from flask import Flask
from flask_cors import CORS
import os
from datetime import timedelta

from models import db, FixdConfig, insert_sample_data
from admin_auth import is_admin
from routes import register_blueprints

app = Flask(__name__, instance_relative_config=True)
CORS(app)  # CORS aktivieren, um Anfragen vom Frontend zu erlauben
app.config.from_pyfile('config.py')
# Configure the app's database URI using an environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///igt.db')

# Admin auth / session (never hardcode secrets)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or app.config.get('SECRET_KEY')
app.config['ADMIN_USERNAME'] = os.environ.get('ADMIN_USERNAME') or app.config.get('ADMIN_USERNAME', '')
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD') or app.config.get('ADMIN_PASSWORD', '')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=1)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # sliding: 1 min inactivity

db.init_app(app)

# Stelle sicher, dass der instance-Ordner existiert
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Datenbanktabellen und Testdaten erstellen (innerhalb des App-Kontexts)
# (ACHTUNG: Oracle benötigt DBA-Rechte für CREATE TABLESPACE)
with app.app_context():
    db.create_all()
    insert_sample_data()


@app.context_processor
def inject_admin_status():
    return {'is_admin': is_admin()}


register_blueprints(app)


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


if __name__ == '__main__':
    app.run(debug=True, port=10010, host='0.0.0.0') # eng/st: 10010, prod:10001
