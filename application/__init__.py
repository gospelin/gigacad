from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
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

from application import routes  # Import routes after initializing app and extensions
