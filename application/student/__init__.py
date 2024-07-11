from flask import Blueprint

student_bp = Blueprint("students", __name__)

from . import routes
