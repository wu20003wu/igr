"""Focused tests for single-admin username/password authentication."""
import pytest

from app import app


@pytest.fixture
def client():
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD="secret",
    )
    with app.test_client() as test_client:
        yield test_client


def test_unauthenticated_cannot_access_admin_ping(client):
    response = client.get("/admin/ping")
    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_valid_login_creates_admin_session(client):
    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")

    with client.session_transaction() as sess:
        assert sess.get("is_admin") is True

    dashboard = client.get("/admin/dashboard")
    assert dashboard.status_code == 200
    assert b"Admin Dashboard" in dashboard.data

    ping = client.get("/admin/ping")
    assert ping.status_code == 200
    assert ping.get_json() == {"ok": True, "admin": True}


def test_unauthenticated_cannot_access_dashboard(client):
    response = client.get("/admin/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/login")


def test_invalid_login_rejected(client):
    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "wrong"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data

    with client.session_transaction() as sess:
        assert not sess.get("is_admin")

    assert client.get("/admin/ping").status_code == 401


def test_unauthenticated_cannot_clear_message(client):
    response = client.post("/admin/clear-message")
    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_admin_can_clear_message(client):
    client.post("/admin/login", data={"username": "admin", "password": "secret"})
    response = client.post("/admin/clear-message")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_logout_removes_admin_authentication(client):
    client.post("/admin/login", data={"username": "admin", "password": "secret"})
    assert client.get("/admin/ping").status_code == 200

    logout = client.get("/admin/logout")
    assert logout.status_code == 302

    with client.session_transaction() as sess:
        assert not sess.get("is_admin")

    assert client.get("/admin/ping").status_code == 401
    assert client.post("/admin/clear-message").status_code == 401
