import pytest
from flask import url_for
from flask_login import current_user
from application import create_app, db
from application.models import User
from unittest.mock import patch
from datetime import datetime
import pytz


@pytest.fixture
def app():
    """Create a test Flask app with testing configuration."""
    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Provide a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Provide a test CLI runner for the Flask app."""
    return app.test_cli_runner()


@pytest.fixture
def authenticated_user(app, client):
    """Create and log in a test user."""
    with app.app_context():
        user = User(
            username="testuser",
            email="testuser@example.com",
            active=True
        )
        user.set_password("TestPassword123!")
        db.session.add(user)
        db.session.commit()
        client.post(url_for("auth.login"), data={
            "username": "testuser",
            "password": "TestPassword123!"
        }, follow_redirects=True)
        yield user


def test_index_route(client):
    """Test the main index route."""
    response = client.get(url_for("main.index"))
    assert response.status_code == 200
    assert b"Where Practical Learning Meets Knowledge and Confidence" in response.data
    assert b"We are committed to providing a transformative education experience" in response.data


def test_auth_login_route_get(client):
    """Test the login route (GET request)."""
    response = client.get(url_for("auth.login"))
    assert response.status_code == 200
    assert b"Login" in response.data
    assert b"Username" in response.data
    assert b"Password" in response.data


def test_auth_login_route_post_valid(client, app):
    """Test the login route with valid credentials (POST request)."""
    with app.app_context():
        user = User(
            username="validuser",
            email="validuser@example.com",
            active=True
        )
        user.set_password("ValidPass123!")
        db.session.add(user)
        db.session.commit()

    response = client.post(url_for("auth.login"), data={
        "username": "validuser",
        "password": "ValidPass123!"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Login successful" in response.data
    with client.session_transaction() as session:
        assert "_user_id" in session


def test_auth_login_route_post_invalid(client):
    """Test the login route with invalid credentials (POST request)."""
    response = client.post(url_for("auth.login"), data={
        "username": "nonexistent",
        "password": "WrongPass123!"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_auth_logout_route(authenticated_user, client):
    """Test the logout route."""
    response = client.get(url_for("auth.logout"), follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out" in response.data
    with client.session_transaction() as session:
        assert "_user_id" not in session
    assert not current_user.is_authenticated


def test_admin_route_unauthenticated(client):
    """Test access to admin route without authentication."""
    response = client.get(url_for("admin.index"), follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data
    assert b"Please log in to access this page" in response.data


def test_admin_route_authenticated(authenticated_user, client):
    """Test access to admin route with authentication."""
    response = client.get(url_for("admin.index"))
    assert response.status_code == 200
    assert b"Admin Dashboard" in response.data


def test_student_route_unauthenticated(client):
    """Test access to student route without authentication."""
    response = client.get(url_for("student.index"), follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data
    assert b"Please log in to access this page" in response.data


def test_teacher_route_unauthenticated(client):
    """Test access to teacher route without authentication."""
    response = client.get(url_for("teacher.index"), follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data
    assert b"Please log in to access this page" in response.data


def test_404_error(client):
    """Test the 404 error page."""
    response = client.get("/nonexistent-route")
    assert response.status_code == 404
    assert b"Page Not Found" in response.data


def test_403_error(client):
    """Test the 403 error page."""
    response = client.get(url_for("admin.index"))  # Assuming admin requires specific role
    assert response.status_code == 403
    assert b"Forbidden" in response.data


def test_csrf_error(client, app):
    """Test the CSRF error handling."""
    with app.app_context():
        # Disable CSRF for this test to simulate a missing token
        app.config["WTF_CSRF_ENABLED"] = False
        response = client.post(url_for("auth.login"), data={
            "username": "testuser",
            "password": "TestPass123!"
        })
        app.config["WTF_CSRF_ENABLED"] = True
        assert response.status_code == 403
        assert b"The form submission has expired" in response.data


@patch("application.__init__.db.session.execute")
def test_database_failure(mock_execute, client, app):
    """Test handling of database connection failure."""
    from sqlalchemy.exc import OperationalError
    mock_execute.side_effect = OperationalError("Database connection failed", None, None)
    with app.app_context():
        response = client.get(url_for("main.index"))
        assert response.status_code == 500
        assert b"Server Error" in response.data


def test_timezone_handling(client):
    """Test that the application uses Nigeria timezone (WAT, UTC+1)."""
    response = client.get(url_for("main.index"))
    assert response.status_code == 200
    nigeria_tz = pytz.timezone("Africa/Lagos")
    current_time = datetime.now(nigeria_tz).strftime("%d %B %Y")
    assert current_time.encode() in response.data


def test_session_security(client, authenticated_user):
    """Test session security settings."""
    response = client.get(url_for("main.index"))
    assert response.status_code == 200
    assert "session" in response.headers["Set-Cookie"]
    assert "HttpOnly" in response.headers["Set-Cookie"]
    assert "SameSite=Lax" in response.headers["Set-Cookie"]


if __name__ == "__main__":
    pytest.main(["-v"])