from flask import Blueprint

auth_bp = Blueprint("auth", __name__)


# Import the routes to ensure they are registered with the blueprint
from . import routes
