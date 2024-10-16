"""
Generic functions/routes of the Admin Dashboard

    admin_dashboard: Displays the admin dashboard
    manage_sessions: Manages the current session
    change_session: Changes the current session
"""

"""
Route for managing sessions.

This route allows administrators to manage sessions. Only users with admin privileges can access this route.
Administrators can select a session from a form and change the current session to the selected one.

Returns:
    If the form is submitted successfully, the user is redirected to the "change_session" route with the selected session ID.
    Otherwise, the user is rendered the "admin/manage_sessions.html" template with the current session and the session form.
"""
from datetime import datetime
from . import admin_bp
from io import BytesIO

# import io
import openpyxl
from openpyxl.styles import Font, Border, Side, Alignment
from openpyxl.utils import get_column_letter
import logging
from flask import (
    abort,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    Response,
    # make_response,
)
from flask_login import login_required, current_user
from ..models import Student, User, Subject, Result, Session, StudentClassHistory
from collections import defaultdict
from ..auth.forms import (
    EditStudentForm,
    ResultForm,
    SubjectForm,
    DeleteForm,
    SelectTermSessionForm,
    SessionForm,
    ApproveForm,
    classForm
)
from ..helpers import (
    get_subjects_by_class_name,
    update_results,
    calculate_results,
    db,
    random,
    string,
)


from weasyprint import HTML
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@admin_bp.before_request
@login_required
def admin_before_request():
    if not current_user.is_admin:
        flash("You are not authorized to access this page.", "alert alert-danger")
        return redirect(url_for("main.index"))


@admin_bp.route("/dashboard")
def admin_dashboard():
    return render_template("admin/index.html")

@admin_bp.route("/manage_sessions", methods=["GET", "POST"])
@login_required
def manage_sessions():
    """
    Route for managing sessions.

    This route allows administrators to manage sessions. Only users with admin privileges can access this route.
    Administrators can select a session from a form and change the current session to the selected one.

    Returns:
        If the form is submitted successfully, the user is redirected to the "change_session" route with the selected session ID.
        Otherwise, the user is rendered the "admin/manage_sessions.html" template with the current session and the session form.
    """

    if not current_user.is_admin:
        abort(403)  # Restrict access for non-admins

    form = SessionForm()

    # Fetch all sessions and populate the choices for the form
    sessions = Session.query.all()
    form.session.choices = [(session.id, session.year) for session in sessions]

    # Set the default session to the current session
    current_session = Session.get_current_session()

    if form.validate_on_submit():
        selected_session = form.session.data
        return redirect(
            url_for("admins.change_session", session_id=selected_session)
        )

    return render_template("admin/manage_sessions.html", current_session=current_session.year, form=form)


@admin_bp.route("/change_session/<int:session_id>", methods=["GET", "POST"])
@login_required
def change_session(session_id):
    """
    Change the current session to the specified session ID.

    Args:
        session_id (int): The ID of the session to set as the current session.

    Returns:
        redirect: Redirects to the "manage_sessions" route.

    Raises:
        403: If the current user is not an admin.

    """

    if not current_user.is_admin:
        abort(403)  # Restrict access for non-admins

    new_session = Session.set_current_session(session_id)

    if new_session:
        flash(
            f"The current session has been updated to {new_session.year}.",
            "alert alert-success",
        )
    else:
        flash("Failed to update the current session.", "alert alert-danger")

    return redirect(url_for("admins.manage_sessions"))


""""
Student Management Section

This section displays the basic view of the student management page
The page displays the list of students and their details
It also provides links to edit, delete, approve, and deactivate students

    approve_students: Displays the list of students and their approval status
    approve_student: Approves a student
    deactivate_student: Deactivates a student
    regenerate_password: Regenerates the password for a student
    manage_classes: Displays the list of classes
    view_class_by_session: Displays the list of students in a class for a given session
    students_by_class: Displays the list of students in a class
    promote_student: Promotes a student to the next class
    edit_student: Edits the details of a student
    delete_student: Deletes a student
"""

@admin_bp.route("/admin/manage_students", methods=["GET", "POST"])
@login_required
def manage_students():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("auth.login"))
    students = Student.query.all()
    return render_template("admin/students/student_admin.html", students=students)


