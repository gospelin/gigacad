import os
from dotenv import load_dotenv

# Load environment variables from the .env file
basedir = os.getenv("BASEDIR", os.path.abspath(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base configuration."""

    # Secret key for security, retrieved from the .env file or a default value
    SECRET_KEY = os.environ.get("SECRET_KEY", "default_secret_key")

    # Retrieve database connection details from environment variables
    DB_USER = os.getenv("DB_USER", "your_mysql_username")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "your_mysql_password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "auntyan1_school_database")

    # Construct the MySQL connection string
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    )

    # To prevent SQLAlchemy from tracking modifications to objects, which uses extra memory
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Enable CSRF protection for Flask forms
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    """Development configuration."""

    # DEBUG = True
    DEBUG = False
    SQLALCHEMY_ECHO = False  # Enables SQL logging for debugging purposes


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    # Use an in-memory SQLite database for testing purposes
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SERVER_NAME = "auntyannesschools.com.ng"
    # SERVER_NAME = "176.74.18.130"
    # MySQL URI is already set in the base Config class and will be used here


# Map the configuration classes to environment names
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": Config,
}
