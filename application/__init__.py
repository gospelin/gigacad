from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_admin import Admin
from .auth import login_manager
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize Flask-WTF's CSRFProtect
csrf = CSRFProtect(app)

# Initialize Flask-Login's LoginManager
login_manager.init_app(app)
login_manager.login_view = "login"

# Import the custom admin index view and model view classes
from application.admin_views import (
    MyAdminIndexView,
    ResultAdmin,
    StudentAdmin,
    SubjectAdmin,
)
from application.models import Student, Result, Subject

# Initialize Flask-Admin with the custom index view
admin = Admin(app, index_view=MyAdminIndexView(), template_mode="bootstrap4")

# Register the Student model view with the admin
admin.add_view(StudentAdmin(Student, db.session))

# Register the Score model view with the admin
admin.add_view(ResultAdmin(Result, db.session))

# Register the Subject model view with the admin
admin.add_view(SubjectAdmin(Subject, db.session))

# Import routes after initializing app and extensions
from application import routes
