from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_admin import Admin
from config import config_by_name, os
from .authentication import login_manager
import logging
from logging.handlers import RotatingFileHandler

# Initialize the app
app = Flask(__name__)

# Load configuration based on the environment
env = os.getenv("FLASK_ENV", "default")
app.config.from_object(config_by_name[env])

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

# Import blueprints
from application.auth import auth_bp
from application.admin import admin_bp
from application.main import main_bp
from application.student import student_bp

# Initialize login manager
login_manager.init_app(app)
login_manager.login_view = "auth.login"

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(main_bp)
app.register_blueprint(student_bp)

# Import models and admin views after initializing extensions
from application.models import Student, Result, Subject, User
from application.admin.admin_views import (
    MyAdminIndexView,
    ResultAdmin,
    StudentAdmin,
    SubjectAdmin,
)

# Initialize Flask-Admin with the custom index view
admin = Admin(app, index_view=MyAdminIndexView(), template_mode="bootstrap4")

# Register the Student model view with the admin
admin.add_view(StudentAdmin(Student, db.session))

# Register the Score model view with the admin
admin.add_view(ResultAdmin(Result, db.session))

# Register the Subject model view with the admin
admin.add_view(SubjectAdmin(Subject, db.session))

# Set up logging
if not app.debug:
    # Create a file handler for logging
    file_handler = RotatingFileHandler(
        "logs/flask_app.log", maxBytes=10240, backupCount=10
    )
    file_handler.setLevel(logging.INFO)

    # Create a formatter and attach it to the handler
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # Add the handler to the app's logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    # Log that the application has started
    app.logger.info("Flask application startup")