@admin_bp.route("/admin/approve_students", methods=["GET", "POST"])
@login_required
def approve_students():
    """
    View function for approving students in the admin panel.

    This function is responsible for rendering the approve students page in the admin panel.
    It fetches the available sessions, populates the session choices for the form,
    retrieves students and their class history for the selected session,
    groups the students by their class name, and renders the template with the necessary data.

    Returns:
        The rendered template for the approve students page.

    Raises:
        403: If the current user is not an admin.
    """
    if not current_user.is_admin:
        abort(403)  # Restrict access for non-admins

    approve_form = ApproveForm(prefix="approve")
    deactivate_form = ApproveForm(prefix="deactivate")
    regenerate_form = ApproveForm(prefix="regenerate")
    session_form = SessionForm()

    # Fetch available sessions and populate the choices for the form
    sessions = Session.query.all()
    session_form.session.choices = [(session.id, session.year) for session in sessions]

    # Default to the latest session if none is selected
    selected_session_id = (
        session_form.session.data
        if session_form.validate_on_submit()
        else sessions[-1].id
    )

    # Get students and their class history for the selected session
    students = (
        db.session.query(Student, StudentClassHistory.class_name)
        .join(
            StudentClassHistory,
            (Student.id == StudentClassHistory.student_id)
            & (StudentClassHistory.session_id == selected_session_id),
        )
        .order_by(StudentClassHistory.class_name)
        .all()
    )

    # Group students by their class name
    students_by_class = defaultdict(list)
    for student, class_name in students:
        students_by_class[class_name].append(student)

    return render_template(
        "admin/students/approve_students.html",
        students_by_class=students_by_class,
        approve_form=approve_form,
        deactivate_form=deactivate_form,
        regenerate_form=regenerate_form,
        session_form=session_form,
    )


@admin_bp.route("/admin/approve_student/<int:student_id>", methods=["POST"])
@login_required
def approve_student(student_id):
    """
    Approves a student with the given student_id.

    Args:
        student_id (int): The ID of the student to be approved.

    Returns:
        redirect: Redirects to the "approve_students" route.

    Raises:
        403: If the current user is not an admin.

    """
    if not current_user.is_admin:
        abort(403)  # Forbidden access

    form = ApproveForm(prefix="approve")

    if form.validate_on_submit():
        student = Student.query.get_or_404(student_id)
        if student.approved:
            flash(
                f"Student {student.first_name} {student.last_name} is already approved.",
                "alert alert-info",
            )
        else:
            student.approved = True
            db.session.commit()
            flash(
                f"Student {student.first_name} {student.last_name} has been approved.",
                "alert alert-success",
            )
    else:
        flash("Form validation failed. Please try again.", "alert alert-danger")

    return redirect(url_for("admins.approve_students"))


@admin_bp.route("/admin/deactivate_student/<int:student_id>", methods=["POST"])
@login_required
def deactivate_student(student_id):
    if not current_user.is_admin:
        abort(403)  # Forbidden access

    form = ApproveForm()
    if form.validate_on_submit():
        student = Student.query.get_or_404(student_id)
        student.approved = False
        db.session.commit()
        flash(
            f"Student {student.first_name} {student.last_name} has been deactivated.",
            "alert alert-success",
        )
    else:
        flash("An error occurred. Please try again.", "alert alert-danger")
    return redirect(url_for("admins.approve_students"))


@admin_bp.route("/admin/regenerate_credentials/<int:student_id>", methods=["POST"])
@login_required
def regenerate_password(student_id):
    """
    Regenerates the password for a student's account and updates it in the database.

    Args:
        student_id (int): The ID of the student whose password needs to be regenerated.

    Returns:
        redirect: Redirects to the "approve_students" route after regenerating the password.

    Raises:
        403: If the current user is not an admin, a Forbidden access error is raised.

    """
    if not current_user.is_admin:
        abort(403)  # Forbidden access

    form = ApproveForm(prefix="regenerate")

    if form.validate_on_submit():
        student = Student.query.get_or_404(student_id)
        new_password = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        student.user.set_password(new_password)
        db.session.commit()

        flash(
            f"Credentials regenerated for {student.first_name} {student.last_name}. New password: {new_password}",
            "alert alert-success",
        )
    else:
        flash("Form validation failed. Please try again.", "alert alert-danger")

    return redirect(url_for("admins.approve_students"))


