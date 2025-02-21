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
import re
from datetime import datetime
from werkzeug.datastructures import MultiDict
from flask_sqlalchemy import pagination
from sqlalchemy import func, or_
from urllib.parse import unquote
from sqlalchemy.orm import joinedload
from flask_wtf.csrf import CSRFError, generate_csrf
from flask_login import login_required, current_user
from sqlalchemy import case
from flask import (
    abort,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    request,
    Response,
    jsonify,
    current_app as app,
)

from . import admin_bp
from ..helpers import (
    get_subjects_by_class_name,
    update_results,
    calculate_results,
    db,
    random,
    string,
    populate_form_with_results,
    generate_excel_broadsheet,
    prepare_broadsheet_data,
    calculate_grade,
    generate_remark,
    group_students_by_class,
    save_result,
    generate_employee_id,
)
from ..models import (
    Student,
    User,
    Subject,
    Result,
    Session,
    StudentClassHistory,
    RoleEnum,
    Classes,
    Teacher,
    class_teacher,
    class_subject,
    teacher_subject,
    FeePayment,
)

from ..auth.forms import (
    EditStudentForm,
    ResultForm,
    SubjectForm,
    DeleteForm,
    SessionForm,
    ApproveForm,
    classForm,
    ClassesForm,
    ManageResultsForm,
    StudentRegistrationForm,
    TeacherForm,
    AssignSubjectToClassForm,
    AssignSubjectToTeacherForm,
    AssignTeacherToClassForm,
)

@admin_bp.errorhandler(CSRFError)
def handle_csrf_error(e):
    app.logger.warning(f"CSRF error: {e.description}")
    flash("The form submission has expired. Please try again.", "alert-danger")
    return redirect(url_for("admins.admin_dashboard"))


@admin_bp.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Server Error: {error}")
    return redirect(url_for("admins.admin_dashboard"))


@admin_bp.errorhandler(404)
def not_found_error(error):
    app.logger.warning(f"404 Error: {error}")
    return redirect(url_for("admins.admin_dashboard"))


@admin_bp.before_request
@login_required
def admin_before_request():
    if not current_user.role == RoleEnum.ADMIN:
        flash("You are not authorized to access this page.", "alert-danger")
        app.logger.warning(
            f"Unauthorized access attempt by user {current_user.username}"
        )
        return redirect(url_for("main.index"))

@admin_bp.after_request
def add_csrf_token(response):
    csrf_token = generate_csrf()
    response.headers['X-CSRFToken'] = csrf_token
    return response

@admin_bp.route("/dashboard")
def admin_dashboard():
    app.logger.info(f"Admin dashboard accessed by user {current_user.username}")
    return render_template("admin/index.html")


@admin_bp.route("/manage_sessions", methods=["GET", "POST"])
@login_required
def manage_sessions():
    if not current_user.role == RoleEnum.ADMIN:
        abort(403)  # Restrict access for non-admins

    form = SessionForm()

    # Fetch all sessions and populate choices
    sessions = Session.query.all()
    form.session.choices = [(session.id, session.year) for session in sessions]

    # Include term options
    terms = ["First Term", "Second Term", "Third Term"]
    form.term.choices = [(term, term) for term in terms]

    # Retrieve current session and term
    current_session, current_term = Session.get_current_session_and_term(include_term=True)

    if form.validate_on_submit():
        session_id = form.session.data
        term = form.term.data

        # Update the session and term in the database
        updated_session = Session.set_current_session(session_id, term)

        if updated_session:
            flash(
                f"Current session set to {updated_session.year} ({term}).",
                "alert-success",
            )
        else:
            flash("Failed to update the current session and term.", "alert-danger")

        return redirect(url_for("admins.manage_sessions"))

    return render_template(
        "admin/manage_sessions.html",
        form=form,
        current_session=current_session.year,
        current_term=current_term,
    )


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

from collections import defaultdict

@admin_bp.route("/register/student", methods=["GET", "POST"])
def add_student():
    form = StudentRegistrationForm()
    current_session = Session.get_current_session_and_term(include_term=False)

    # Populate the class selection dynamically
    form.class_id.choices = [
        (cls.id, f"{cls.name}")
        for cls in Classes.query.order_by(Classes.hierarchy).all()
    ]

    try:
        if form.validate_on_submit():

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
                approved=False,
            )
            db.session.add(student)
            db.session.flush()  # Ensure the student gets an ID before generating reg_no

            # Generate reg_no and use it as the temporary password
            student.reg_no = f"AAIS/0559/{student.id:03}"

            # Create a User object for login credentials
            user = User(username=student.reg_no, role=RoleEnum.STUDENT)
            user.set_password(student.reg_no)
            student.user = user

            db.session.add(user)

            # Link the student to the selected class via StudentClassHistory
            class_id = form.class_id.data
            class_history = StudentClassHistory(
                student_id=student.id,
                session_id=current_session.id,
                class_id=class_id,
            )
            db.session.add(class_history)

            # Commit all changes (student, user, and class history)
            db.session.commit()

            # Log success and inform the user
            app.logger.info(f"Student registered successfully: {student.reg_no}")
            flash(
                f"Student registered successfully. Registration Number: {student.reg_no}.",
                "alert alert-success",
            )
            return redirect(url_for("admins.add_student"))

    except Exception as e:
        db.session.rollback()  # Rollback the session on error
        app.logger.error(f"Error registering student: {str(e)}")
        flash("An error occurred. Please try again later.", "alert alert-danger")

    return render_template(
        "admin/students/add_student.html",
        title="Register",
        form=form,
        school_name="Aunty Anne's International School",
    )

@admin_bp.route("/students/<string:action>", methods=["GET", "POST"])
@login_required
def students(action):
    # Restrict access for non-admin users
    if not current_user.role == RoleEnum.ADMIN:
        abort(403)

    # Get current session and term
    current_session, current_term = Session.get_current_session_and_term(include_term=True)

    if not current_session:
        app.logger.error("No active session found.")
        return jsonify({"error": "No active session found."}), 400

    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Customize the number of students per page

    # Fetch students with their class hierarchy for the current session
    students_query = (
        db.session.query(Student, Classes.name.label("class_name"), Classes.hierarchy)
        .join(StudentClassHistory, Student.id == StudentClassHistory.student_id)
        .join(Classes, StudentClassHistory.class_id == Classes.id)
        .filter(StudentClassHistory.session_id == current_session.id)
        .order_by(Classes.hierarchy)  # Order by the hierarchy field in the Classes model
    )

    # Paginate results
    paginated_students = students_query.paginate(page=page, per_page=per_page, error_out=False)

    # Group students by class
    students_classes = group_students_by_class(paginated_students.items)

    # Handle AJAX requests
    if request.args.get('ajax', type=bool):
        return render_template(
            "ajax/students/_students_table.html",
            students_classes=students_classes,
            pagination=paginated_students,
            action=action,
        )

    # Render the full page for standard requests
    form = DeleteForm()
    return render_template(
        "admin/students/view_students.html",
        students_classes=students_classes,
        pagination=paginated_students,
        current_session=current_session.year,
        session = current_session,
        current_term=current_term,
        action=action,
        form=form,
    )



