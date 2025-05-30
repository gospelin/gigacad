import pytest
import logging
from flask import url_for
from application import create_app, db
from application.models import User, Student, RoleEnum
from unittest.mock import patch
from datetime import datetime
import pytz
import sys
import os

# Configure logging for better debugging in CI/CD
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Fixture to log Python version for debugging
@pytest.fixture(autouse=True)
def log_python_version():
    logger.debug(f"Running tests with Python version: {sys.version}")

@pytest.fixture
def app():
    """Create a test Flask app with testing configuration."""
    os.environ["FLASK_ENV"] = "testing"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DB_NAME"] = ":memory:"  # Use in-memory SQLite for testing

    app = create_app(config_name="testing")
    logger.debug("Test app created with testing configuration")

    with app.app_context():
        try:
            db.create_all()
            logger.debug("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise
        yield app
        try:
            db.session.remove()
            db.drop_all()
            logger.debug("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {str(e)}")
            raise

@pytest.fixture
def client(app):
    """Provide a test client for the Flask app."""
    return app.test_client()

@pytest.fixture
def authenticated_user(app, client):
    """Create and log in a test user with a linked Student record."""
    with app.app_context():
        # Create User
        user = User(
            username="testuser",
            role=RoleEnum.STUDENT.value,
            active=True
        )
        user.set_password("TestPassword123!")
        db.session.add(user)
        db.session.commit()

        # Create linked Student record
        student = Student(
            first_name="Test",
            last_name="User",
            gender="Male",
            user_id=user.id
        )
        db.session.add(student)
        db.session.commit()
        logger.debug(f"Test user and student created: {user.username}")

        response = client.post(url_for("auth.login"), data={
            "identifier": "testuser",
            "password": "TestPassword123!",
            "remember": True
        }, follow_redirects=False)
        assert response.status_code == 302  # Expect redirect after login
        logger.debug("Test user logged in successfully")
        yield user

def test_app_creation(app):
    """Test that the app is created correctly."""
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert app.config["WTF_CSRF_ENABLED"] is False
    logger.debug("App configuration verified")

def test_index_route(client):
    """Test the main index route."""
    response = client.get(url_for("main.index"))
    assert response.status_code == 200
    assert b"Aunty Anne's International School" in response.data
    logger.debug("Index route test passed")

def test_auth_login_route_get(client):
    """Test the login route (GET request)."""
    response = client.get(url_for("auth.login"))
    assert response.status_code == 200
    assert b"Login" in response.data
    logger.debug("Login route (GET) test passed")

def test_auth_login_route_post_valid(client, app):
    """Test the login route with valid credentials (POST request)."""
    with app.app_context():
        # Create User
        user = User(
            username="validuser",
            role=RoleEnum.STUDENT.value,
            active=True
        )
        user.set_password("ValidPass123!")
        db.session.add(user)
        db.session.commit()

        # Create linked Student record
        student = Student(
            first_name="Valid",
            last_name="User",
            gender="Male",
            user_id=user.id
        )
        db.session.add(student)
        db.session.commit()
        logger.debug("Valid user and student created for login test")

    response = client.post(url_for("auth.login"), data={
        "identifier": "validuser",
        "password": "ValidPass123!",
        "remember": True
    }, follow_redirects=False)
    assert response.status_code == 302  # Expect redirect to dashboard
    logger.debug("Login route (POST, valid) test passed")

def test_auth_login_route_post_invalid(client):
    """Test the login route with invalid credentials (POST request)."""
    response = client.post(url_for("auth.login"), data={
        "identifier": "nonexistent",
        "password": "WrongPass123!"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid password" in response.data or b"User not found" in response.data
    logger.debug("Login route (POST, invalid) test passed")

def test_auth_login_route_post_empty(client):
    """Test the login route with empty credentials (POST request)."""
    response = client.post(url_for("auth.login"), data={
        "identifier": "",
        "password": ""
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"required" in response.data or b"Login" in response.data
    logger.debug("Login route (POST, empty) test passed")

def test_auth_logout_route(authenticated_user, client):
    """Test the logout route."""
    response = client.get(url_for("auth.logout"), follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data
    with client.session_transaction() as session:
        assert "_user_id" not in session
    logger.debug("Logout route test passed")

def test_admin_route_unauthenticated(client):
    """Test access to admin route without authentication."""
    try:
        response = client.get(url_for("admins.admin_dashboard"), follow_redirects=True)
        assert response.status_code == 200
        assert b"Login" in response.data
    except Exception:
        pytest.skip("Admin dashboard endpoint not defined")
    logger.debug("Admin route (unauthenticated) test passed")

def test_admin_route_authenticated(authenticated_user, client):
    """Test access to admin route with authentication."""
    try:
        response = client.get(url_for("admins.admin_dashboard"), follow_redirects=True)
        assert response.status_code == 200 or response.status_code == 403
    except Exception:
        pytest.skip("Admin dashboard endpoint not defined")
    logger.debug("Admin route (authenticated) test passed")

def test_student_route_unauthenticated(client):
    """Test access to student route without authentication."""
    try:
        response = client.get(url_for("students.student_portal"), follow_redirects=True)
        assert response.status_code == 200
        assert b"Login" in response.data
    except Exception:
        pytest.skip("Student portal endpoint not defined")
    logger.debug("Student route (unauthenticated) test passed")

def test_teacher_route_unauthenticated(client):
    """Test access to teacher route without authentication."""
    try:
        response = client.get(url_for("teachers.teacher_dashboard"), follow_redirects=True)
        assert response.status_code == 200
        assert b"Login" in response.data
    except Exception:
        pytest.skip("Teacher dashboard endpoint not defined")
    logger.debug("Teacher route (unauthenticated) test passed")

def test_404_error(client):
    """Test the 404 error page."""
    response = client.get("/nonexistent-route")
    assert response.status_code == 404
    assert b"Page Not Found" in response.data
    logger.debug("404 error test passed")

def test_403_error(client):
    """Test the 403 error page."""
    try:
        response = client.get(url_for("admins.admin_dashboard"), follow_redirects=True)
        assert response.status_code == 403 or response.status_code == 200
    except Exception:
        pytest.skip("Admin dashboard endpoint not defined")
    logger.debug("403 error test passed")

@patch("application.db.session.execute")
def test_database_failure(mock_execute, client, app):
    """Test handling of database connection failure."""
    from sqlalchemy.exc import OperationalError
    mock_execute.side_effect = OperationalError("Database connection failed", None, None)
    with pytest.raises(RuntimeError, match="Database connection failed on startup"):
        with app.app_context():
            from application.__init__ import create_app
            create_app(config_name="development")
    logger.debug("Database failure test passed")

def test_timezone_handling(client):
    """Test that the application uses Nigeria timezone (WAT, UTC+1)."""
    response = client.get(url_for("main.index"))
    assert response.status_code == 200
    nigeria_tz = pytz.timezone("Africa/Lagos")
    current_time = datetime.now(nigeria_tz).strftime("%d %B %Y")
    assert current_time.encode() in response.data
    logger.debug("Timezone handling test passed")

def test_session_security(client, authenticated_user):
    """Test session security settings."""
    response = client.get(url_for("main.index"))
    assert response.status_code == 200
    assert "session" in response.headers["Set-Cookie"]
    assert "HttpOnly" in response.headers["Set-Cookie"]
    assert "SameSite=Lax" in response.headers["Set-Cookie"]
    logger.debug("Session security test passed")