@admin_bp.route("/admin/manage_classes")
@login_required
def manage_classes():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("auth.login"))
    students = Student.query.all()
    return render_template("admin/classes/classes.html", students=students)


@admin_bp.route("/select_class", methods=["GET", "POST"])
@login_required
def view_class_by_session():
    """
    View function for selecting a class based on session.

    This function handles the GET and POST requests for selecting a class based on session.
    It renders a form to select the session and class, and redirects to the students by class page
    when the form is submitted.

    Returns:
        A rendered template for selecting a class by session.
    """
    form = classForm()
    # Query the sessions from the database
    sessions = Session.query.all() 
    form.session.choices = [
        (session.id, session.year) for session in sessions
    ]
    current_session = Session.get_current_session()

    if form.validate_on_submit():
        selected_session = form.session.data

        selected_class = form.class_name.data
        return redirect(
            url_for(
                "admins.students_by_class",
                session_id=selected_session,
                class_name=selected_class,
            )
        )
    return render_template("admin/classes/select_class_by_session.html", current_session=current_session.year, form=form)


@admin_bp.route("/students_by_class/<int:session_id>/<string:class_name>")
@login_required
def students_by_class(session_id, class_name):
    """
    Retrieve students by class for a given session.

    Args:
        session_id (int): The ID of the session.
        class_name (str): The name of the class.

    Returns:
        render_template: The rendered template with the students, session, class name, and form.
    """
    # Get the selected session
    session = Session.query.get_or_404(session_id)

    # Get the student history filtered by session and class
    student_histories = StudentClassHistory.query.filter_by(
        session_id=session_id, class_name=class_name
    ).all()

    # Extract the students based on the history records
    students = [history.student for history in student_histories]

    form = DeleteForm()  # Example form for actions like delete or edit
    return render_template(
        "admin/classes/students_by_class.html",
        students=students,
        session=session,
        class_name=class_name,
        form=form,
    )


@admin_bp.route("/promote_student/<int:student_id>", methods=["POST"])
@login_required
def promote_student(student_id):
    """
    Promotes a student to the next class if applicable.

    Args:
        student_id (int): The ID of the student to be promoted.

    Returns:
        redirect: Redirects to the page displaying students of the new class.

    Raises:
        403: If the current user is not an admin.
        404: If the student with the given ID is not found.
    """
    if not current_user.is_admin:
        abort(403)  # Restrict access for non-admins

    student = Student.query.get_or_404(student_id)
    current_session = Session.get_current_session()

    if not current_session:
        flash("No current session available for promotion.", "alert alert-danger")
        return redirect(url_for("admins.manage_students"))

    # Define the class hierarchy
    class_hierarchy = [
        "Creche",
        "Pre-Nursery",
        "Nursery 1",
        "Nursery 2",
        "Nursery 3",
        "Basic 1",
        "Basic 2",
        "Basic 3",
        "Basic 4",
        "Basic 5",
        "Basic 6",
        "JSS 1",
        "JSS 2",
        "JSS 3",
    ]

    # Retrieve the latest class from StudentClassHistory
    latest_class_history = (
        StudentClassHistory.query.filter_by(student_id=student.id)
        .order_by(StudentClassHistory.id.desc())
        .first()
    )

    if not latest_class_history:
        flash("No class history found for the student.", "alert alert-danger")
        return redirect(url_for("admins.manage_students"))

    current_class = latest_class_history.class_name

    # Promote the student to the next class if applicable
    if current_class in class_hierarchy:
        current_index = class_hierarchy.index(current_class)
        if current_index + 1 < len(class_hierarchy):
            new_class = class_hierarchy[current_index + 1]
        else:
            flash(
                "This student has completed the highest class.", "alert alert-warning"
            )
            return redirect(
                url_for(
                    "admins.students_by_class",
                    session_id=current_session.id,
                    class_name=current_class,
                )
            )
    else:
        flash("Current class not found in the hierarchy.", "alert alert-danger")
        return redirect(
            url_for(
                "admins.students_by_class",
                session_id=current_session.id,
                class_name=current_class,
            )
        )

    # Add a new StudentClassHistory record for the promotion, only for the current session
    new_class_history = StudentClassHistory(
        student_id=student.id, session_id=current_session.id, class_name=new_class
    )
    db.session.add(new_class_history)
    db.session.commit()

    flash(
        f"{student.first_name} has been promoted to {new_class}.", "alert alert-success"
    )
    return redirect(
        url_for(
            "admins.students_by_class",
            session_id=current_session.id,
            class_name=new_class,
        )
    )


