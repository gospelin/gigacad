from . import auth_bp
import logging
from flask import Blueprint, redirect, url_for, flash, render_template, request
from flask_login import login_required, login_user, logout_user, current_user
from application.models import User
from application.auth.forms import LoginForm
from application.helpers import rate_limit
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@rate_limit(limit=105, per=60)  # Limit to 5 requests per minute per IP
def login():
    if current_user.is_authenticated:
        return redirect(url_for("students.student_portal"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if hasattr(user, "student") and user.student and not user.student.approved:
                flash(
                    "Your account is not approved yet. Please contact admin.",
                    "alert alert-danger",
                )
                logger.warning(f"Unapproved login attempt for user: {user.username}")
                return redirect(url_for("auth.login"))

            login_user(user)
            next_page = request.args.get("next")
            logger.info(f"User {user.username} logged in successfully")
            return (
                redirect(next_page)
                if next_page
                else redirect(url_for("students.student_portal"))
            )
        else:
            flash(
                "Login Unsuccessful. Please check username and password",
                "alert alert-danger",
            )
            logger.warning(f"Failed login attempt for username: {form.username.data}")

    return render_template("auth/login.html", title="Login", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