@admin_bp.route("/edit_student/<int:student_id>/<string:action>", methods=["GET", "POST"])
@login_required
def edit_student(student_id, action):
    """
    Edit a student's information.

    Args:
        student_id (int): The ID of the student to be edited.

    Returns:
        A rendered template for editing a student's information.

    Raises:
        403: If the current user is not an admin.

    """
    if not current_user.role == RoleEnum.ADMIN:
        abort(403)  # Restrict access for non-admins

    form = EditStudentForm()
    student = Student.query.get_or_404(student_id)
    current_session = Session.get_current_session_and_term(include_term=False)

    if not current_session:
        flash("No current session found.", "alert-danger")
        return redirect(url_for("admins.students", action=action))

    # Populate the class selection dynamically
    form.class_id.choices = [
        (cls.id, f"{cls.name} ({cls.section})")
        for cls in Classes.query.order_by(Classes.hierarchy).all()
    ]

    # Retrieve the latest class history for the student in the current session
    student_class_history = (
        StudentClassHistory.query.filter_by(
            student_id=student.id, session_id=current_session.id
        )
        .order_by(StudentClassHistory.id.desc())
        .first()
    )

    if form.validate_on_submit():
        # Update student fields
        student.reg_no = form.reg_no.data
        student.first_name = form.first_name.data
        student.last_name = form.last_name.data
        student.middle_name = form.middle_name.data
        student.gender = form.gender.data

        # Link the student to the selected class via StudentClassHistory
        class_id = form.class_id.data

        # Update the class history for the current session
        if student_class_history:
            student_class_history.class_id = form.class_id.data
        else:
            # Create a new entry if no history exists for the current session
            new_class_history = StudentClassHistory(
                student_id=student.id,
                session_id=current_session.id,
                class_id=form.class_id.data,
            )
            db.session.add(new_class_history)

        # Update username in the User model
        user = User.query.filter_by(id=student.user_id).first()
        user.username = form.reg_no.data

        db.session.commit()
        flash("Student updated successfully!", "alert-success")
        return redirect(
            url_for(
                "admins.students",
                session_id=current_session.id,
                action=action,
            )
        )

    elif request.method == "GET":
        # Pre-fill form with student data
        form.reg_no.data = student.reg_no
        form.first_name.data = student.first_name
        form.last_name.data = student.last_name
        form.middle_name.data = student.middle_name
        form.gender.data = student.gender

        # Pre-fill the class name from StudentClassHistory if available
        if student_class_history:
            form.class_id.data = student_class_history.class_id

    return render_template(
        "admin/students/edit_student.html", form=form, student=student, action=action
    )

@admin_bp.route("/select_class/<string:action>", methods=["GET", "POST"])
@login_required
def select_class(action):
    class_form = classForm()

    # Populate the class selection dynamically
    class_form.class_name.choices = [
        (cls.name, f"{cls.name}")
        for cls in Classes.query.order_by(Classes.hierarchy).all()
    ]


    if class_form.validate_on_submit():
        class_name = class_form.class_name.data

        app.logger.info(f"{class_name}")

        # Redirect to the students_by_class route with class_name as a URL path segment
        return redirect(
            url_for(
                "admins.students_by_class",
                class_name=class_name,
                action=action
            )
        )

    return render_template(
        "admin/classes/select_class.html",
        class_form=class_form,
        action=action
    )

@admin_bp.route("/students_by_class/<string:class_name>/<string:action>", methods=["GET", "POST"])
@login_required
def students_by_class(class_name, action):
    """
    Retrieve students by class for the current session with pagination.

    This function retrieves students in a specific class for the current session and term.
    It also handles the delete functionality.

    Returns:
        render_template: The rendered template with the students, session, class name, and form.
    """
    class_name = unquote(class_name).strip()

    if not class_name:
        flash("Invalid class name provided.", "alert-danger")
        return redirect(url_for("admins.select_class", action=action))

    # Get current session and term directly from the Session model
    current_session, current_term = Session.get_current_session_and_term(include_term=True)

    class_record = Classes.query.filter_by(name=class_name).first()
    if not class_record:
        return jsonify({"error": f"Class '{class_name}' not found."}), 404

    # Initialize the form for deletion
    form = DeleteForm()

    # Fetch the student history filtered by session and class with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of students per page
    student_histories_pagination = StudentClassHistory.query.filter(
        StudentClassHistory.session_id == current_session.id,
        StudentClassHistory.class_id == class_record.id
    ).paginate(page=page, per_page=per_page)

    # Extract students from the pagination object
    student_histories = student_histories_pagination.items
    students = [history.student for history in student_histories]

    if not students and page == 1:
        flash(
            f"No students found in {class_name} for {current_session.year} - {current_term}",
            "alert-danger",
        )
        return redirect(url_for("admins.select_class", action=action))

    return render_template(
        "admin/classes/students_by_class.html",
        students=students,
        session=current_session.year,
        current_session=current_session.year,
        class_name=class_name,
        form=form,
        current_term=current_term,
        action=action,
        pagination=student_histories_pagination,
    )

