from . import auth_bp
from flask import redirect, url_for, flash, render_template, request, current_app as app
from flask_login import login_required, login_user, logout_user, current_user
from application.models import User
from application.auth.forms import LoginForm
from application.helpers import rate_limit

@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
@rate_limit(limit=15, per=60)  # Limit to 5 requests per minute per IP
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admins.admin_dashboard"))
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

# @auth_bp.route("/login", methods=["GET", "POST"])
# def login():
#     if current_user.is_authenticated:
#         if current_user.is_admin:
#             return redirect(url_for("admins.admin_dashboard", _external=True, _scheme="https", _subdomain="portal"))
#         return redirect(url_for("students.student_portal", _external=True, _scheme="https", _subdomain="portal"))

#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(username=form.username.data).first()
#         if user and user.check_password(form.password.data):
#             login_user(user)
#             next_page = request.args.get("next")
#             return redirect(next_page) if next_page else redirect(
#                 url_for("students.student_portal", _external=True, _scheme="https", _subdomain="portal")
#             )
#         flash("Invalid username or password", "alert alert-danger")
#     return render_template("auth/login.html", form=form)


# @auth_bp.route("/login", methods=["GET", "POST"])
# def login():
#     if current_user.is_authenticated:
#         # Redirect based on user type
#         if current_user.is_admin:
#             return redirect(url_for("admins.admin_dashboard", _external=True, _scheme="https", _subdomain="portal"))
#         return redirect(url_for("students.student_portal", _external=True, _scheme="https", _subdomain="portal"))

#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(username=form.username.data).first()
#         if user and user.check_password(form.password.data):
#             login_user(user)
#             # Handle the 'next' parameter
#             next_page = request.args.get("next")
#             if not next_page:
#                 next_page = url_for("students.student_portal", _external=True, _scheme="https", _subdomain="portal")
#             app.logger.info(f"Redirecting to: {next_page}")
#             return redirect(next_page)
#         else:
#             flash("Invalid credentials.", "alert alert-danger")
#     return render_template("auth/login.html", form=form)

# @auth_bp.route("/login", methods=["GET", "POST"], subdomain="portal")
# @rate_limit(limit=15, per=60)  # Limit to 15 requests per minute per IP
# def login():
#     if current_user.is_authenticated:
#         # Redirect to the student portal, ensuring the subdomain is included
#         return redirect(url_for("students.student_portal", _external=True, _scheme="https", _subdomain="portal"))

#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(username=form.username.data).first()
#         if user and user.check_password(form.password.data):
#             if hasattr(user, "student") and user.student and not user.student.approved:
#                 flash(
#                     "Your account is not approved yet. Please contact admin.",
#                     "alert alert-danger",
#                 )
#                 app.logger.warning(f"Unapproved login attempt for user: {user.username}")
#                 return redirect(url_for("auth.login", _external=True, _scheme="https", _subdomain="portal"))

#             login_user(user)
#             next_page = request.args.get("next")
#             app.logger.info(f"User {user.username} logged in successfully")
#             # Redirect to next page or the student portal with the subdomain
#             return (
#                 redirect(next_page)
#                 if next_page
#                 else redirect(url_for("students.student_portal", _external=True, _scheme="https", _subdomain="portal"))
#             )
#         else:
#             flash(
#                 "Login Unsuccessful. Please check username and password",
#                 "alert alert-danger",
#             )
#             app.logger.warning(f"Failed login attempt for username: {form.username.data}")

#     # Ensure the login page is loaded on the subdomain
#     return render_template("auth/login.html", title="Login", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