@admin_bp.route("/admin/edit_student/<int:student_id>", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    """
    Edit a student's information.

    Args:
        student_id (int): The ID of the student to be edited.

    Returns:
        A rendered template for editing a student's information.

    Raises:
        403: If the current user is not an admin.

    """
    if not current_user.is_admin:
        abort(403)  # Restrict access for non-admins

    student = Student.query.get_or_404(student_id)
    session_id = Session.query.filter_by(is_current=True).first().id
    form = EditStudentForm()

    # Retrieve the latest class history for the student
    student_class_history = (
        StudentClassHistory.query.filter_by(student_id=student.id)
        .order_by(StudentClassHistory.id.desc())
        .first()
    )

    if form.validate_on_submit():
        # Update student fields
        student.username = form.username.data
        student.first_name = form.first_name.data
        student.last_name = form.last_name.data
        student.middle_name = form.middle_name.data
        student.gender = form.gender.data
        # Update other fields as necessary

        # Update class in StudentClassHistory (create new entry if necessary)
        if student_class_history:
            student_class_history.class_name = form.class_name.data
        else:
            # If no history exists, create a new entry
            new_class_history = StudentClassHistory(
                student_id=student.id, session_id=session_id,  # Assuming current session is tracked
                class_name=form.class_name.data,
            )
            db.session.add(new_class_history)

        # Update username in the User model
        user = User.query.filter_by(id=student.user_id).first()
        user.username = form.username.data

        db.session.commit()
        flash("Student updated successfully!", "alert alert-success")
        return redirect(
            url_for("admins.students_by_class", session_id=session_id, class_name=form.class_name.data)
        )

    elif request.method == "GET":
        # Pre-fill form with student data
        form.username.data = student.username
        form.first_name.data = student.first_name
        form.last_name.data = student.last_name
        form.middle_name.data = student.middle_name
        form.gender.data = student.gender

        # Pre-fill the class name from StudentClassHistory if available
        if student_class_history:
            form.class_name.data = student_class_history.class_name
        else:
            form.class_name.data = "Unassigned"  # Default or handle no class case

    return render_template(
        "admin/students/edit_student.html", form=form, student=student
    )


@admin_bp.route("/admin/delete_student/<int:student_id>", methods=["POST"])
@login_required
def delete_student(student_id):
    """
    Delete a student and associated records.

    Args:
        student_id (int): The ID of the student to be deleted.

    Returns:
        redirect: Redirects to the student's class page.

    Raises:
        403: If the current user is not an admin.
        404: If the student with the given ID is not found.

    """
    if not current_user.is_admin:
        abort(403)  # Restrict access for non-admins

    form = DeleteForm()
    session_id = Session.query.filter_by(is_current=True).first().id

    if form.validate_on_submit():
        student = Student.query.get_or_404(student_id)
        student_class_history = (
            StudentClassHistory.query.filter_by(student_id=student.id)
            .order_by(StudentClassHistory.id.desc())
            .first()
        )

        try:
            # Delete all related results
            results = Result.query.filter_by(student_id=student.id).all()
            for result in results:
                db.session.delete(result)

            # Delete the associated User account
            user = User.query.get(student.user_id)
            if user:
                db.session.delete(user)

            # Delete all class history for the student
            class_history_records = StudentClassHistory.query.filter_by(
                student_id=student.id
            ).all()
            for history in class_history_records:
                db.session.delete(history)

            # Delete the student record itself
            db.session.delete(student)
            db.session.commit()

            flash(
                "Student and associated records deleted successfully!",
                "alert alert-success",
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting student: {e}", "alert alert-danger")

    # Redirect to the student's class page, using the latest class from history or default if not found
    class_name = (
        student_class_history.class_name if student_class_history else "Unassigned"
    )
    return redirect(url_for("admins.students_by_class", session_id=session_id, class_name=class_name))


""""
Subject Management Section

This section displays the basic view of the subject management page
The page displays the list of subjects and their details
It also provides links to edit, delete, and add subjects

    manage_subjects: Displays the list of subjects and their details
    edit_subject: Edits the details of a subject
    delete_subject: Deletes a subject

"""


@admin_bp.route("/admin/manage_subjects", methods=["GET", "POST"])
@login_required
def manage_subjects():
    """
    Route handler for managing subjects in the admin panel.

    This function handles the GET and POST requests for the "/admin/manage_subjects" route.
    It requires the user to be authenticated and have admin privileges.
    The function renders the subject administration template, which allows the admin to add and delete subjects.

    Returns:
        A rendered template for the subject administration page.
    """
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("auth.login"))

    form = SubjectForm()
    if form.validate_on_submit():
        subjects_input = form.name.data
        subject_names = [name.strip() for name in subjects_input.split(",")]

        for subject_name in subject_names:
            for section in form.section.data:
                # Check if the subject already exists for the given section
                existing_subject = Subject.query.filter_by(
                    name=subject_name, section=section
                ).first()
                if existing_subject is None:
                    subject = Subject(name=subject_name, section=section)
                    db.session.add(subject)
        db.session.commit()
        flash("Subject(s) added successfully!", "alert alert-success")
        return redirect(url_for("admins.manage_subjects"))

    subjects = Subject.query.order_by(Subject.section).all()
    subjects_by_section = {}
    for subject in subjects:
        if subject.section not in subjects_by_section:
            subjects_by_section[subject.section] = []
        subjects_by_section[subject.section].append(subject)

    delete_form = DeleteForm()
    return render_template(
        "admin/subjects/subject_admin.html",
        form=form,
        subjects_by_section=subjects_by_section,
        delete_form=delete_form,
    )


@admin_bp.route("/admin/edit_subject/<int:subject_id>", methods=["GET", "POST"])
@login_required
def edit_subject(subject_id):
    """
    Edit a subject with the given subject_id.

    Args:
        subject_id (int): The ID of the subject to be edited.

    Returns:
        A response object or a template with the form and subject data.

    Raises:
        404: If the subject with the given subject_id does not exist.
    """
    subject = Subject.query.get_or_404(subject_id)
    form = SubjectForm(obj=subject)
    if form.validate_on_submit():
        subject.name = form.name.data
        subject.section = form.section.data
        db.session.commit()

        # Update all related results with the new subject name and section
        results = Result.query.filter_by(subject_id=subject.id).all()
        for result in results:
            result.subject_name = subject.name
            result.subject_section = subject.section
        db.session.commit()

        flash("Subject updated successfully!", "alert alert-success")
        return redirect(url_for("admins.manage_subjects"))

    return render_template(
        "admin/subjects/edit_subject.html", form=form, subject=subject
    )


@admin_bp.route("/admin/delete_subject/<int:subject_id>", methods=["POST"])
def delete_subject(subject_id):
    """
    Delete a subject and its associated scores.

    Args:
        subject_id (int): The ID of the subject to be deleted.

    Returns:
        redirect: Redirects to the manage_subjects route.

    Raises:
        None

    """
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("auth.login"))

    form = DeleteForm()  # Instantiate the DeleteForm

    if form.validate_on_submit():
        try:
            # Find the subject
            subject = Subject.query.get_or_404(subject_id)

            # Delete all scores associated with the subject
            Result.query.filter_by(subject_id=subject_id).delete()

            # Delete the subject
            db.session.delete(subject)
            db.session.commit()

            flash(
                "Subject and associated scores deleted successfully!",
                "alert alert-success",
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting subject: {e}", "alert alert-danger")

    return redirect(url_for("admins.manage_subjects"))


""""
Result Management Section

Manages results by classes and sessions
This section allows the admin to view, edit, and delete results
It also provides the ability to generate broadsheets and download results

    select_term_session: Select the term and session for result management
    manage_results: Manage the results for a student
    broadsheet: Generate a broadsheet for a class
    download_broadsheet: Download a broadsheet for a class
    update_results: Update the results for a student
    calculate_results: Calculate the results for a student
    get_subjects_by_class_name: Get the subjects for a class
"""


@admin_bp.route("/select_term_session/<int:student_id>", methods=["GET", "POST"])
@login_required
def select_term_session(student_id):
    """
    Renders a form for selecting the term and session for managing results of a student.

    Args:
        student_id (int): The ID of the student.

    Returns:
        If the form is submitted successfully, redirects to the "manage_results" route with the selected term and session.
        Otherwise, renders the "select_term_session.html" template with the form, student, and available sessions.
    """
    student = Student.query.get_or_404(student_id)
    form = ResultForm()

    # Fetch available sessions from the database
    sessions = Session.query.all()
    form.session.choices = [(s.year, s.year) for s in sessions]

    if form.validate_on_submit():
        term = form.term.data
        session_year = form.session.data

        return redirect(
            url_for(
                "admins.manage_results",
                student_id=student.id,
                term=term,
                session_year=session_year,
            )
        )

    return render_template(
        "admin/results/select_term_session.html",
        form=form,
        student=student,
        sessions=sessions,
    )


@admin_bp.route("/manage_results/<int:student_id>", methods=["GET", "POST"])
@login_required
def manage_results(student_id):
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("auth.login"))

    try:
        student = Student.query.get_or_404(student_id)
        term = request.args.get("term")
        session_year = request.args.get("session")  # this is a string from the form

        # Ensure both term and session_year are provided
        if not term or not session_year:
            return redirect(
                url_for("admins.select_term_session", student_id=student.id)
            )

        # Query the Session table to get the session object using session_year (string)
        session = Session.query.filter_by(year=session_year).first()

        # If session is not found, return an error
        if not session:
            flash("Invalid session year selected", "alert alert-danger")
            return redirect(
                url_for("admins.select_term_session", student_id=student.id)
            )

        # Now get the class for the selected session using session.id
        student_class = StudentClassHistory.get_class_by_session(student.id, session.id)

        if not student_class:
            flash("No class found for the selected session", "alert alert-danger")
            return redirect(
                url_for("admins.select_term_session", student_id=student.id)
            )

        # Initialize the result form with the term and session pre-filled
        form = ResultForm(term=term, session=session_year)

        student_class_history = StudentClassHistory.query.filter_by(
            student_id=student.id, session_id=session.id  # Use session.id here
        ).first()

        subjects = get_subjects_by_class_name(student_class_history)

        if form.validate_on_submit():
            update_results(student, subjects, term, session_year, form)
            flash("Results updated successfully", "alert alert-success")
            return redirect(
                url_for(
                    "admins.manage_results",
                    student_id=student.id,
                    term=term,
                    session=session_year,
                )
            )

        # Calculate and display results
        results, grand_total, average, cumulative_average, results_dict = (
            calculate_results(student.id, term, session_year)
        )

        return render_template(
            "admin/results/manage_results.html",
            student=student,
            subjects=subjects,
            results=results,
            grand_total=grand_total,
            average=average,
            cumulative_average=cumulative_average,
            results_dict=results_dict,
            form=form,
            selected_term=term,
            selected_session=session_year,
            student_class=student_class,  # Pass the class to the template
        )

    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f"Database error: {str(e)}", "alert alert-danger")
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "alert alert-danger")

    return redirect(url_for("admin.index"))


