from flask import Blueprint

admin_bp = Blueprint("admins", __name__)

from . import routes
