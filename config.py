import os
from dotenv import load_dotenv

# project_folder = os.path.expanduser("C:/Users/GIGO/Documents/Flask_Development/AAIS")
# load_dotenv(os.path.join(project_folder, ".env"))


# class Config(object):
#    SECRET_KEY = os.environ.get("SECRET_KEY")
#    # or "your_secret_key_here"

#    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
#    SQLALCHEMY_TRACK_MODIFICATIONS = False

#    WTF_CSRF_ENABLED = True

# Load environment variables from a .env file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "default_secret_key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///" + os.path.join(basedir, "school_database.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///"  # Use an in-memory database for tests


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "app.db")
    )


# Map the configuration classes to environment names
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": Config,
}
