from flask import Blueprint

teacher_bp = Blueprint("teachers", __name__)

from . import routes
