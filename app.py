from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import re, os
import cx_Oracle
from models import db, FixdConfig, MqdConfig, DbQueueAssign, DbRoutingRules, DbMsg, insert_sample_data
from datetime import datetime, timedelta
from sqlalchemy import func
from admin_auth import admin_required, check_credentials, is_admin

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


@app.route('/')
def index():
    fixd_nodes = FixdConfig.query.all()
    mqd_nodes = MqdConfig.query.all()

    nodes = [
        *[{'link_name': n.link_name} for n in fixd_nodes],
        *[{'link_name': n.link_name} for n in mqd_nodes],
        {'link_name': 'hold'},
        {'link_name': '$log'}
    ]

    # Hardcoded queue assignments MUST BE DEFINED HERE
    HARDCODED_QUEUES = {
        'hold': 'hold',
        '$log': '$log'
    }

    router_links = [n['link_name'] for n in nodes if n['link_name'] != 'Router']

    edges = []

    for link in router_links:
        edges.append({
            'id': f'{link}_to_Router',
            'source': link,
            'target': 'Router',
        })
        edges.append({
            'id': f'Router_to_{link}',
            'source': 'Router',
            'target': link,
        })

    routing_rules = {}
    reverse_routing_rules = {}

    for rule in DbRoutingRules.query.all():
        # Alle IN_LINKs finden (auch bei OR-Kombinationen)
        link_patterns = re.findall(r'IN_LINK\s+(?:=|LIKE)\s*"([^"]+)"', rule.rule)

        queue_name = rule.queue_name
        
        # Check for hardcoded queues first
        if queue_name in HARDCODED_QUEUES.values():
            link_name = [k for k,v in HARDCODED_QUEUES.items() if v == queue_name][0]
        else:
            queue_assignment = DbQueueAssign.query.filter_by(queue_name=queue_name).first()
            if not queue_assignment:
                continue
            link_name = queue_assignment.link_name

        for pattern in link_patterns:
            sql_pattern = pattern.replace('*', '%')
            is_wildcard = '%' in sql_pattern

            # Include both FixdConfig and MqdConfig in the query
            if is_wildcard:
                matching_fixd = FixdConfig.query.filter(FixdConfig.link_name.like(sql_pattern)).all()
                matching_mqd = MqdConfig.query.filter(MqdConfig.link_name.like(sql_pattern)).all()
                matching_links = matching_fixd + matching_mqd
            else:
                matching_fixd = FixdConfig.query.filter_by(link_name=sql_pattern).all()
                matching_mqd = MqdConfig.query.filter_by(link_name=sql_pattern).all()
                matching_links = matching_fixd + matching_mqd

            for link in matching_links:
                # Use correct source and target mapping
                source_link = link.link_name
                target_link = link_name  # From queue assignment

                if source_link not in routing_rules:
                    routing_rules[source_link] = []
                routing_rules[source_link].append({
                    'target': target_link,
                    'order': rule.rule_order,
                    'rule': rule.rule
                })

                # Reverse-Mapping with order
                if target_link not in reverse_routing_rules:
                    reverse_routing_rules[target_link] = []
                reverse_routing_rules[target_link].append({
                    'source': source_link,
                    'order': rule.rule_order,
                    'rule': rule.rule
                })

    all_rules = DbRoutingRules.query.order_by(DbRoutingRules.rule_order).all()

    return render_template('index.html',
                           nodes=nodes,
                           edges=edges,
                           routing_rules=routing_rules,
                           reverse_routing_rules=reverse_routing_rules,
                           all_rules=all_rules)


