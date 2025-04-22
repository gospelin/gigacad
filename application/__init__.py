import os
from flask import Flask, render_template, flash, has_request_context, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
from jinja2 import filters
from config import config_by_name
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pythonjsonlogger import jsonlogger
import colorlog
from uuid import uuid4
import json
import pytz

# Initialize extensions globally
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
bcrypt = Bcrypt()
limiter = Limiter(key_func=get_remote_address)
login_manager = LoginManager()
login_manager.login_message_category = "alert-info"
login_manager.session_protection = "strong"

# Define Nigeria timezone (WAT, UTC+1)
NIGERIA_TZ = pytz.timezone('Africa/Lagos')

class PrettyJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with pretty printing and request context."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def format(self, record):
        record.asctime = self.formatTime(record, self.datefmt)
        nigeria_time = datetime.now(NIGERIA_TZ)
        log_record = self.process_log_record(record.__dict__.copy())

        if has_request_context():
            log_record['blueprint'] = request.blueprint or "no-blueprint"
            log_record['endpoint'] = request.endpoint or "no-endpoint"
            log_record['url'] = request.url
            log_record['request_id'] = getattr(request, 'request_id', 'no-request-id')
        else:
            log_record['blueprint'] = None
            log_record['endpoint'] = None
            log_record['url'] = None
            log_record['request_id'] = None
        log_record['timestamp'] = nigeria_time.isoformat()

        filtered_record = {
            'asctime': nigeria_time.strftime('%Y-%m-%d %H:%M:%S'),
            'name': log_record['name'],
            'levelname': log_record['levelname'],
            'pathname': log_record['pathname'],
            'lineno': log_record['lineno'],
            'funcName': log_record['funcName'],
            'message': record.getMessage(),
            'blueprint': log_record['blueprint'],
            'endpoint': log_record['endpoint'],
            'url': log_record['url'],
            'request_id': log_record['request_id'],
            'timestamp': log_record['timestamp'],
            'exc_info': str(record.exc_info) if record.exc_info else None
        }

        return json.dumps(filtered_record, indent=2, ensure_ascii=False) + "\n"

@login_manager.user_loader
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(OperationalError)
)
def load_user(user_id):
    from .models import User
    try:
        user_id_int = int(user_id)
        db.session.execute(text("SELECT 1"))
        user = User.query.get(user_id_int)
        if user and user.active:
            app.logger.debug(f"User {user.username} (ID: {user_id}) loaded successfully",
                           extra={"user_id": user_id, "username": user.username})
            return user
        app.logger.debug(f"No active user found for ID: {user_id}", extra={"user_id": user_id})
        return None
    except ValueError as e:
        app.logger.warning(f"Invalid user_id format '{user_id}': {str(e)}", extra={"user_id": user_id})
        return None
    except OperationalError as e:
        app.logger.error(f"Database error loading user {user_id}: {str(e)}", exc_info=True, extra={"user_id": user_id})
        raise
    except Exception as e:
        app.logger.error(f"Unexpected error loading user {user_id}: {str(e)}", exc_info=True, extra={"user_id": user_id})
        return None

def datetimeformat(value, format_string="%d %B %Y"):
    if value == "now":
        return datetime.now(NIGERIA_TZ).strftime(format_string)
    return value.strftime(format_string) if hasattr(value, 'strftime') else value

def setup_logging(app):
    """Configure advanced logging with pretty-printed JSON for files."""
    log_dir = app.config.get("LOG_DIR", "/home/gigo/AAIS/logs")
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
            app.logger.info(f"Created log directory: {log_dir}")
        except OSError as e:
            app.logger.warning(f"Failed to create log directory {log_dir}: {str(e)}. Logs may not be written.")

    if app.logger.handlers:
        app.logger.handlers.clear()

    json_formatter = PrettyJsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(pathname)s %(lineno)d %(funcName)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - "
        "%(pathname)s:%(lineno)d - %(funcName)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if os.getenv("PYTHONANYWHERE") != "true":
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(color_formatter)
        app.logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "flask_app.log"),
        maxBytes=50480,
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(json_formatter)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    sqlalchemy_logger.handlers.clear()
    sqlalchemy_logger.addHandler(file_handler)
    sqlalchemy_logger.setLevel(logging.WARNING)

    @app.before_request
    def add_request_id():
        request.request_id = str(uuid4())
        app.logger.debug("Request started", extra={"request_id": request.request_id})

    app.logger.info("Advanced logging setup complete", extra={"env": app.config.get("FLASK_ENV", "unknown")})

def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.jinja_env.filters['datetimeformat'] = datetimeformat

    env = os.getenv("FLASK_ENV", "default") if config_name is None else config_name
    app.config.from_object(config_by_name[env])

    # Call init_app for configuration-specific validation
    if hasattr(config_by_name[env], "init_app"):
        config_by_name[env].init_app(app)

    session_config = {
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "PERMANENT_SESSION_LIFETIME": app.config.get("PERMANENT_SESSION_LIFETIME", 7776000),
        "SESSION_COOKIE_NAME": "session",
        "SESSION_COOKIE_PATH": "/",
        "SESSION_COOKIE_SECURE": True if env == "production" and app.config.get("SERVER_NAME", "").startswith("https") else False,
    }
    app.config.update(session_config)
    app.logger.debug(f"Session configuration applied: {session_config}")

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # Matches /portal
    bcrypt.init_app(app)
    try:
        limiter.init_app(app)
    except Exception as e:
        app.logger.error(f"Failed to initialize Flask-Limiter: {str(e)}", exc_info=True)
        raise RuntimeError("Failed to initialize Flask-Limiter.") from e

    setup_logging(app)

    from application.auth.routes import auth_bp
    from application.admins.routes import admin_bp
    from application.main.routes import main_bp
    from application.students.routes import student_bp
    from application.teachers.routes import teacher_bp

    try:
        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp, url_prefix="/admin")
        app.register_blueprint(main_bp)
        app.register_blueprint(student_bp, url_prefix="/student")
        app.register_blueprint(teacher_bp, url_prefix="/teacher")
        app.logger.info("Registered blueprints: auth, admins, main, students, teachers")
    except Exception as e:
        app.logger.error(f"Error registering blueprints: {str(e)}", exc_info=True)
        raise RuntimeError("Failed to register blueprints.") from e

    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f"404 Error: {error}", extra={"path": request.path})
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Server Error: {error}", exc_info=True)
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        app.logger.warning(f"CSRF error: {e.description}", extra={"path": request.path})
        flash("The form submission has expired. Please try again.", "alert-danger")
        return render_template("errors/csrf.html"), 403

    @app.errorhandler(403)
    def forbidden_error(error):
        app.logger.warning(f"403 Forbidden: {error}", extra={"path": request.path})
        return render_template("errors/403.html"), 403

    with app.app_context():
        if not app.config.get("TESTING", False):
            try:
                db.session.execute(text("SELECT 1"))
                app.logger.info("Database connection verified on startup")
            except OperationalError as e:
                app.logger.error(f"Failed to connect to database on startup: {str(e)}", exc_info=True)
                raise RuntimeError("Database connection failed on startup") from e

    return app

app = create_app()