from . import auth_bp
from flask import redirect, url_for, flash, render_template, request, current_app as app
from flask_login import login_required, login_user, logout_user, current_user
from application.models import User, Student
from application.auth.forms import StudentLoginForm, AdminLoginForm
from application.helpers import rate_limit

@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admins.admin_dashboard"))
        return redirect(url_for("students.student_portal"))

    # Instantiate forms
    student_form = StudentLoginForm()
    admin_form = AdminLoginForm()

    # Handle student login form submission
    if student_form.validate_on_submit():
        identifier = student_form.identifier.data
        password = student_form.password.data

        if identifier.startswith("AAIS/0559/"):
            try:
                student_id = int(identifier.split("/")[-1])
                student = Student.query.get(student_id)  # Query Student by ID
                user = student.user if student else None
            except (ValueError, AttributeError):
                user = None
        else:
            # Check if the identifier matches a student's username but ensure it's not an admin
            user = User.query.filter_by(username=identifier).first()
            if user and (not hasattr(user, "student") or user.is_admin):
                user = None  # Exclude admin or non-student users

        # Verify user credentials and role
        if user and user.check_password(password) and hasattr(user, "student"):
            if not user.student.approved:
                flash("Your account is not approved yet. Please contact admin.", "alert alert-danger")
                return redirect(url_for("auth.login"))

            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("students.student_portal"))
        else:
            flash("Login Unsuccessful. Please check your Student ID/Username and password.", "alert alert-danger")

    # Handle admin login form submission
    if admin_form.validate_on_submit():
        username = admin_form.username.data
        password = admin_form.password.data

        user = User.query.filter_by(username=username).first()

        # Verify user credentials and admin role
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("admins.admin_dashboard"))
        else:
            flash("Login Unsuccessful. Please check your username and password.", "alert alert-danger")

    # Render the login page with both forms
    return render_template(
        "auth/login.html",
        title="Login",
        student_form=student_form,
        admin_form=admin_form,
    )


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
