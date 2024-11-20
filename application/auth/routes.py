from . import auth_bp
from flask import redirect, url_for, flash, render_template, request, current_app as app
from flask_login import login_required, login_user, logout_user, current_user
from application.models import User
from application.auth.forms import LoginForm
from application.helpers import rate_limit


@auth_bp.route("/login", methods=["GET", "POST"])
@rate_limit(limit=15, per=60)  # Limit to 5 requests per minute per IP
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
                app.logger.warning(f"Unapproved login attempt for user: {user.username}")
                return redirect(url_for("auth.login"))

            login_user(user)
            next_page = request.args.get("next")
            app.logger.info(f"User {user.username} logged in successfully")
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
            app.logger.warning(f"Failed login attempt for username: {form.username.data}")

    return render_template("auth/login.html", title="Login", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
