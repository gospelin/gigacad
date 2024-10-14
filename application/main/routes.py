from . import main_bp
import logging
from flask_wtf.csrf import CSRFError
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
)
from ..models import Student, User, StudentClassHistory, Session
from ..auth.forms import StudentRegistrationForm

from ..helpers import (
    generate_unique_username,
    db,
    random,
    string,
)

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
    current_session = (
        Session.get_current_session()
    )  
    try:
        if form.validate_on_submit():
            # Generate a unique username and temporary password
            username = generate_unique_username(
                form.first_name.data, form.last_name.data
            )
            temporary_password = "".join(
                random.choices(string.ascii_letters + string.digits, k=8)
            )

            # Create the Student object
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
                state_of_origin=form.state_of_origin.data,
                local_government_area=form.local_government_area.data,
                religion=form.religion.data,
                username=username,
                password=temporary_password,
                approved=False,  
            )

            # Create a User object for login credentials
            user = User(username=student.username, is_admin=False)
            user.set_password(temporary_password)  # Hash the temporary password
            student.user = user  # Link user to the student

            # Add the student and user to the session
            db.session.add(student)
            db.session.add(user)
            db.session.flush()  # Ensure student gets an ID before creating the class history

            # Add entry to StudentClassHistory to track class for the current session
            class_history = StudentClassHistory(
                student_id=student.id,
                session_id=current_session.id,  # Store session ID from current session
                class_name=form.class_name.data,  # Store the class entered during registration
            )
            db.session.add(class_history)

            # Commit all changes (student, user, class history)
            db.session.commit()

            # Log success and inform the user
            logger.info(f"Student registered successfully: {username}")
            flash(
                f"Student registered successfully. Username: {username}, Password: {temporary_password}",
                "alert alert-success",
            )
            return redirect(url_for("main.student_registration"))

    except Exception as e:
        db.session.rollback()  # Rollback the session on error
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
