from . import main_bp
import logging, os
from flask_wtf.csrf import CSRFError
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    # make_response,
)
from flask_login import login_required, login_user, logout_user, current_user
from ..models import Student, User, Subject, Result
from collections import defaultdict
from ..auth.forms import (
    StudentRegistrationForm,
    LoginForm,
    ResultForm,
    EditStudentForm,
    SubjectForm,
    DeleteForm,
    ApproveForm,
)
from ..helpers import (
    get_subjects_by_entry_class,
    update_results,
    calculate_results,
    generate_unique_username,
    db,
    get_last_term,
    calculate_average,
    calculate_cumulative_average,
    random,
    string,
    rate_limit,
)

# from weasyprint import HTML
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@main_bp.route("/")
@main_bp.route("/index")
@main_bp.route("/home")
def index():
    return render_template(
        "main/index.html", title="Home", school_name="Aunty Anne's Int'l School"
    )

@main_bp.route("/about_us")
def about_us():
    return render_template(
        "main/about_us.html", title="About Us", school_name="Aunty Anne's Int'l School"
    )


# """ Manage Student Section

# This section includes functionalities like:

# Register Student - Add a new student to the database and generate username and password
# Login - Authenticate a user and log them in
# Logout - Log a user out
# Approve Students - Approve or deactivate students
# Manage Classes - View all students by class
# Manage Results - Add, edit, and delete student results
# View Results - View student results
# Manage Students - View all students
# Add Students - Add a new student
# Edit Student - Edit a student's details
# Delete Student - Delete a student
# Manage Subjects - Add, edit, and delete subjects
# Regenerate Password - Generate a new password for a student

# """


@main_bp.route("/register/student", methods=["GET", "POST"])
def student_registration():
    form = StudentRegistrationForm()
    try:
        if form.validate_on_submit():
            username = generate_unique_username(
                form.first_name.data, form.last_name.data
            )
            temporary_password = "".join(
                random.choices(string.ascii_letters + string.digits, k=8)
            )

            student = Student(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                middle_name=form.middle_name.data,
                gender=form.gender.data,
                date_of_birth=form.date_of_birth.data,
                parent_name=form.parent_name.data,
                parent_phone_number=form.parent_phone_number.data,
                address=form.address.data,
                parent_occupation=form.parent_occupation.data,
                entry_class=form.entry_class.data,
                previous_class=form.previous_class.data,
                state_of_origin=form.state_of_origin.data,
                local_government_area=form.local_government_area.data,
                religion=form.religion.data,
                username=username,
                password=temporary_password,
            )

            user = User(username=student.username, is_admin=False)
            user.set_password(temporary_password)
            student.user = user

            db.session.add(student)
            db.session.add(user)
            db.session.commit()

            logger.info(f"Student registered successfully: {username}")
            flash(
                f"Student registered successfully. Username: {username}, Password: {temporary_password}",
                "alert alert-success",
            )
            return redirect(url_for("main.student_registration"))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error registering student: {str(e)}")
        flash("An error occurred. Please try again later.", "alert alert-danger")

    return render_template(
        "student/student_registration.html",
        title="Register",
        form=form,
        school_name="Aunty Anne's Int'l School",
    )


# CSRF error handler
@main_bp.errorhandler(CSRFError)
def handle_csrf_error(e):
    logger.warning(f"CSRF error: {e.description}")
    flash("The form submission has expired. Please try again.", "alert alert-danger")
    return redirect(url_for("main.student_registration"))
