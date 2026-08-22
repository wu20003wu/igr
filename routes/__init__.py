"""Route blueprints package."""


def register_blueprints(app):
    from routes.admin import admin_bp
    from routes.main import main_bp
    from routes.messages import messages_bp
    from routes.stats import stats_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(stats_bp)