# @admin_bp.route("/broadsheet/<string:class_name>", methods=["GET", "POST"])
# @login_required
# def broadsheet(class_name):
#    if not current_user.is_authenticated or not current_user.is_admin:
#        return redirect(url_for("auth.login"))

#    form = SelectTermSessionForm()
#    term = form.term.data if form.term.data else request.args.get("term")
#    session = form.session.data if form.session.data else request.args.get("session")

#    students = Student.query.filter_by(class_name=class_name).all()
#    subjects = get_subjects_by_class_name(class_name=class_name)

#    broadsheet_data = []
#    subject_averages = {subject.id: {"total": 0, "count": 0} for subject in subjects}

#    for student in students:
#        student_results = {
#            "student": student,
#            "results": {
#                subject.id: {
#                    "class_assessment": "",
#                    "summative_test": "",
#                    "exam": "",
#                    "total": "",
#                    "grade": "",
#                    "remark": "",
#                }
#                for subject in subjects
#            },
#            "grand_total": "",
#            "average": "",
#            "position": "",
#        }
#        results = Result.query.filter_by(
#            student_id=student.id, term=term, session=session
#        ).all()

#        grand_total = 0
#        non_zero_subjects = 0
#        for result in results:
#            if result.subject_id in student_results["results"]:
#                student_results["results"][result.subject_id] = {
#                    "class_assessment": (
#                        result.class_assessment
#                        if result.class_assessment is not None
#                        else ""
#                    ),
#                    "summative_test": (
#                        result.summative_test
#                        if result.summative_test is not None
#                        else ""
#                    ),
#                    "exam": result.exam if result.exam is not None else "",
#                    "total": (
#                        result.total
#                        if result.total is not None and result.total > 0
#                        else ""
#                    ),
#                    "grade": result.grade if result.grade is not None else "",
#                    "remark": result.remark if result.remark is not None else "",
#                }
#                if result.total > 0:
#                    grand_total += result.total
#                    non_zero_subjects += 1
#                    subject_averages[result.subject_id]["total"] += result.total
#                    subject_averages[result.subject_id]["count"] += 1
#                student_results["position"] = result.position

