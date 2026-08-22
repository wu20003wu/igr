"""Shared fixtures for isolated SQLite app contexts."""
import pytest

from app import create_app
from models import db


@pytest.fixture
def app():
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test-secret-key",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "secret",
        }
    )
    yield application


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.remove()