@admin_bp.route("/promote_student/<string:class_name>/<int:student_id>/<string:action>", methods=["POST"])
@login_required
def promote_student(class_name, student_id, action):
    """
    Promotes a student to the next class in the same session or the next academic session.
    Ensures only one class record exists per session.
    """
    if not current_user.role == RoleEnum.ADMIN:
        abort(403)  # Restrict access for non-admins

    student = Student.query.get_or_404(student_id)
    current_session = Session.get_current_session()
    class_name = unquote(class_name).strip()

    if not current_session:
        flash("No current session available for promotion.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    # Get the current class object
    current_class = Classes.query.filter_by(name=class_name).first()
    if not current_class:
        flash("Class not found in the system.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    # Determine the session for the promotion
    session_choice = request.form.get("session_choice", "next")  # Default to 'next' session
    if session_choice == "current":
        target_session = current_session
    elif session_choice == "next":
        target_session = Session.query.filter(Session.year > current_session.year).order_by(Session.year.asc()).first()
        if not target_session:
            flash("No next academic session available for promotion.", "alert-danger")
            return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))
    else:
        flash("Invalid session choice for promotion.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    # Get the next class based on the hierarchy
    next_class = Classes.get_next_class(current_class.hierarchy)
    if not next_class:
        flash("This student has completed the highest class.", "alert-warning")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    # Check if a record already exists for the target session
    existing_record = StudentClassHistory.query.filter_by(
        student_id=student.id, session_id=target_session.id
    ).first()

    if existing_record:
        # Update the existing record to the new class
        existing_record.class_id = next_class.id
    else:
        # Create a new StudentClassHistory record
        new_class_history = StudentClassHistory(
            student_id=student.id, session_id=target_session.id, class_id=next_class.id
        )
        db.session.add(new_class_history)

    db.session.commit()

    session_label = "current session" if session_choice == "current" else f"{target_session.year}"
    flash(
        f"{student.first_name} has been promoted to {next_class.name} in the {session_label}.",
        "alert-success",
    )
    return redirect(
        url_for(
            "admins.students_by_class",
            class_name=next_class.name,
            action=action,
            student_id=student.id,
        )
    )

@admin_bp.route("/demote_student/<string:class_name>/<int:student_id>/<string:action>", methods=["POST"])
@login_required
def demote_student(class_name, student_id, action):
    """
    Demotes a student to the previous class in the same session or the next academic session.
    Ensures only one class record exists per session.
    """
    if not current_user.role == RoleEnum.ADMIN:
        abort(403)  # Restrict access for non-admins

    student = Student.query.get_or_404(student_id)
    current_session = Session.get_current_session_and_term(include_term=False)
    class_name = unquote(class_name).strip()

    if not current_session:
        flash("No current session available for demotion.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    # Get the current class object
    current_class = Classes.query.filter_by(name=class_name).first()
    if not current_class:
        flash("Class not found in the system.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    # Determine the session for the demotion
    session_choice = request.form.get("session_choice", "next")  # Default to 'next' session
    if session_choice == "current":
        target_session = current_session
    elif session_choice == "next":
        target_session = Session.query.filter(Session.year > current_session.year).order_by(Session.year.asc()).first()
        if not target_session:
            flash("No next academic session available for demotion.", "alert-danger")
            return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))
    else:
        flash("Invalid session choice for demotion.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    # Get the previous class based on the hierarchy
    previous_class = Classes.get_previous_class(current_class.hierarchy)
    if not previous_class:
        flash("This student is already in the lowest class.", "alert-warning")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    # Check if a record already exists for the target session
    existing_record = StudentClassHistory.query.filter_by(
        student_id=student.id, session_id=target_session.id
    ).first()

    if existing_record:
        # Update the existing record to the new class
        existing_record.class_id = previous_class.id
    else:
        # Create a new StudentClassHistory record
        new_class_history = StudentClassHistory(
            student_id=student.id, session_id=target_session.id, class_id=previous_class.id
        )
        db.session.add(new_class_history)

    db.session.commit()

    session_label = "current session" if session_choice == "current" else f"{target_session.year}"
    flash(
        f"{student.first_name} has been demoted to {previous_class.name} in the {session_label}.",
        "alert-success",
    )
    return redirect(
        url_for(
            "admins.students_by_class",
            class_name=previous_class.name,
            action=action,
            student_id=student.id,
        )
    )


@admin_bp.route("/delete_student_record/<string:class_name>/<int:student_id>/<string:action>", methods=["POST"])
@login_required
def delete_student_record(class_name, student_id, action):
    """
    Deletes a student's class record for the current session.

    Args:
        student_id (int): The ID of the student whose record is to be deleted.

    Returns:
        redirect: Redirects to the manage students page or class-specific view.

    Raises:
        403: If the current user is not an admin.
        404: If the student or current session record is not found.
    """
    if not current_user.role == RoleEnum.ADMIN:
        abort(403)  # Restrict access for non-admins

    # Check if the student exists
    student = Student.query.get_or_404(student_id)

    class_name = unquote(class_name).strip()

    # Get the current session dynamically
    current_session = Session.get_current_session_and_term(include_term=False)
    if not current_session:
        flash("No current session available.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    # Find the student's class record for the current session
    class_record = StudentClassHistory.query.filter_by(
        student_id=student.id, session_id=current_session.id
    ).first()

    if not class_record:
        flash(
            f"No class record found for {student.first_name} in the current session.",
            "alert-danger",
        )
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    # Delete the class record
    db.session.delete(class_record)
    db.session.commit()

    flash(
        f"Class record for {student.first_name} in session {current_session.year} has been deleted.",
        "alert-success",
    )
    return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

# @admin_bp.route("/delete_student/<int:student_id>/<string:action>", methods=["POST"])
# @login_required
# def delete_student(student_id, action):
#     """
#     Delete a student and associated records.

#     Args:
#         student_id (int): The ID of the student to be deleted.

#     Returns:
#         redirect: Redirects to the student's class page.

#     Raises:
#         403: If the current user is not an admin.
#         404: If the student with the given ID is not found.

#     """
#     if not current_user.role == RoleEnum.ADMIN:
#         abort(403)  # Restrict access for non-admins

#     form = DeleteForm()
#     session_id = Session.query.filter_by(is_current=True).first().id

#     if form.validate_on_submit():
#         student = Student.query.get_or_404(student_id)
#         student_class_history = (
#             StudentClassHistory.query.filter_by(student_id=student.id)
#             .order_by(StudentClassHistory.id.desc())
#             .first()
#         )

#         try:
#             # Delete all related results
#             results = Result.query.filter_by(student_id=student.id).all()
#             for result in results:
#                 db.session.delete(result)

#             # Delete the associated User account
#             user = User.query.get(student.user_id)
#             if user:
#                 db.session.delete(user)

#             # Delete all class history for the student
#             class_history_records = StudentClassHistory.query.filter_by(
#                 student_id=student.id
#             ).all()
#             for history in class_history_records:
#                 db.session.delete(history)

#             # Delete the student record itself
#             db.session.delete(student)
#             db.session.commit()

#             flash(
#                 "Student and associated records deleted successfully!",
#                 "alert-success",
#             )
#         except Exception as e:
#             db.session.rollback()
#             flash(f"Error deleting student: {e}", "alert-danger")

#     # Redirect to the student's class page, using the latest class from history or default if not found
#     class_name = (
#         student_class_history.class_ref.name
#         if student_class_history and student_class_history.class_ref
#         else "Unassigned"
#     )
#     return redirect(
#         url_for(
#             "admins.students", session_id=session_id, action=action, class_name=class_name,
#         )
#     )

@admin_bp.route("/delete_student/<int:student_id>/<string:action>", methods=["POST"])
@login_required
def delete_student(student_id, action):
    if not current_user.role == RoleEnum.ADMIN:
        abort(403)

    form = DeleteForm()
    session_id = Session.query.filter_by(is_current=True).first().id
    class_name = "Unassigned"  # Default value

    if form.validate_on_submit():
        student = Student.query.get_or_404(student_id)
        student_class_history = (
            StudentClassHistory.query.filter_by(student_id=student.id)
            .order_by(StudentClassHistory.id.desc())
            .first()
        )

        # Get class name BEFORE any deletions (while session is active)
        if student_class_history and student_class_history.class_ref:
            class_name = student_class_history.class_ref.name

        try:
            # Delete all related results
            results = Result.query.filter_by(student_id=student.id).all()
            for result in results:
                db.session.delete(result)

            # Delete associated User account
            user = db.session.get(User, student.user_id)
            if user:
                db.session.delete(user)

            # Delete class history records
            class_history_records = StudentClassHistory.query.filter_by(
                student_id=student.id
            ).all()
            for history in class_history_records:
                db.session.delete(history)

            # Delete the student
            db.session.delete(student)
            db.session.commit()

            flash("Student and records deleted successfully!", "alert-success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting student: {e}", "alert-danger")
            # Optionally re-get class_name if deletion failed (if needed)

    # Redirect using the pre-fetched class_name
    return redirect(url_for("admins.students", session_id=session_id, action=action, class_name=class_name))


""""
Subject Management Section

This section displays the basic view of the subject management page
The page displays the list of subjects and their details
It also provides links to edit, delete, and add subjects

    manage_subjects: Displays the list of subjects and their details
    edit_subject: Edits the details of a subject
    delete_subject: Deletes a subject

"""


@admin_bp.route("/manage_subjects", methods=["GET", "POST"])
@login_required
def manage_subjects():
    """
    Route handler for managing subjects in the admin panel.
    Allows adding and deactivating subjects for the current session.
    """
    if not current_user.role == RoleEnum.ADMIN:
        abort(403)

    form = SubjectForm()
    if form.validate_on_submit():
        subjects_input = form.name.data
        subject_names = [name.strip() for name in subjects_input.split(",")]

        for subject_name in subject_names:
            for section in form.section.data:
                existing_subject = Subject.query.filter_by(
                    name=subject_name, section=section, deactivated=False
                ).first()
                if existing_subject is None:
                    subject = Subject(name=subject_name, section=section)
                    db.session.add(subject)
        db.session.commit()
        flash("Subject(s) added successfully!", "alert-success")
        return redirect(url_for("admins.manage_subjects"))

    # Check for deactivation request
    if request.method == "POST" and "deactivate_subject_id" in request.form:
        subject_id = int(request.form.get("deactivate_subject_id"))
        subject = Subject.query.get(subject_id)
        if subject:
            subject.deactivated = True
            db.session.commit()
            flash(
                f"Subject '{subject.name}' has been deactivated.", "alert-warning"
            )
        return redirect(url_for("admins.manage_subjects"))

    # Display only active subjects for the current session
    subjects = (
        Subject.query.order_by(Subject.section).all()
    )
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


@admin_bp.route("/edit_subject/<int:subject_id>", methods=["GET", "POST"])
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

        flash("Subject updated successfully!", "alert-success")
        return redirect(url_for("admins.manage_subjects"))

    return render_template(
        "admin/subjects/edit_subject.html", form=form, subject=subject
    )


@admin_bp.route("/delete_subject/<int:subject_id>", methods=["POST"])
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
    if not current_user.role == RoleEnum.ADMIN:
        abort(403)

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
                "alert-success",
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting subject: {e}", "alert-danger")

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
@admin_bp.route("/manage_results/<string:class_name>/<int:student_id>/<string:action>", methods=["GET"])
@login_required
def manage_results(class_name, student_id, action):
    student = Student.query.get_or_404(student_id)
    class_name = unquote(class_name).strip()

    # Get the current session and term directly from the Session model
    current_session, current_term = Session.get_current_session_and_term(include_term=True)

    # Get subjects based on class and session (with deactivated subjects based on session year)
    subjects = get_subjects_by_class_name(
        class_name, include_deactivated=(current_session.year == "2023/2024")
    )

    # Initialize the forms
    result_form = ResultForm(term=current_term, session=current_session.year)
    form = ManageResultsForm()

    # Fetch results in a single query and map by subject_id
    results = Result.query.filter_by(
        student_id=student.id, term=current_term, session=current_session.year
    ).all()
    results_dict = {result.subject_id: result for result in results}

    # Populate form with existing results for GET requests
    populate_form_with_results(form, subjects, results_dict)

    # Default details for the results page
    details = {
        "grand_total": None,
        "last_term_average": None,
        "average": None,
        "cumulative_average": None,
        "subjects_offered": None,
        "next_term_begins": None,
        "position": None,
        "date_issued": None,
        "principal_remark": None,
        "teacher_remark": None,
    }

    if results:
        first_result = results[0]
        details.update({
            "grand_total": first_result.grand_total,
            "last_term_average": first_result.last_term_average,
            "average": first_result.term_average,
            "cumulative_average": first_result.cumulative_average,
            "subjects_offered": first_result.subjects_offered,
            "next_term_begins": first_result.next_term_begins,
            "position": first_result.position,
            "date_issued": first_result.date_issued,
            "principal_remark": first_result.principal_remark,
            "teacher_remark": first_result.teacher_remark,
        })

    # Render the template
    return render_template(
        "admin/results/manage_results.html",
        student=student,
        subjects=subjects,
        form=form,
        term=current_term,
        subject_results=zip(subjects, form.subjects),
        class_name=class_name,
        session=current_session.year,
        results_dict=results_dict,
        results=results,
        action=action,
        school_name="Aunty Anne's International School",
        **details,  # Unpack the details dictionary
    )


@admin_bp.route("/update_result/<string:class_name>/<int:student_id>/<string:action>", methods=["POST"])
@login_required
def update_result(class_name, student_id, action):
    student = Student.query.get_or_404(student_id)
    class_name = unquote(class_name).strip()

    # Get the current session and term directly from the Session model
    current_session, current_term = Session.get_current_session_and_term(include_term=True)

    # Initialize the forms
    result_form = ResultForm(term=current_term, session=current_session.year)
    form = ManageResultsForm()

    # Fetch results in a single query and map by subject_id
    results = Result.query.filter_by(
        student_id=student.id, term=current_term, session=current_session.year
    ).all()
    results_dict = {result.subject_id: result for result in results}

    # Handle form submission
    if form.validate_on_submit():
        try:
            # Update results in the database
            update_results(student, current_term, current_session.year, form, result_form)
            flash("Results updated successfully.", "alert-success")
            app.logger.info(
                f"Results for student {student.id} updated for term {current_term}, session {current_session.year}."
            )
            return redirect(
                url_for(
                    "admins.manage_results",
                    class_name=class_name,
                    student_id=student.id,
                    action=action,
                )
            )
        except Exception as e:
            # Log errors and flash a failure message
            app.logger.error(
                f"Error updating results for student {student.id}: {str(e)}"
            )
            flash(
                "An error occurred while updating the results. Please try again.",
                "alert-danger",
            )

    # Log validation errors if POST request fails
    elif request.method == "POST":
        app.logger.error(f"Form validation failed: {form.errors}")

    # Render the template if POST fails
    return redirect(
        url_for(
            "admins.manage_results",
            class_name=class_name,
            student_id=student.id,
            action=action,
        )
    )


@admin_bp.route("/broadsheet/<string:class_name>/<string:action>", methods=["GET", "POST"])
@login_required
def broadsheet(class_name, action):
    try:
        # Decode and normalize class_name
        class_name = unquote(class_name).strip()
        form = classForm()

        # Get the current session and term directly from the Session model
        current_session, current_term = Session.get_current_session_and_term(include_term=True)

        if not current_session or not current_term:
            flash("Current session or term is not set", "alert-danger")
            return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

        # Fetch the class record
        class_record = Classes.query.filter_by(name=class_name).first()

        # # Fetch students and subjects based on class_name from StudentClassHistory
        student_class_histories = (
            StudentClassHistory.query.filter(
                StudentClassHistory.session_id == current_session.id,
                StudentClassHistory.class_id == class_record.id
            )
            .options(joinedload(StudentClassHistory.student))
            .all()
        )

        students = [history.student for history in student_class_histories]
        subjects = get_subjects_by_class_name(class_name=class_name)

        if not students or not subjects:
            flash(
                f"No students or subjects found for class {class_name}.",
                "alert-info",
            )
            return render_template(
                "admin/results/broadsheet.html",
                students=[],
                subjects=[],
                broadsheet_data=[],
                subject_averages={},
                class_name=class_name,
                action=action,
            )

        broadsheet_data = []
        subject_averages = {
            subject.id: {"total": 0, "count": 0} for subject in subjects
        }

        # Iterate through students and their results
        for student in students:
            student_results = {
                "student": student,
                "results": {
                    subject.id: {
                        "class_assessment": "",
                        "summative_test": "",
                        "exam": "",
                        "total": "",
                        "grade": "",
                        "remark": "",
                    }
                    for subject in subjects
                },
                "grand_total": "",
                "average": "",
                "cumulative_average": "",
                "position": "",
            }

            # Fetch student results for the specific term and session
            results = Result.query.filter_by(
                student_id=student.id, term=current_term, session=current_session.year
            ).all()

            # Process each result for the student
            for result in results:
                if result.subject_id in student_results["results"]:
                    student_results["results"][result.subject_id] = {
                        "class_assessment": result.class_assessment or "",
                        "summative_test": result.summative_test or "",
                        "exam": result.exam or "",
                        "total": result.total or "",
                        "grade": result.grade or "",
                        "remark": result.remark or "",
                    }

                    if result.total is not None and result.total > 0:
                        subject_averages[result.subject_id]["total"] += result.total
                        subject_averages[result.subject_id]["count"] += 1

                # Safely set grand total, average, and position
                student_results["grand_total"] = (
                    int(result.grand_total) if result.grand_total not in ("", None) else ""
                )
                student_results["cumulative_average"] = (
                    float(result.cumulative_average) if result.cumulative_average not in ("", None) else ""
                )
                student_results["average"] = (
                    float(result.term_average) if result.term_average not in ("", None) else ""
                )
                student_results["position"] = result.position if result.position not in ("", None) else ""

            # Add student results to the broadsheet data
            broadsheet_data.append(student_results)

        # Calculate class averages for each subject
        for subject_id, values in subject_averages.items():
            values["average"] = (
                round(values["total"] / values["count"], 1)
                if values["count"]
                else ""
            )

        # Safely sort students by their average
        broadsheet_data.sort(
            key=lambda x: float(x["average"]) if isinstance(x["average"], (int, float, str)) and x["average"] not in ("", None) else 0,
            reverse=True
        )

        return render_template(
            "admin/results/broadsheet.html",
            students=students,
            subjects=subjects,
            broadsheet_data=broadsheet_data,
            subject_averages=subject_averages,
            class_name=class_name,
            current_session=current_session.year,
            current_term=current_term,
            form=form,
            action=action,
        )

    except Exception as e:
        app.logger.error(
            f"Error generating broadsheet for class_name: {class_name} - {str(e)}"
        )
        flash("An error occurred. Please try again later.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))


@admin_bp.route("/update-broadsheet/<string:class_name>/<string:action>", methods=["POST"])
@login_required
def update_broadsheet(class_name, action):
    class_name = unquote(class_name).strip()

    # Get the current session and term
    current_session, current_term = Session.get_current_session_and_term(include_term=True)

    # Fetch the class record
    class_record = Classes.query.filter_by(name=class_name).first()

    # Fetch students and subjects based on class_name from StudentClassHistory
    student_class_histories = (
        StudentClassHistory.query.filter(
            StudentClassHistory.session_id == current_session.id,
            StudentClassHistory.class_id == class_record.id
        )
        .options(joinedload(StudentClassHistory.student))
        .all()
    )

    students = [history.student for history in student_class_histories]
    subjects = get_subjects_by_class_name(class_name=class_name)

    # Parse the form data
    results_data = {}
    for key, value in request.form.items():
        if key.startswith('results['):
            match = re.match(r'results\[(\d+)\]\[(\d+)\]\[(\w+)\]', key)
            if match:
                student_id, subject_id, field = match.groups()
                student_id, subject_id = int(student_id), int(subject_id)

                value = None if not value else int(value)
                results_data.setdefault(student_id, {}).setdefault(subject_id, {})[field] = value

    if not results_data:
        app.logger.error("No results data provided.")
        flash("No data was submitted for update.", "alert-danger")
        return redirect(url_for('admins.broadsheet', class_name=class_name, action=action))

    try:
        for student_id, subject_scores in results_data.items():
            for subject_id, scores in subject_scores.items():
                # Prepare data to send to save_result
                data = {
                    "class_assessment": scores.get("class_assessment"),
                    "summative_test": scores.get("summative_test"),
                    "exam": scores.get("exam"),
                }

                # Call the centralized save_result function
                save_result(student_id, subject_id, current_term, current_session.year, data)

        flash("Broadsheet updated successfully.", "alert-success")
        app.logger.info(
            f"Broadsheet updated for class {class_name}, term {current_term}, session {current_session.year}."
        )

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating broadsheet: {str(e)}")
        flash("An error occurred while updating the broadsheet.", "alert-danger")

    return redirect(url_for('admins.broadsheet', class_name=class_name, action=action))


@admin_bp.route("/download_broadsheet/<string:class_name>/<string:action>", methods=["GET"])
def download_broadsheet(class_name, action):
    try:
        # Decode and normalize class_name
        current_session, current_term = Session.get_current_session_and_term(include_term=True)
        class_name = unquote(class_name).strip()

        if not current_term or not current_session:
            flash("Term and session must be provided to download broadsheet.", "alert-danger")
            return redirect(url_for("admins.broadsheet", class_name=class_name, action=action))

        # Fetch the class record
        class_record = Classes.query.filter_by(name=class_name).first()

        # Retrieve student and subject data
        student_class_histories = (
            StudentClassHistory.query.filter_by(class_id=class_record.id, session_id=current_session.id)
            .options(joinedload(StudentClassHistory.student))
            .all()
        )
        students = [history.student for history in student_class_histories]
        subjects = get_subjects_by_class_name(class_name=class_name)

        if not students or not subjects:
            flash(f"No students or subjects found for class {class_name}.", "alert-info")
            return redirect(url_for("admins.broadsheet", class_name=class_name, action=action))

        # Prepare broadsheet data
        broadsheet_data, subject_averages = prepare_broadsheet_data(students, subjects, current_term, current_session.year)

        # Generate Excel file
        output = generate_excel_broadsheet(class_name, current_term, current_session.year, broadsheet_data, subjects, subject_averages)

        # Return the Excel file as a downloadable response
        filename = f"Broadsheet_{class_name}_{current_term}_{current_session.year}.xlsx"
        return Response(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )

    except Exception as e:
        app.logger.error(f"Error generating broadsheet for class_name: {class_name} - {str(e)}")
        flash("An error occurred while downloading the broadsheet. Please try again later.", "alert-danger")
        return redirect(url_for("admins.broadsheet", class_name=class_name, action=action))




"""Classes Management"""
# ==========================================================================================================================

@admin_bp.route("/manage_classes", methods=["GET", "POST"])
@login_required
def manage_classes():
    form = ClassesForm()
    if form.validate_on_submit():
        if form.submit_create.data:
            # Handle creating a class
            name = form.name.data.strip()
            section = form.section.data.strip()
            hierarchy = form.hierarchy.data

            if Classes.query.filter_by(name=name).first():
                flash("Class with this name already exists!", "alert-warning")
            else:
                try:
                    Classes.create_class(name=name, section=section, hierarchy=hierarchy)
                    flash(f"Class '{name}' created successfully!", "alert-success")
                except Exception as e:
                    db.session.rollback()
                    flash(f"Error creating class: {str(e)}", "alert-danger")

        elif form.submit_edit.data:
            # Handle editing a class
            class_id = form.class_id.data
            cls = Classes.query.get(class_id)

            form.name.data
            if cls:
                try:
                    cls.edit_class(name=form.name.data.strip(), section=form.section.data.strip(), hierarchy=form.hierarchy.data)
                    flash("Class updated successfully!", "alert-success")
                except Exception as e:
                    db.session.rollback()
                    flash(f"Error updating class: {str(e)}", "alert-danger")
            else:
                flash("Class not found!", "alert-warning")

    classes = Classes.query.order_by(Classes.hierarchy).all()
    return render_template("admin/classes/manage_classes.html", form=form, classes=classes)


@admin_bp.route("/delete-class/<int:class_id>", methods=["POST"])
@login_required
def delete_class(class_id):
    cls = Classes.query.get(class_id)
    if cls:
        try:
            cls.delete_class()
            flash("Class deleted successfully!", "alert-success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting class: {str(e)}", "alert-danger")
    else:
        flash("Class not found!", "alert-warning")

    return redirect(url_for("admins.manage_classes"))




# AJAX ROUTES ===========================================================================================================================
@admin_bp.route("/print_student_message", methods=["GET", "POST"])
@login_required
def print_student_message():
    if not current_user.role == RoleEnum.ADMIN:
        abort(403)

    form = ApproveForm()

    # Fetch all students from the database
    students = Student.query.all()
    selected_student = None

    if request.method == "POST":
        student_id = request.form.get("student_id")
        selected_student = Student.query.get(student_id)

    return render_template(
        "admin/students/print_student_message.html",
        students=students,
        selected_student=selected_student,
        form=form,
    )

@admin_bp.route('/get-student/<int:student_id>', methods=['GET'])
def get_student(student_id):
    student = Student.query.get(student_id)
    if student:
        return jsonify({
            "first_name": student.first_name,
            "last_name": student.last_name,
            "reg_no": student.reg_no
        })
    return jsonify({"error": "Student not found"}), 404

@admin_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Route to fetch updated stats based on current session and term."""

    # Get the current session and term
    current_session, current_term = Session.get_current_session_and_term(include_term=True)

    if not current_session or not current_term:
        return jsonify({"error": "Current session or term is not set."}), 400

    # Query to count students based on the session and term
    base_query = StudentClassHistory.query.join(StudentClassHistory.session).filter(
        Session.year == current_session.year
    ).join(Student)

    # Total students in the current session and term
    total_students = base_query.count()

    # Approved students in the current session and term
    approved_students = base_query.filter(Student.approved == True).count()

    # Students who have paid fees in the current session and term
    # Use the FeePayment model to check fee payment status for the current term
    fees_paid = db.session.query(Student).join(
        StudentClassHistory,
        StudentClassHistory.student_id == Student.id
    ).join(
        FeePayment,
        (FeePayment.student_id == Student.id) &
        (FeePayment.session_id == current_session.id) &
        (FeePayment.term == current_term) &
        (FeePayment.has_paid_fee == True)
    ).filter(
        StudentClassHistory.session_id == current_session.id
    ).count()

    # Students who have not paid fees in the current session and term
    # Use the FeePayment model to check fee payment status for the current term
    fees_not_paid = db.session.query(Student).join(
        StudentClassHistory,
        StudentClassHistory.student_id == Student.id
    ).outerjoin(
        FeePayment,
        (FeePayment.student_id == Student.id) &
        (FeePayment.session_id == current_session.id) &
        (FeePayment.term == current_term)
    ).filter(
        StudentClassHistory.session_id == current_session.id,
        db.or_(
            FeePayment.has_paid_fee == False,
            FeePayment.id.is_(None)  # Students with no fee payment record
        )
    ).count()

    stats = {
        "total_students": total_students,
        "approved_students": approved_students,
        "fees_paid": fees_paid,
        "fees_not_paid": fees_not_paid
    }

    # Return the stats
    return jsonify(stats)

@admin_bp.route('/toggle_fee_status/<int:student_id>', methods=['POST'])
@login_required
def toggle_fee_status(student_id):
    """Route to toggle fee status of a student per term."""

    if not current_user.role == RoleEnum.ADMIN:
        return jsonify({"success": False, "error": "Unauthorized access"}), 403

    student = Student.query.get_or_404(student_id)
    session, term = Session.get_current_session_and_term(include_term=True)

    if not session or not term:
        return jsonify({"success": False, "error": "No active session or term found"}), 400

    fee_payment = FeePayment.query.filter_by(
        student_id=student_id,
        session_id=session.id,
        term=term
    ).first()

    if not fee_payment:
        fee_payment = FeePayment(
            student_id=student_id,
            session_id=session.id,
            term=term,
            has_paid_fee=True
        )
        db.session.add(fee_payment)
    else:
        fee_payment.has_paid_fee = not fee_payment.has_paid_fee

    db.session.commit()

    status = "paid" if fee_payment.has_paid_fee else "unpaid"
    message = f"Fee status for {student.first_name} {student.last_name} for term {term} has been marked as {status}."
    return jsonify({
        "success": True,
        "message": message,
        "has_paid_fee": fee_payment.has_paid_fee
    })

@admin_bp.route('/toggle_approval_status/<int:student_id>', methods=['POST'])
@login_required
def toggle_approval_status(student_id):
    """Route to toggle approval status of a student."""
    if not current_user.role == RoleEnum.ADMIN:
        return jsonify({"success": False, "error": "Unauthorized access"}), 403

    student = Student.query.get_or_404(student_id)
    student.approved = not student.approved

    db.session.commit()

    message = f"{student.first_name} {student.last_name} has been {'approved' if student.approved == True else 'deactivated'} successfully"
    return jsonify({
        "success": True,
        "message": message,
        "approved": student.approved,
    })


@admin_bp.route('/student_stats/<string:class_name>', methods=['GET'])
@login_required
def get_student_stats_by_class(class_name):
    """Route to fetch stats based on the current session, term, and class."""
    # Get the current session and term
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    class_name = unquote(class_name).strip()

    if not current_session or not current_term:
        return jsonify({"error": "Current session or term is not set."}), 400

    # Fetch the class record
    class_record = Classes.query.filter_by(name=class_name).first()
    if not class_record:
        return jsonify({"error": f"Class '{class_name}' not found."}), 404

    # Base query: filter by session and class
    base_query = StudentClassHistory.query.filter(
        StudentClassHistory.session_id == current_session.id,
        StudentClassHistory.class_id == class_record.id
    ).join(Student)

    # Total students in the class, session, and term
    total_students = base_query.count()

    # Approved students in the class, session, and term
    approved_students = base_query.filter(Student.approved == True).count()

    # Students who have paid fees in the class, session, and term
    # Use the FeePayment model to check fee payment status for the current term
    fees_paid = db.session.query(Student).join(
        StudentClassHistory,
        StudentClassHistory.student_id == Student.id
    ).join(
        FeePayment,
        (FeePayment.student_id == Student.id) &
        (FeePayment.session_id == current_session.id) &
        (FeePayment.term == current_term) &
        (FeePayment.has_paid_fee == True)
    ).filter(
        StudentClassHistory.session_id == current_session.id,
        StudentClassHistory.class_id == class_record.id
    ).count()

    # Students who have not paid fees in the class, session, and term
    # Use the FeePayment model to check fee payment status for the current term
    fees_not_paid = db.session.query(Student).join(
        StudentClassHistory,
        StudentClassHistory.student_id == Student.id
    ).outerjoin(
        FeePayment,
        (FeePayment.student_id == Student.id) &
        (FeePayment.session_id == current_session.id) &
        (FeePayment.term == current_term)
    ).filter(
        StudentClassHistory.session_id == current_session.id,
        StudentClassHistory.class_id == class_record.id,
        db.or_(
            FeePayment.has_paid_fee == False,
            FeePayment.id.is_(None)  # Students with no fee payment record
        )
    ).count()

    stats = {
        "class_name": class_name,
        "total_students": total_students,
        "approved_students": approved_students,
        "fees_paid": fees_paid,
        "fees_not_paid": fees_not_paid
    }

    # Return the stats
    return jsonify(stats)

@admin_bp.route('/search_students/<string:action>', methods=['GET'])
@login_required
def search_students(action):
    search_query = request.args.get('query', '', type=str).strip()
    ajax_request = request.args.get('ajax', False, type=bool)
    page = request.args.get('page', 1, type=int)

    # Get the current session
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    form = DeleteForm()

    if not current_session:
        app.logger.error('No active session found.')
        return jsonify({'error': 'No active session found.'}), 400

    # # Base query to get all students for the current session
    # students_query = StudentClassHistory.query.filter(
    #     StudentClassHistory.session_id == selected_session
    # ).join(Student).join(Classes)

    # Fetch students with their class hierarchy for the current session
    students_query = (
        db.session.query(Student, Classes.name.label("class_name"), Classes.hierarchy)
        .join(StudentClassHistory, Student.id == StudentClassHistory.student_id)
        .join(Classes, StudentClassHistory.class_id == Classes.id)
        .filter(StudentClassHistory.session_id == current_session.id)
        .order_by(Classes.hierarchy)  # Order by the hierarchy field in the Classes model
    )

    # Apply search filters
    if search_query:
        search_filter = db.or_(
            func.lower(Student.first_name).contains(search_query.lower()),
            func.lower(Student.last_name).contains(search_query.lower()),
            func.lower(Student.reg_no).contains(search_query.lower()),
            func.lower(Classes.name).contains(search_query.lower()),
        )
        students_query = students_query.filter(search_filter)

    # Paginate the results
    pagination = students_query.paginate(page=page, per_page=5, error_out=False)

    # Group students by class
    students_classes = group_students_by_class(pagination.items)

    return render_template(
        "ajax/students/pagination.html",
        students_classes=students_classes,
        current_session=current_session.year,
        current_term=current_term,
        pagination=pagination,
        action=action,
        form=form,
        search_query=search_query,
    )

# @admin_bp.route('/search_students/<string:action>', methods=['GET'])
# @login_required
# def search_students(action):
#     search_query = request.args.get('query', '', type=str).strip()
#     fee_status = request.args.get('status', '', type=str).strip()
#     ajax_request = request.args.get('ajax', False, type=bool)
#     page = request.args.get('page', 1, type=int)

#     # Get the current session and term
#     current_session, current_term = Session.get_current_session_and_term(include_term=True)
#     form = DeleteForm()

#     if not current_session:
#         app.logger.error('No active session found.')
#         return jsonify({'error': 'No active session found.'}), 400

#     # Base query to fetch students with their class hierarchy for the current session
#     students_query = (
#         db.session.query(Student, Classes.name.label("class_name"), Classes.hierarchy)
#         .join(StudentClassHistory, Student.id == StudentClassHistory.student_id)
#         .join(Classes, StudentClassHistory.class_id == Classes.id)
#         .filter(StudentClassHistory.session_id == current_session.id)
#         .order_by(Classes.hierarchy)  # Order by the hierarchy field in the Classes model
#     )

#     # Apply search filters
#     if search_query:
#         search_filter = db.or_(
#             func.lower(Student.first_name).contains(search_query.lower()),
#             func.lower(Student.last_name).contains(search_query.lower()),
#             func.lower(Student.reg_no).contains(search_query.lower()),
#             func.lower(Classes.name).contains(search_query.lower()),
#         )
#         students_query = students_query.filter(search_filter)

#     # Apply fee status filter
#     if fee_status:
#         students_query = students_query.join(FeePayment, (FeePayment.student_id == Student.id) &
#                                             (FeePayment.session_id == current_session.id) &
#                                             (FeePayment.term == current_term))
#         if fee_status == "paid":
#             students_query = students_query.filter(FeePayment.has_paid_fee == True)
#         elif fee_status == "unpaid":
#             students_query = students_query.filter(FeePayment.has_paid_fee == False)

#     # Paginate the results
#     pagination = students_query.paginate(page=page, per_page=5, error_out=False)

#     # Group students by class
#     students_classes = group_students_by_class(pagination.items)

#     if ajax_request:
#         # Render only the table rows for AJAX requests
#         html = render_template(
#             "ajax/students/pagination.html",
#             students_classes=students_classes,
#             session=current_session,
#             current_session=current_session.year,
#             current_term=current_term,
#             pagination=pagination,
#             action=action,
#             form=form,
#             search_query=search_query,
#         )
#         return jsonify({'success': True, 'html': html})
#     else:
#         # Render the full page for non-AJAX requests
#         return render_template(
#             "admin/students/view_students.html",
#             students_classes=students_classes,
#             current_session=current_session.year,
#             session=current_session,
#             current_term=current_term,
#             pagination=pagination,
#             action=action,
#             form=form,
#             search_query=search_query,
#         )


@admin_bp.route('/search_students_by_class/<string:class_name>/<string:action>', methods=['GET'])
@login_required
def search_students_by_class(class_name, action):
    search_query = request.args.get('query', '', type=str).strip()
    ajax_request = request.args.get('ajax', False, type=bool)

    class_name = unquote(class_name).strip()
    page = request.args.get('page', 1, type=int)

    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    form = DeleteForm()

     # Fetch the class record
    class_record = Classes.query.filter_by(name=class_name).first()
    if not class_record:
        return jsonify({"error": f"Class '{class_name}' not found."}), 404

    # Base query: filter by session and class
    students_query = StudentClassHistory.query.filter(
        StudentClassHistory.session_id == current_session.id,
        StudentClassHistory.class_id == class_record.id
    ).join(Student)

    # Apply search filter if query is not empty
    if search_query:
        search_filter = or_(
            func.lower(Student.first_name).contains(search_query.lower()),
            func.lower(Student.last_name).contains(search_query.lower()),
            func.lower(Student.reg_no).contains(search_query.lower()),
        )
        students_query = students_query.filter(search_filter)

    # Paginate results
    pagination = students_query.paginate(page=page, per_page=5, error_out=False)
    student_histories = pagination.items
    students = [history.student for history in student_histories]

    # Handle AJAX requests
    # if ajax_request:
    return render_template(
        "ajax/classes/students_by_class.html",
        students=students,
        session=current_session.year,
        current_session=current_session.year,
        form=form,
        current_term=current_term,
        pagination=pagination,
        action=action,
        class_name=class_name,
    )

@admin_bp.route("/update_result_field", methods=["POST"])
@login_required
def update_result_field():
    try:
        data = request.get_json()
        current_session, current_term = Session.get_current_session_and_term(include_term=True)

        subject_id = data.get("subject_id")
        student_id = data.get("student_id")

        if not subject_id or not student_id:
            return jsonify({"status": "error", "message": "Invalid subject or student ID."}), 400

        class_assessment = data.get("class_assessment")
        summative_test = data.get("summative_test")
        exam = data.get("exam")
        next_term_begins = data.get("next_term_begins")
        position = data.get("position")
        date_issued = data.get("date_issued")

        for key, value in data.items():
            app.logger.info(f"{key}: {value}")

        app.logger.info(f"Data:=>> {data}")

        save_result(student_id, subject_id, current_term, current_session.year, data)

        return jsonify({"status": "success", "message": "Result saved successfully."})
    except Exception as e:
        app.logger.error(f"Error saving result via AJAX: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to save result."}), 400



"""
TEACHER MANAGEMENT
"""

@admin_bp.route("/teachers", methods=["GET", "POST"])
@login_required
def manage_teachers():
    teachers = Teacher.query.all()
    form = TeacherForm()

    if request.method == "POST" and form.validate_on_submit():
        teacher_id = form.id.data  # Fetching primary key for editing
        first_name = form.first_name.data.strip()
        last_name = form.last_name.data.strip()
        email = form.email.data.strip().lower() if form.email.data else None
        phone_number = form.phone_number.data.strip() if form.phone_number.data else None
        section = form.section.data

        # Editing existing teacher
        if teacher_id:
            teacher = Teacher.query.get(teacher_id)
            if teacher:
                # Validate email uniqueness (if changed)
                if email and email != teacher.email and Teacher.query.filter_by(email=email).first():
                    flash("Email is already associated with another teacher!", "alert-danger")
                else:
                    teacher.first_name = first_name
                    teacher.last_name = last_name
                    teacher.email = email
                    teacher.phone_number = phone_number
                    teacher.section = section
                    db.session.commit()
                    flash("Teacher updated successfully.", "alert-success")
            else:
                flash("Teacher not found!", "alert-danger")
        else:  # Adding a new teacher
            # Check for email uniqueness if provided
            if email and Teacher.query.filter_by(email=email).first():
                flash("Email is already associated with another teacher!", "alert-danger")
            # Check for phone number uniqueness if provided
            elif phone_number and Teacher.query.filter_by(phone_number=phone_number).first():
                flash("Phone number is already associated with another teacher!", "alert-danger")
            else:
                # Generate a unique employee ID
                employee_id = generate_employee_id(section)

                # Ensure the generated employee ID is unique
                if Teacher.query.filter_by(employee_id=employee_id).first():
                    flash("Employee ID already exists! Try again.", "alert-danger")
                else:
                    # Create the user with the employee_id as username
                    user = User(username=employee_id, role=RoleEnum.TEACHER)
                    user.set_password(employee_id)  # Set password as the employee_id

                    # Add user to the session and commit
                    db.session.add(user)
                    db.session.commit()

                    # Create the teacher record
                    new_teacher = Teacher(
                        user_id=user.id,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        phone_number=phone_number,
                        section=section,
                        employee_id=employee_id,
                    )
                    db.session.add(new_teacher)
                    db.session.commit()
                    flash("Teacher added successfully.", "alert-success")

        return redirect(url_for("admins.manage_teachers"))

    return render_template(
        "admin/teachers/teachers.html",
        teachers=teachers,
        form=form,
    )


@admin_bp.route("/delete_teacher/<int:teacher_id>", methods=["POST"])
@login_required
def delete_teacher(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if teacher:
        user = User.query.get(teacher.user_id)  # Fetch the associated user record
        db.session.delete(teacher)  # Delete the teacher record

        if user:
            db.session.delete(user)  # Delete the associated user record

        db.session.commit()
        flash("Teacher and associated user deleted successfully.", "alert-success")
    else:
        flash("Teacher not found!", "alert-danger")

    return redirect(url_for("admins.manage_teachers"))






@admin_bp.route("/assign_subject_to_class", methods=["GET", "POST"])
def assign_subject_to_class():
    """
    Assign a subject to a class. Multiple subjects can be assigned to the same class.
    """
    form = AssignSubjectToClassForm()
    if form.validate_on_submit():
        class_ = form.class_name.data
        subject = form.subject.data

        # Avoid duplicate assignments
        if subject not in class_.subjects:
            class_.subjects.append(subject)
            db.session.commit()
            flash(f"Subject '{subject.name}' assigned to class '{class_.name}' successfully!", "alert-success")
        else:
            flash(f"Subject '{subject.name}' is already assigned to class '{class_.name}'.", "alert-warning")

    return render_template("admin/subjects/assign_subject_to_class.html", form=form)


@admin_bp.route("/assign_subject_to_teacher", methods=["GET", "POST"])
def assign_subject_to_teacher():
    """
    Assign a subject to a teacher. A teacher can be assigned to multiple subjects.
    """
    form = AssignSubjectToTeacherForm()
    if form.validate_on_submit():
        teacher = form.teacher.data
        subject = form.subject.data

        # Avoid duplicate assignments
        if subject not in teacher.subjects:
            teacher.subjects.append(subject)
            db.session.commit()
            flash(f"Subject '{subject.name}' assigned to teacher '{teacher.last_name}, {teacher.first_name}' successfully!", "alert-success")
        else:
            flash(f"Subject '{subject.name}' is already assigned to teacher '{teacher.last_name}, {teacher.first_name}'.", "alert-warning")

    return render_template("admin/teachers/assign_subject_to_teacher.html", form=form)


@admin_bp.route("/assign_teacher_to_class", methods=["GET", "POST"])
def assign_teacher_to_class():
    form = AssignTeacherToClassForm()
    current_form_teachers = None

    if form.validate_on_submit():
        teacher = form.teacher.data
        class_ = form.class_name.data
        is_form_teacher = form.is_form_teacher.data

        # Check if the teacher is already assigned to the class
        existing_assignment = db.session.query(class_teacher).filter_by(
            class_id=class_.id, teacher_id=teacher.id
        ).first()

        if existing_assignment:
            flash(
                f"Teacher '{teacher.last_name}, {teacher.first_name}' is already assigned to class '{class_.name}'.",
                "alert-warning"
            )
        else:
            # Assign the teacher to the class
            class_.teachers.append(teacher)

            # If the teacher is marked as a form teacher
            if is_form_teacher:
                db.session.execute(
                    class_teacher.insert().values(
                        class_id=class_.id,
                        teacher_id=teacher.id,
                        is_form_teacher=True
                    )
                )

            db.session.commit()
            flash(
                f"Teacher '{teacher.last_name}, {teacher.first_name}' assigned to class '{class_.name}' successfully!",
                "alert-success"
            )

    else:
        # Populate current form teachers if a class is selected
        if form.class_name.data:
            class_ = form.class_name.data
            current_form_teachers = db.session.query(Teacher).join(class_teacher).filter(
                class_teacher.c.class_id == class_.id,
                class_teacher.c.is_form_teacher == True
            ).all()

    return render_template(
        "admin/teachers/assign_teacher_to_class.html",
        form=form,
        current_form_teachers=current_form_teachers
    )