@app.route('/igs')
def igs_page():
    return render_template('igs.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if is_admin():
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username') or ''
        password = request.form.get('password') or ''
        if check_credentials(username, password):
            session.clear()
            session['is_admin'] = True
            session.permanent = True
            flash('Logged in as admin.', 'info')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password.', 'error')

    return render_template('admin_login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin():
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')


@app.route('/admin/logout', methods=['GET', 'POST'])
def admin_logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/admin/ping')
@admin_required
def admin_ping():
    """Example admin-only endpoint — pattern for future mutating routes."""
    return jsonify(ok=True, admin=True)


@app.route('/admin/clear-message', methods=['POST'])
@admin_required
def admin_clear_message():
    """Authorize clearing the message field (UI clears only after this succeeds)."""
    return jsonify(ok=True)


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


@app.route('/api/message_stats')
def message_stats():
    total_msgs = db.session.query(func.count(DbMsg.SEQ_NR)).scalar()
    pending_msgs = DbMsg.query.filter(DbMsg.out_link.is_(None)).count()

    completed_msgs = DbMsg.query.filter(DbMsg.out_time.isnot(None)).all()
    if completed_msgs:
        total_processing_time = sum([(msg.out_time - msg.in_time).total_seconds() for msg in completed_msgs if msg.in_time and msg.out_time])
        avg_processing_time = total_processing_time / len(completed_msgs) if len(completed_msgs) > 0 else 0
    else:
        avg_processing_time = 0

    return jsonify({
        'total_messages': total_msgs,
        'pending_messages': pending_msgs,
        'avg_processing_time_seconds': round(avg_processing_time, 2)
    })


@app.route('/api/link_stats')
def link_stats():
    all_links_with_modes = db.session.query(FixdConfig.link_name, FixdConfig.TEST_MODE).all()
    link_to_mode_map = dict(all_links_with_modes)

    incoming_stats = dict(db.session.query(
        DbMsg.in_link,
        func.count(DbMsg.in_link)
    ).group_by(DbMsg.in_link).all())

    outgoing_stats = dict(db.session.query(
        DbMsg.out_link,
        func.count(DbMsg.out_link)
    ).filter(DbMsg.out_link.isnot(None)).group_by(DbMsg.out_link).all())

    stats_data = []
    for link_name in sorted(link_to_mode_map.keys()):
        incoming = incoming_stats.get(link_name, 0)
        outgoing = outgoing_stats.get(link_name, 0)
        stats_data.append({
            'link_name': link_name,
            'test_mode': link_to_mode_map.get(link_name),
            'incoming': incoming,
            'outgoing': outgoing,
            'total': incoming + outgoing
        })

    stats_data.sort(key=lambda x: x['total'], reverse=True)
    return jsonify(stats_data)


@app.route('/api/pie_chart_data')
def pie_chart_data():
    """Provides data for the pie chart, showing message totals per link."""
    group_by = request.args.get('group_by')

    if group_by == 'test_mode':
        incoming_stats = dict(db.session.query(
            FixdConfig.TEST_MODE, func.count(DbMsg.SEQ_NR)
        ).join(FixdConfig, DbMsg.in_link == FixdConfig.link_name).group_by(FixdConfig.TEST_MODE).all())

        outgoing_stats = dict(db.session.query(
            FixdConfig.TEST_MODE, func.count(DbMsg.SEQ_NR)
        ).join(FixdConfig, DbMsg.out_link == FixdConfig.link_name).filter(DbMsg.out_link.isnot(None)).group_by(FixdConfig.TEST_MODE).all())

        all_test_modes = {mode for mode, in db.session.query(FixdConfig.TEST_MODE).distinct()}

        mode_totals = {}
        for mode in all_test_modes:
            total = incoming_stats.get(mode, 0) + outgoing_stats.get(mode, 0)
            if total > 0:
                mode_totals[f"Test Mode {mode}"] = total

        sorted_modes = sorted(mode_totals.items(), key=lambda item: item[1], reverse=True)
        labels = [item[0] for item in sorted_modes]
        data = [item[1] for item in sorted_modes]
        return jsonify({'labels': labels, 'data': data})

    incoming_stats = dict(db.session.query(
        DbMsg.in_link,
        func.count(DbMsg.in_link)
    ).group_by(DbMsg.in_link).all())

    outgoing_stats = dict(db.session.query(
        DbMsg.out_link,
        func.count(DbMsg.out_link)
    ).filter(DbMsg.out_link.isnot(None)).group_by(DbMsg.out_link).all())

    link_totals = {}
    all_link_names = {link.link_name for link in FixdConfig.query.all()}

    for link_name in all_link_names:
        total = incoming_stats.get(link_name, 0) + outgoing_stats.get(link_name, 0)
        if total > 0:
            link_totals[link_name] = total

    sorted_links = sorted(link_totals.items(), key=lambda item: item[1], reverse=True)
    labels = [item[0] for item in sorted_links]
    data = [item[1] for item in sorted_links]
    return jsonify({'labels': labels, 'data': data})


def _message_like_pattern(raw):
    """Convert user/routing-style patterns (*wildcard) to SQL LIKE."""
    if not raw:
        return None
    pattern = raw.replace('*', '%')
    if '%' not in pattern:
        pattern = f'%{pattern}%'
    return pattern


@app.route('/api/messages')
def get_messages():
    try:
        limit = int(request.args.get('limit', 10))
    except (ValueError, TypeError):
        limit = 10

    limit = min(limit, 100)
    in_link = request.args.get('in_link') or request.args.get('link_name')
    out_link = request.args.get('out_link')
    message_like = _message_like_pattern(request.args.get('message_like'))

    query = DbMsg.query
    if in_link:
        query = query.filter(DbMsg.in_link == in_link)
    if out_link:
        query = query.filter(DbMsg.out_link == out_link)
    if message_like:
        query = query.filter(DbMsg.fix_msg.like(message_like))

    messages = query.order_by(DbMsg.in_time.desc()).limit(limit).all()

    output = []
    for msg in messages:
        output.append({
            'seq_nr': msg.SEQ_NR,
            'msg_src': msg.msg_src,
            'in_link': msg.in_link,
            'in_time': msg.in_time.strftime('%Y-%m-%d %H:%M:%S') if msg.in_time else None,
            'out_link': msg.out_link,
            'out_time': msg.out_time.strftime('%Y-%m-%d %H:%M:%S') if msg.out_time else None,
            'fix_msg': msg.fix_msg,
        })

    return jsonify(output)


def extract_tag_value(fix_string, tag):
    """Extracts the value of a given tag from a FIX string."""
    pattern = f'(?:^|\\|){tag}=([^|]+)'
    match = re.search(pattern, fix_string)
    if match:
        return match.group(1)
    return None


@app.route('/api/grouped_stats')
def grouped_stats():
    """Provides message stats grouped by a specified FIX tag, optionally filtered by link/LIKE."""
    group_by_tag = request.args.get('group_by_tag', '35')
    in_link = request.args.get('in_link') or request.args.get('link_name')
    out_link = request.args.get('out_link')
    message_like = _message_like_pattern(request.args.get('message_like'))

    query = DbMsg.query
    if in_link:
        query = query.filter(DbMsg.in_link == in_link)
    if out_link:
        query = query.filter(DbMsg.out_link == out_link)
    if message_like:
        query = query.filter(DbMsg.fix_msg.like(message_like))

    messages = query.all()

    stats = {}
    for msg in messages:
        if msg.fix_msg:
            value = extract_tag_value(msg.fix_msg, group_by_tag)
            if value:
                stats[value] = stats.get(value, 0) + 1

    sorted_stats = sorted(stats.items(), key=lambda item: item[1], reverse=True)
    labels = [item[0] for item in sorted_stats]
    data = [item[1] for item in sorted_stats]
    return jsonify({'labels': labels, 'data': data})


if __name__ == '__main__':
    app.run(debug=True, port=10010, host='0.0.0.0') # eng/st: 10010, prod:10001
