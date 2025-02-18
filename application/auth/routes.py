from . import auth_bp
from flask import redirect, url_for, flash, render_template, request, current_app as app
from flask_login import login_required, login_user, logout_user, current_user
from application.models import User, Student, RoleEnum
from application.auth.forms import StudentLoginForm, AdminLoginForm
from application.helpers import rate_limit

# @auth_bp.route("/", methods=["GET", "POST"])
# @auth_bp.route("/login", methods=["GET", "POST"])
# def login():
#     if current_user.is_authenticated:
#         if current_user.is_admin:
#             return redirect(url_for("admins.admin_dashboard"))
#         return redirect(url_for("students.student_portal"))

#     # Instantiate forms
#     student_form = StudentLoginForm()
#     admin_form = AdminLoginForm()

#     # Handle student login form submission
#     if student_form.validate_on_submit():
#         identifier = student_form.identifier.data
#         password = student_form.password.data

#         # Query the Student by reg_no
#         student = Student.query.filter_by(reg_no=identifier).first()
#         user = student.user if student else None  # Get associated user if student exists

#         # Verify user credentials and role
#         if user and user.check_password(password) and hasattr(user, "student"):
#             if not user.student.approved:
#                 flash("Your account is not approved yet. Please contact admin.", "alert alert-danger")
#                 return redirect(url_for("auth.login"))

#             login_user(user)
#             next_page = request.args.get("next")
#             return redirect(next_page) if next_page else redirect(url_for("students.student_portal"))
#         else:
#             flash("Login Unsuccessful. Please check your Student ID and password.", "alert alert-danger")

#     # Handle admin login form submission
#     if admin_form.validate_on_submit():
#         username = admin_form.username.data
#         password = admin_form.password.data

#         user = User.query.filter_by(username=username).first()

#         # Verify user credentials and admin role
#         if user and user.check_password(password) and user.is_admin:
#             login_user(user)
#             next_page = request.args.get("next")
#             return redirect(next_page) if next_page else redirect(url_for("admins.admin_dashboard"))
#         else:
#             flash("Login Unsuccessful. Please check your username and password.", "alert alert-danger")

#     # Render the login page with both forms
#     return render_template(
#         "auth/login.html",
#         title="Login",
#         student_form=student_form,
#         admin_form=admin_form,
#     )


# @auth_bp.route("/logout")
# @login_required
# def logout():
#     logout_user()
#     return redirect(url_for("auth.login"))



# @auth_bp.route("/login", methods=["GET", "POST"])
# def login():
#     if current_user.is_authenticated:
#         return redirect_based_on_role(current_user)

#     form = LoginForm()
#     if form.validate_on_submit():
#         username = form.username.data
#         password = form.password.data

#         user = User.query.filter_by(username=username).first()

#         if user and user.check_password(password):
#             if not user.active:
#                 flash("Account is inactive. Contact admin.", "alert alert-danger")
#                 return redirect(url_for("auth.login"))

#             login_user(user)
#             return redirect_based_on_role(user)
#         else:
#             flash("Invalid credentials. Please try again.", "alert alert-danger")

#     return render_template("auth/login.html", title="Login", form=form)

@auth_bp.route("/portal", methods=["GET", "POST"])
@auth_bp.route("/portal/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect_based_on_role(current_user)

    # Instantiate forms
    student_form = StudentLoginForm()
    admin_form = AdminLoginForm()

    username = None
    password = None

    # Determine which form was submitted and process accordingly
    if student_form.validate_on_submit():
        username = student_form.identifier.data
        password = student_form.password.data
    elif admin_form.validate_on_submit():
        username = admin_form.username.data
        password = admin_form.password.data

    # Query user
    user = User.query.filter_by(username=username).first()

    # Verify user and credentials
    if user and user.check_password(password):
        if not user.active:
            flash("Account is inactive. Contact admin.", "alert alert-danger")
            return redirect(url_for("auth.login"))

        login_user(user)
        return redirect_based_on_role(user)
    elif student_form.is_submitted() or admin_form.is_submitted():
        flash("Invalid credentials. Please check your username and password.", "alert alert-danger")

    return render_template(
        "auth/login.html",
        title="Login",
        student_form=student_form,
        admin_form=admin_form,
    )


# @auth_bp.route("/portal", methods=["GET", "POST"])
# @auth_bp.route("/portal/login", methods=["GET", "POST"])
# def login():
#     return redirect("https://gigo.pythonanywhere.com/login", code=302)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "alert alert-success")
    return redirect(url_for("auth.login"))

def redirect_based_on_role(user):
    if user.role == RoleEnum.ADMIN:
        return redirect(url_for("admins.admin_dashboard"))
    elif user.role == RoleEnum.STUDENT:
        return redirect(url_for("students.student_portal"))
    elif user.role == RoleEnum.TEACHER:
        return redirect(url_for("teachers.teacher_dashboard"))
    else:
        logout_user()
        flash("Unauthorized access.", "alert alert-danger")
        return redirect(url_for("auth.login"))
