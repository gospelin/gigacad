import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.WARNING)
config_logger = logging.getLogger(__name__)
sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
sqlalchemy_logger.setLevel(logging.WARNING)

basedir = os.getenv("BASEDIR", os.path.abspath(os.path.dirname(__file__)))
env_path = os.path.join(basedir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    config_logger.warning(f"No .env file found at {env_path}. Using default values.")

class Config:
    """Base configuration for the Flask application."""
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(32).hex()
    DB_USER = os.getenv("DB_USER", "mysql_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "mysql_password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "school_database")
    LOG_DIR = os.getenv("LOG_DIR", os.path.join(os.path.abspath(os.path.dirname(__file__)), "logs"))
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True
    }
    WTF_CSRF_ENABLED = True
    SCHOOL_NAME = os.getenv("SCHOOL_NAME", "Aunty Anne's International School")
    REG_NO_PREFIX = os.getenv("REG_NO_PREFIX", "AAIS/0559/")
    PERMANENT_SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", 86400))

    def __init__(self):
        if not self.SECRET_KEY or self.SECRET_KEY == "insecure_default_secret_key_please_change_me":
            config_logger.warning("Using insecure default SECRET_KEY. Set SECRET_KEY in .env for security.")
        if "mysql_user" in self.SQLALCHEMY_DATABASE_URI or "mysql_password" in self.SQLALCHEMY_DATABASE_URI:
            config_logger.warning("Using default DB credentials. Set DB_USER and DB_PASSWORD in .env.")

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SERVER_NAME = "localhost"

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = os.getenv("SQL_LOGGING", "False").lower() == "true"
    SERVER_NAME = os.getenv("SERVER_NAME", "auntyannesschools.com.ng")
    SECRET_KEY = os.environ.get("SECRET_KEY")

    @classmethod
    def init_app(cls, app):
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set in environment for production.")

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": Config,
}