from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from config import config_by_name, os
from .authentication import login_manager
import logging
from logging.handlers import RotatingFileHandler

# Initialize the extensions
db = SQLAlchemy()
migrate = Migrate()
# csrf = CSRFProtect()


# Function to create and configure the Flask application
def create_app(config_name=None):
    # Initialize the Flask app
    app = Flask(__name__)

    # Load configuration based on the environment
    env = os.getenv("FLASK_ENV", "default") if config_name is None else config_name
    app.config.from_object(config_by_name[env])


    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    csrf = CSRFProtect(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Import blueprints and register them
    from application.auth import auth_bp
    from application.admin import admin_bp
    from application.main import main_bp
    from application.student import student_bp
    from application.teacher import teacher_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(main_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp, url_prefix="/teacher")

    # app.register_blueprint(auth_bp, subdomain="portal")
    # app.register_blueprint(admin_bp, url_prefix="/admin", subdomain="portal")
    # app.register_blueprint(main_bp)
    # app.register_blueprint(student_bp, url_prefix="/student", subdomain="portal")
    # app.register_blueprint(teacher_bp, url_prefix="/teacher", subdomain="portal")

    # Set up logging for the app
    setup_logging(app)

    return app


# Function to set up logging
def setup_logging(app):
    log_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create a rotating file handler for logging
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "flask_app.log"), maxBytes=100960, backupCount=10
    )
    file_handler.setLevel(logging.INFO)

    # Set formatter for the logs
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Add the handler to the app's logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
