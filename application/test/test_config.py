import pytest
import os
import logging
from application import create_app

# Configure logging for better debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def app():
    """Create a test Flask app with testing configuration."""
    os.environ["FLASK_ENV"] = "testing"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DB_NAME"] = ":memory:"

    app = create_app(config_name="testing")
    logger.debug("Test app created with testing configuration")
    yield app

@pytest.fixture
def client(app):
    """Provide a test client for the Flask app."""
    return app.test_client()

def test_app_config(app):
    """Test that the app configuration is set correctly for testing."""
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert app.config["WTF_CSRF_ENABLED"] is False
    assert app.config["SECRET_KEY"] == "test-secret-key"
    logger.debug("App configuration test passed")