#        # Set grand_total and average with blank space if they are zero
#        student_results["grand_total"] = grand_total if grand_total > 0 else ""
#        average = grand_total / non_zero_subjects if non_zero_subjects > 0 else 0
#        student_results["average"] = round(average, 1) if average > 0 else float("-inf")

#        # student_results["average"] = round(average, 1) if average > 0 else ""

#        # average = grand_total / non_zero_subjects if non_zero_subjects > 0 else 0
#        # student_results["grand_total"] = grand_total
#        # student_results["average"] = round(average, 1)
#        broadsheet_data.append(student_results)

#    # Calculate class averages for each subject
#    for subject_id, values in subject_averages.items():
#        values["average"] = (
#            round(values["total"] / values["count"], 1) if values["count"] > 0 else 0
#        )

#    # Sort students by their average
#    broadsheet_data.sort(key=lambda x: x["average"], reverse=True)

#    return render_template(
#        "admin/results/broadsheet.html",
#        form=form,
#        students=students,
#        subjects=subjects,
#        broadsheet_data=broadsheet_data,
#        subject_averages=subject_averages,
#        class_name=class_name,
#    )


# @admin_bp.route("/download_broadsheet/<string:class_name>")
# @login_required
# def download_broadsheet(class_name):
#    if not current_user.is_authenticated or not current_user.is_admin:
#        return redirect(url_for("auth.login"))

#    term = request.args.get("term")
#    session = request.args.get("session")

#    students = Student.query.filter_by(class_name=class_name).all()
#    subjects = get_subjects_by_class_name(class_name=class_name)

#    broadsheet_data = []
#    subject_averages = {subject.id: {"total": 0, "count": 0} for subject in subjects}

#    for student in students:
#        student_results = {
#            "student": student,
#            "results": {subject.id: None for subject in subjects},
#            "grand_total": 0,
#            "average": 0,
#            "position": None,
#        }
#        results = Result.query.filter_by(
#            student_id=student.id, term=term, session=session
#        ).all()

#        grand_total = 0
#        non_zero_subjects = 0
#        for result in results:
#            student_results["results"][result.subject_id] = result
#            grand_total += result.total
#            if result.total > 0:
#                non_zero_subjects += 1
#                subject_averages[result.subject_id]["total"] += result.total
#                subject_averages[result.subject_id]["count"] += 1
#            student_results["position"] = result.position

#        average = grand_total / non_zero_subjects if non_zero_subjects > 0 else 0
#        student_results["grand_total"] = grand_total
#        student_results["average"] = round(average, 1)
#        broadsheet_data.append(student_results)

#    # Calculate class averages for each subject
#    for subject_id, values in subject_averages.items():
#        values["average"] = (
#            round(values["total"] / values["count"], 1) if values["count"] > 0 else 0
#        )

#    # Sort students by their average in descending order
#    broadsheet_data.sort(key=lambda x: x["average"], reverse=True)

#    # Create Excel file
#    workbook = openpyxl.Workbook()
#    sheet = workbook.active
#    sheet.title = f"Broadsheet_{class_name}_{term}"

#    # Define styles
#    header_font = Font(bold=True, size=14, name="Times New Roman")
#    sub_header_font = Font(bold=True, size=12, name="Times New Roman")
#    cell_font = Font(size=12, name="Times New Roman")
#    border = Border(
#        left=Side(style="thin"),
#        right=Side(style="thin"),
#        top=Side(style="thin"),
#        bottom=Side(style="thin"),
#    )
#    alignment = Alignment(horizontal="left", vertical="center")

#    # Add context information at the top
#    sheet.append([f"Broadsheet for {class_name} - Term: {term}, Session: {session}"])
#    sheet.append([f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
#    sheet.append([])  # Blank row for separation

#    # Write headers
#    headers = ["Subjects"]
#    for student_data in broadsheet_data:
#        student = student_data["student"]
#        headers.extend([f"{student.first_name} {student.last_name}", "", "", ""])
#    headers.append("Class Average")
#    sheet.append(headers)

#    sub_headers = [""]
#    for _ in broadsheet_data:
#        sub_headers.extend(["C/A", "S/T", "Exam", "Total"])
#    sub_headers.append("")
#    sheet.append(sub_headers)

#    for cell in sheet["1:1"]:
#        cell.font = header_font
#    for cell in sheet["2:2"]:
#        cell.font = sub_header_font
#    for cell in sheet["3:3"]:
#        cell.font = cell_font
#    sheet.merge_cells("A1:A2")

#    # Write data
#    for subject in subjects:
#        row = [subject.name]
#        for student_data in broadsheet_data:
#            result = student_data["results"][subject.id]
#            if result:
#                row.extend(
#                    [
#                        result.class_assessment,
#                        result.summative_test,
#                        result.exam,
#                        result.total,
#                    ]
#                )
#            else:
#                row.extend(["-", "-", "-", "-"])
#        row.append(subject_averages[subject.id]["average"])
#        sheet.append(row)

#    # Write grand totals, averages, and positions
#    sheet.append(
#        ["Grand Total"]
#        + sum(
#            [
#                ["", "", "", student_data["grand_total"]]
#                for student_data in broadsheet_data
#            ],
#            [],
#        )
#        + [""]
#    )
#    sheet.append(
#        ["Average"]
#        + sum(
#            [["", "", "", student_data["average"]] for student_data in broadsheet_data],
#            [],
#        )
#        + [""]
#    )
#    sheet.append(
#        ["Position"]
#        + sum(
#            [
#                ["", "", "", student_data["position"]]
#                for student_data in broadsheet_data
#            ],
#            [],
#        )
#        + [""]
#    )

#    # Set page orientation to landscape
#    sheet.page_setup.orientation = sheet.ORIENTATION_LANDSCAPE

#    # Apply styles
#    for row in sheet.iter_rows(
#        min_row=1, max_row=sheet.max_row, min_col=1, max_col=sheet.max_column
#    ):
#        for cell in row:
#            cell.border = border
#            cell.alignment = alignment
#            cell.font = cell_font

#    # Adjust column widths
#    for col in sheet.columns:
#        max_length = 0
#        column = col[0].column_letter
#        for cell in col:
#            try:
#                if len(str(cell.value)) > max_length:
#                    max_length = len(cell.value)
#            except:
#                pass
#        adjusted_width = max_length + 2
#        sheet.column_dimensions[column].width = adjusted_width

#    # Save to a bytes buffer
#    output = BytesIO()
#    workbook.save(output)
#    output.seek(0)

#    return Response(
#        output,
#        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#        headers={
#            "Content-Disposition": f"attachment;filename=Broadsheet_{class_name}_{term}_{session}.xlsx"
#        },
#    )
