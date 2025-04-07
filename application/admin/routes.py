from datetime import datetime
from urllib.parse import unquote
from sqlalchemy import func, or_, case
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.sql import text
from flask import (
    render_template, redirect, url_for, flash, make_response, request, Response, jsonify, current_app as app, session
)
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from . import admin_bp
from ..models import (
    Student, User, Subject, Result, Session, StudentClassHistory, UserSessionPreference,
    RoleEnum, TermEnum, Classes, Teacher, class_subject, class_teacher, FeePayment, AdminPrivilege, AuditLog, StudentTermSummary
)
from ..helpers import (
    get_subjects_by_class_name, update_results_helper, save_result, db, populate_form_with_results,
    generate_excel_broadsheet, prepare_broadsheet_data, generate_employee_id, group_students_by_class,
    get_students_query, save_class_wide_fields, apply_filters_to_students_query, require_session_and_term, handle_db_errors
)
from ..auth.forms import (
    EditStudentForm, ResultForm, SubjectForm, DeleteForm, SessionForm, ApproveForm, classForm,
    ClassesForm, ManageResultsForm, StudentRegistrationForm, TeacherForm, AdminCreationForm,
    AdminEditForm, AdminPrivilegeEditForm, AssignSubjectToClassForm, AssignSubjectToTeacherForm,
    AssignTeacherToClassForm
)
import bleach
from marshmallow import Schema, fields, ValidationError, validates_schema
from application import limiter
import pyotp
import qrcode
from io import BytesIO
import base64
from itertools import groupby
from operator import itemgetter
import re

# admin_bp = Blueprint("admins", __name__)

# ------------------------------
# Request Hooks
# ------------------------------

@admin_bp.before_request
def admin_before_request():
    """Ensure user is authenticated and has admin privileges before processing requests."""
    app.logger.debug(f"Before request: is_authenticated={current_user.is_authenticated}, mfa_verified={session.get('mfa_verified', False)}")
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role != RoleEnum.ADMIN.value:
        flash("You are not authorized to access this page.", "alert-danger")
        app.logger.warning(f"Unauthorized access attempt by user {current_user.username} with role {current_user.role}")
        return redirect(url_for("main.index"))
    if not session.get('mfa_verified', False) and current_user.mfa_secret:
        return redirect(url_for("auth.mfa_verify"))

@admin_bp.after_request
def add_csrf_token(response):
    """Add security headers to every response."""
    response.headers['X-CSRFToken'] = generate_csrf()
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ------------------------------
# Admin Dashboard and Theme
# ------------------------------

@admin_bp.route("/dashboard")
@login_required
def admin_dashboard():
    """Render the admin dashboard."""
    app.logger.info(f"Admin dashboard accessed by user {current_user.username}")
    return render_template("admin/index.html")

@admin_bp.route("/set_theme", methods=["POST"])
@login_required
def set_theme():
    """Set the user's preferred theme."""
    theme = request.form.get("theme", "light")
    resp = make_response(redirect(url_for("admins.admin_dashboard")))
    resp.set_cookie("user_theme", theme, max_age=86400, httponly=True, samesite="Lax", secure=app.config["SESSION_COOKIE_SECURE"])
    flash(f"Theme set to {theme}", "alert-success")
    return resp

# ------------------------------
# Admin User Management
# ------------------------------

@admin_bp.route("/create_admin", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute")
def create_admin():
    """Create a new admin user with MFA setup."""
    if not current_user.privileges or not current_user.privileges.can_manage_users:
        flash("You do not have permission to create admin users.", "alert-danger")
        return redirect(url_for("admins.admin_dashboard"))

    form = AdminCreationForm()
    qr_code_url = None

    if form.validate_on_submit():
        app.logger.info("Form validated successfully")
        try:
            username = bleach.clean(form.username.data)
            if User.query.filter_by(username=username).first():
                flash("Username already exists.", "alert-danger")
                return redirect(url_for("admins.create_admin"))

            new_user = User(username=username, role=RoleEnum.ADMIN.value)
            new_user.set_password(form.password.data)
            new_user.mfa_secret = pyotp.random_base32()
            db.session.add(new_user)
            db.session.flush()

            privileges = AdminPrivilege(
                user_id=new_user.id,
                can_manage_users=form.can_manage_users.data,
                can_manage_sessions=form.can_manage_sessions.data,
                can_manage_classes=form.can_manage_classes.data,
                can_manage_results=form.can_manage_results.data,
                can_manage_teachers=form.can_manage_teachers.data,
                can_manage_subjects=form.can_manage_subjects.data,
                can_view_reports=form.can_view_reports.data
            )
            db.session.add(privileges)
            db.session.add(AuditLog(user_id=current_user.id, action=f"Created admin {username}"))
            db.session.commit()

            totp = pyotp.TOTP(new_user.mfa_secret)
            provisioning_uri = totp.provisioning_uri(
                name=new_user.username,
                issuer_name=app.config.get("SCHOOL_NAME", "Aunty Anne's International School")
            )
            qr = qrcode.make(provisioning_uri)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            qr_code_url = f"data:image/png;base64,{qr_code_base64}"

            flash(f"Admin user '{username}' created successfully.", "alert-success")
            return render_template(
                "admin/users/create_admin_success.html",
                username=username,
                mfa_secret=new_user.mfa_secret,
                qr_code_url=qr_code_url
            )
        except IntegrityError as e:
            db.session.rollback()
            app.logger.error(f"Integrity error creating admin: {str(e)}")
            flash("Creation failed due to duplicate data.", "alert-danger")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error creating admin: {str(e)}")
            flash("Database error occurred. Please try again.", "alert-danger")
    return render_template("admin/users/create_admins.html", form=form, qr_code_url=qr_code_url)

@admin_bp.route("/view_admins", methods=["GET"])
@login_required
def view_admins():
    """Display a list of all admin users."""
    if not current_user.privileges or not current_user.privileges.can_manage_users:
        flash("You do not have permission to view admin users.", "alert-danger")
        return redirect(url_for("admins.admin_dashboard"))

    form = DeleteForm()
    admins = User.query.filter_by(role=RoleEnum.ADMIN.value).all()
    return render_template("admin/users/view_admins.html", form=form, admins=admins)

@admin_bp.route("/edit_admin/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_admin(user_id):
    """Edit an admin user's basic details."""
    if not current_user.privileges or not current_user.privileges.can_manage_users:
        flash("You do not have permission to edit admin users.", "alert-danger")
        return redirect(url_for("admins.admin_dashboard"))

    admin = User.query.get_or_404(user_id)
    if admin.role != RoleEnum.ADMIN.value:
        flash("This user is not an admin", "alert-danger")
        return redirect(url_for("admins.view_admins"))

    has_all_privileges = all([
        current_user.privileges.can_manage_users,
        current_user.privileges.can_manage_sessions,
        current_user.privileges.can_manage_classes,
        current_user.privileges.can_manage_results,
        current_user.privileges.can_manage_teachers,
        current_user.privileges.can_manage_subjects,
        current_user.privileges.can_view_reports
    ])

    form = AdminEditForm(obj=admin)
    if form.validate_on_submit():
        try:
            if User.query.filter(User.username == form.username.data, User.id != user_id).first():
                flash("Username already exists.", "alert-danger")
                return redirect(url_for("admins.edit_admin", user_id=user_id))

            admin.username = form.username.data
            if has_all_privileges and form.password.data:
                admin.set_password(form.password.data)
                flash("Password updated successfully.", "alert-info")

            db.session.commit()
            flash(f"Admin '{admin.username}' updated successfully.", "alert-success")
            return redirect(url_for("admins.view_admins"))
        except IntegrityError as e:
            db.session.rollback()
            app.logger.error(f"Integrity error editing admin {user_id}: {str(e)}")
            flash("Update failed due to duplicate data.", "alert-danger")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error editing admin {user_id}: {str(e)}")
            flash("Database error occurred. Please try again.", "alert-danger")
    return render_template("admin/users/edit_admins.html", form=form, admin=admin, has_all_privileges=has_all_privileges)

@admin_bp.route("/edit_admin_privileges/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_admin_privileges(user_id):
    """Edit an admin user's privileges."""
    if not current_user.privileges or not current_user.privileges.can_manage_users:
        flash("You do not have permission to edit admin privileges.", "alert-danger")
        return redirect(url_for("admins.admin_dashboard"))

    admin = User.query.get_or_404(user_id)
    if admin.role != RoleEnum.ADMIN.value:
        flash("This user is not an admins.", "alert-danger")
        return redirect(url_for("admins.view_admins"))

    privileges = AdminPrivilege.query.filter_by(user_id=admin.id).first_or_404()
    form = AdminPrivilegeEditForm(obj=privileges)
    if form.validate_on_submit():
        try:
            privileges.can_manage_users = form.can_manage_users.data
            privileges.can_manage_sessions = form.can_manage_sessions.data
            privileges.can_manage_classes = form.can_manage_classes.data
            privileges.can_manage_results = form.can_manage_results.data
            privileges.can_manage_teachers = form.can_manage_teachers.data
            privileges.can_manage_subjects = form.can_manage_subjects.data
            privileges.can_view_reports = form.can_view_reports.data
            db.session.commit()
            flash(f"Privileges for '{admin.username}' updated successfully.", "alert-success")
            return redirect(url_for("admins.view_admins"))
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error updating privileges for admin {user_id}: {str(e)}")
            flash("Database error occurred. Please try again.", "alert-danger")
    return render_template("admin/users/edit_admin_privileges.html", form=form, admin=admin)

@admin_bp.route("/delete_admin/<int:user_id>", methods=["POST"])
@login_required
def delete_admin(user_id):
    """Delete an admin user and their associated privileges."""
    if not current_user.privileges or not current_user.privileges.can_manage_users:
        flash("You do not have permission to delete admin users.", "alert-danger")
        return redirect(url_for("admins.admin_dashboard"))

    admin = User.query.get_or_404(user_id)
    if admin.role != RoleEnum.ADMIN.value or admin.id == current_user.id:
        flash("Invalid operation.", "alert-danger")
        return redirect(url_for("admins.view_admins"))

    form = DeleteForm()
    if form.validate_on_submit():
        try:
            AdminPrivilege.query.filter_by(user_id=admin.id).delete()
            UserSessionPreference.query.filter_by(user_id=admin.id).delete()
            db.session.delete(admin)
            db.session.commit()
            flash(f"Admin '{admin.username}' deleted successfully.", "alert-success")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error deleting admin {user_id}: {str(e)}")
            flash("Database error occurred. Please try again.", "alert-danger")
    return redirect(url_for("admins.view_admins"))

# ------------------------------
# Session Management
# ------------------------------

@admin_bp.route("/manage_sessions", methods=["GET", "POST"])
@login_required
def manage_sessions():
    """Manage the current academic session and term for the current user."""
    if not current_user.privileges or not current_user.privileges.can_manage_sessions:
        flash("You do not have permission to manage sessions.", "alert-danger")
        return redirect(url_for("admins.admin_dashboard"))

    form = SessionForm()
    academic_sessions = Session.query.all()
    form.session.choices = [(s.id, s.year) for s in academic_sessions]
    form.term.choices = [(t.value, t.value) for t in TermEnum]

    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if form.validate_on_submit():
        session_id = form.session.data
        term_str = form.term.data
        try:
            term_enum = TermEnum(term_str)
            preference = UserSessionPreference.query.filter_by(user_id=current_user.id).first()
            selected_session = Session.query.get(session_id)
            if not selected_session:
                flash("Selected session does not exist.", "alert-danger")
                return redirect(url_for("admins.manage_sessions"))

            if preference:
                preference.session_id = session_id
                preference.current_term = term_enum.value
            else:
                preference = UserSessionPreference(
                    user_id=current_user.id,
                    session_id=session_id,
                    current_term=term_enum.value
                )
                db.session.add(preference)
            db.session.commit()
            flash(f"Your current session set to {selected_session.year} ({term_str}).", "alert-success")
            app.logger.info(f"User {current_user.username} set session to {selected_session.year} and term to {term_str}")
            return redirect(url_for("admins.manage_sessions"))
        except ValueError:
            flash(f"Invalid term '{term_str}' selected.", "alert-danger")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error updating session preference: {str(e)}")
            flash("Database error occurred. Please try again.", "alert-danger")
    return render_template(
        "admin/manage_sessions.html",
        form=form,
        current_session=current_session.year if current_session else "Not Set",
        current_term=current_term.value if current_term else "Not Set"
    )

# ------------------------------
# Student Management
# ------------------------------

@admin_bp.route("/register/student", methods=["GET", "POST"])
@login_required
def add_student():
    """Register a new student and assign them to a class."""
    form = StudentRegistrationForm()
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        flash("No current session or term set. Please set one first.", "alert-danger")
        return redirect(url_for("admins.manage_sessions"))

    form.class_id.choices = [(cls.id, f"{cls.name}") for cls in Classes.query.order_by(Classes.hierarchy).all()]
    form.term.choices = [(t.value, t.value) for t in TermEnum]

    if form.validate_on_submit():
        try:
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
                approved=False
            )
            db.session.add(student)
            db.session.flush()

            student.reg_no = f"{app.config.get('REG_NO_PREFIX', 'AAIS/0559/')}{student.id:03}"
            user = User(username=student.reg_no, role=RoleEnum.STUDENT.value)
            user.set_password(student.reg_no)
            student.user = user
            db.session.add(user)

            class_history = StudentClassHistory(
                student_id=student.id,
                session_id=current_session.id,
                class_id=form.class_id.data,
                start_term=form.term.data,
                join_date=datetime.utcnow(),
                is_active=True
            )
            db.session.add(class_history)
            db.session.commit()

            flash(f"Student registered successfully. Registration Number: {student.reg_no}.", "alert-success")
            return redirect(url_for("admins.add_student"))
        except IntegrityError as e:
            db.session.rollback()
            app.logger.error(f"Integrity error registering student: {str(e)}")
            flash("Registration failed: Duplicate data.", "alert-danger")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error registering student: {str(e)}")
            flash("Database error occurred. Please try again.", "alert-danger")
    return render_template(
        "admin/students/add_student.html",
        title="Register",
        form=form,
        school_name=app.config.get("SCHOOL_NAME", "Aunty Anne's International School"),
        current_term=current_term.value if current_term else "None"
    )

@admin_bp.route("/students/<string:action>", methods=["GET", "POST"])
@login_required
@require_session_and_term
@handle_db_errors
def students(current_session, current_term, action):
    """View and filter students across all classes."""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    enrollment_status = request.args.get('enrollment_status', 'active')
    fee_status = request.args.get('fee_status', '')
    approval_status = request.args.get('approval_status', '')
    term = request.args.get('term', current_term.value)

    students_query = get_students_query(current_session, term)
    students_query = apply_filters_to_students_query(
        students_query, enrollment_status, fee_status, approval_status, current_session, current_term, term
    )
    students_query = students_query.order_by(Classes.hierarchy, Student.first_name.asc())
    paginated_students = students_query.paginate(page=page, per_page=per_page, error_out=False)
    students_classes = group_students_by_class(paginated_students.items)
    form = DeleteForm()
    classes = Classes.query.order_by(Classes.hierarchy).all()
    sessions = Session.query.order_by(Session.year.desc()).all()

    if request.args.get('ajax', type=bool):
        return render_template(
            "ajax/students/pagination.html",
            students_classes=students_classes,
            pagination=paginated_students,
            action=action,
            session=current_session,
            current_term=current_term.value,
            form=form,
            enrollment_status=enrollment_status,
            fee_status=fee_status,
            approval_status=approval_status,
            classes=classes,
            sessions=sessions
        )
    return render_template(
        "admin/students/view_students.html",
        students_classes=students_classes,
        pagination=paginated_students,
        current_session=current_session.year,
        session=current_session,
        current_term=current_term.value,
        action=action,
        form=form,
        enrollment_status=enrollment_status,
        fee_status=fee_status,
        approval_status=approval_status,
        classes=classes,
        sessions=sessions
    )

@admin_bp.route("/edit_student/<int:student_id>/<string:action>", methods=["GET", "POST"])
@login_required
@require_session_and_term
def edit_student(current_session, current_term, student_id, action):
    """Edit an existing student's details."""
    student = Student.query.get_or_404(student_id)
    form = EditStudentForm()
    form.class_id.choices = [(cls.id, f"{cls.name} ({cls.section})") for cls in Classes.query.order_by(Classes.hierarchy).all()]
    student_class_history = StudentClassHistory.query.filter_by(
        student_id=student.id,
        session_id=current_session.id,
        is_active=True,
        leave_date=None
    ).order_by(StudentClassHistory.join_date.desc()).first()

    if form.validate_on_submit():
        try:
            student.reg_no = form.reg_no.data
            student.first_name = form.first_name.data
            student.last_name = form.last_name.data
            student.middle_name = form.middle_name.data
            student.gender = form.gender.data

            if student_class_history:
                student_class_history.class_id = form.class_id.data
            else:
                new_class_history = StudentClassHistory(
                    student_id=student.id,
                    session_id=current_session.id,
                    class_id=form.class_id.data,
                    start_term=current_term.value,
                    join_date=datetime.utcnow(),
                    is_active=True
                )
                db.session.add(new_class_history)

            user = User.query.filter_by(id=student.user_id).first()
            if user:
                user.username = form.reg_no.data

            db.session.commit()
            flash("Student updated successfully!", "alert-success")
            return redirect(url_for("admins.students", action=action))
        except IntegrityError as e:
            db.session.rollback()
            app.logger.error(f"Integrity error updating student {student_id}: {str(e)}")
            flash("Update failed: Duplicate registration number.", "alert-danger")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error updating student {student_id}: {str(e)}")
            flash("Database error occurred. Please try again.", "alert-danger")
    elif request.method == "GET":
        form.reg_no.data = student.reg_no
        form.first_name.data = student.first_name
        form.last_name.data = student.last_name
        form.middle_name.data = student.middle_name
        form.gender.data = student.gender
        if student_class_history:
            form.class_id.data = student_class_history.class_id
    return render_template("admin/students/edit_student.html", form=form, student=student, action=action)

@admin_bp.route("/delete_student/<int:student_id>/<string:action>", methods=["POST"])
@login_required
def delete_student(student_id, action):
    form = DeleteForm()
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    class_name = "Unassigned"

    if not current_session or not current_term:
        flash("No current session or term available.", "alert-danger")
        return redirect(url_for("admins.students", action=action))

    if form.validate_on_submit():
        student = Student.query.get_or_404(student_id)
        try:
            student_class_history = (
                StudentClassHistory.query.filter_by(
                    student_id=student.id,
                    session_id=current_session.id,
                    is_active=True,
                    leave_date=None
                ).order_by(StudentClassHistory.join_date.desc()).first()
            )
            if student_class_history and student_class_history.class_ref:
                class_name = student_class_history.class_ref.name

            app.logger.info(f"Preparing to delete student {student_id}")
            db.session.add(AuditLog(user_id=current_user.id, action=f"Deleted student {student_id}"))
            user = User.query.get(student.user_id) if student.user_id else None
            if user:
                app.logger.info(f"Deleting user {user.id} for student {student_id} with cascading to Student")
                db.session.delete(user)
            else:
                app.logger.info(f"Deleting student {student_id} directly (no user associated)")
                db.session.delete(student)

            app.logger.info(f"Committing deletion for student {student_id}")
            db.session.commit()
            app.logger.info(f"Successfully deleted student {student_id} and related records")
            flash("Student and records deleted successfully!", "alert-success")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting student {student_id}: {str(e)}", exc_info=True)  # Log full traceback
            flash(f"Error deleting student: {str(e)}", "alert-danger")

    return redirect(url_for("admins.students", action=action, class_name=class_name))

@admin_bp.route("/student/<int:student_id>/reenroll", methods=["POST"])
@login_required
def student_reenroll(student_id):
    """Re-enroll a student into a class."""
    if current_user.role != RoleEnum.ADMIN.value:
        return jsonify({"success": False, "error": "Unauthorized access"}), 403

    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        return jsonify({"success": False, "error": "No current session or term set"}), 400

    class_id = request.form.get("class_id", type=int)
    try:
        enrollment = StudentClassHistory.query.filter_by(
            student_id=student_id,
            session_id=current_session.id
        ).order_by(StudentClassHistory.join_date.desc()).first()

        if enrollment and enrollment.is_active and enrollment.leave_date is None:
            return jsonify({"success": False, "message": "Student is already actively enrolled"}), 400

        if not class_id:
            class_id = enrollment.class_id if enrollment else None
        if not class_id or not Classes.query.get(class_id):
            return jsonify({"success": False, "error": "No valid class specified"}), 400

        if enrollment:
            enrollment.reenroll(current_session.id, class_id, current_term.value)
        else:
            new_enrollment = StudentClassHistory(
                student_id=student_id,
                session_id=current_session.id,
                class_id=class_id,
                start_term=current_term.value,
                join_date=datetime.utcnow(),
                is_active=True
            )
            db.session.add(new_enrollment)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Student re-enrolled in {current_term.value} term",
            "stats": get_stats().get_json()
        })
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error re-enrolling student {student_id}: {str(e)}")
        return jsonify({"success": False, "error": "Database error occurred"}), 500

# ------------------------------
# Class Management
# ------------------------------

@admin_bp.route("/manage_classes", methods=["GET", "POST"])
@login_required
def manage_classes():
    """Manage classes (create, edit)."""
    form = ClassesForm()
    if form.validate_on_submit():
        if form.submit_create.data:
            name = form.name.data.strip()
            section = form.section.data.strip()
            hierarchy = form.hierarchy.data
            if Classes.query.filter_by(name=name).first():
                flash("Class with this name already exists!", "alert-warning")
            else:
                try:
                    new_class = Classes(name=name, section=section, hierarchy=hierarchy)
                    db.session.add(new_class)
                    db.session.commit()
                    flash(f"Class '{name}' created successfully!", "alert-success")
                except IntegrityError as e:
                    db.session.rollback()
                    app.logger.error(f"Integrity error creating class {name}: {str(e)}")
                    flash("Creation failed: Duplicate name or hierarchy.", "alert-danger")
                except OperationalError as e:
                    db.session.rollback()
                    app.logger.error(f"Database error creating class {name}: {str(e)}")
                    flash("Database error occurred.", "alert-danger")
        elif form.submit_edit.data:
            class_id = form.class_id.data
            cls = Classes.query.get(class_id)
            if cls:
                try:
                    cls.name = form.name.data.strip()
                    cls.section = form.section.data.strip()
                    cls.hierarchy = form.hierarchy.data
                    db.session.commit()
                    flash("Class updated successfully!", "alert-success")
                except IntegrityError as e:
                    db.session.rollback()
                    app.logger.error(f"Integrity error updating class {class_id}: {str(e)}")
                    flash("Update failed: Duplicate name or hierarchy.", "alert-danger")
                except OperationalError as e:
                    db.session.rollback()
                    app.logger.error(f"Database error updating class {class_id}: {str(e)}")
                    flash("Database error occurred.", "alert-danger")
            else:
                flash("Class not found!", "alert-warning")
    classes = Classes.query.order_by(Classes.hierarchy).all()
    return render_template("admin/classes/manage_classes.html", form=form, classes=classes)

@admin_bp.route("/delete-class/<int:class_id>", methods=["POST"])
@login_required
def delete_class(class_id):
    """Delete a class if no active students are enrolled."""
    cls = Classes.query.get(class_id)
    if cls:
        try:
            active_students = StudentClassHistory.query.filter_by(class_id=class_id, is_active=True, leave_date=None).count()
            if active_students > 0:
                flash("Cannot delete class with active student enrollments.", "alert-danger")
            else:
                db.session.delete(cls)
                db.session.commit()
                flash("Class deleted successfully!", "alert-success")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error deleting class {class_id}: {str(e)}")
            flash("Database error occurred.", "alert-danger")
    else:
        flash("Class not found!", "alert-warning")
    return redirect(url_for("admins.manage_classes"))

@admin_bp.route("/select_class/<string:action>", methods=["GET", "POST"])
@login_required
def select_class(action):
    """Select a class to view its students."""
    class_form = classForm()
    class_form.class_name.choices = [(cls.name, f"{cls.name}") for cls in Classes.query.order_by(Classes.hierarchy).all()]

    if class_form.validate_on_submit():
        class_name = class_form.class_name.data
        class_name = unquote(class_name).strip()
        app.logger.info(f"Selected class: {class_name}")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))
    return render_template("admin/classes/select_class.html", class_form=class_form, action=action)

@admin_bp.route("/students_by_class/<string:class_name>/<string:action>", methods=["GET", "POST"])
@login_required
def students_by_class(class_name, action):
    """View students in a specific class."""
    class_name = unquote(class_name).strip()
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        flash("No current session or term available.", "alert-danger")
        return redirect(url_for("admins.select_class", action=action))

    class_record = Classes.query.filter_by(name=class_name).first()
    if not class_record:
        return jsonify({"error": f"Class '{class_name}' not found."}), 404

    form = DeleteForm()
    page = request.args.get('page', 1, type=int)
    per_page = 5
    term = request.args.get('term', current_term.value)
    term_order = {t.value: i for i, t in enumerate(TermEnum, 1)}
    target_term_order = term_order.get(term, 1)

    try:
        student_histories_query = (
            db.session.query(StudentClassHistory)
            .join(Student, StudentClassHistory.student_id == Student.id)
            .filter(
                StudentClassHistory.session_id == current_session.id,
                StudentClassHistory.class_id == class_record.id,
                StudentClassHistory.is_active == True,
                StudentClassHistory.leave_date.is_(None),
                case(
                    *[(StudentClassHistory.start_term == t.value, i) for i, t in enumerate(TermEnum, 1)],
                    else_=1
                ) <= target_term_order,
                or_(
                    StudentClassHistory.end_term.is_(None),
                    case(
                        *[(StudentClassHistory.end_term == t.value, i) for i, t in enumerate(TermEnum, 1)],
                        else_=4
                    ) >= target_term_order
                )
            )
            .order_by(Student.last_name.asc())
        )
        student_histories_pagination = student_histories_query.paginate(page=page, per_page=per_page, error_out=False)
        students = [history.student for history in student_histories_pagination.items]

        return render_template(
            "admin/classes/students_by_class.html",
            students=students,
            session_year=current_session.year,
            current_session=current_session,
            class_name=class_name,
            form=form,
            current_term=current_term.value,
            action=action,
            pagination=student_histories_pagination
        )
    except OperationalError as e:
        app.logger.error(f"Database error fetching students for class {class_name}: {str(e)}")
        flash("Database error occurred while fetching students.", "alert-danger")
        return redirect(url_for("admins.select_class", action=action))

@admin_bp.route("/promote_student/<string:class_name>/<int:student_id>/<string:action>", methods=["POST"])
@login_required
def promote_student(class_name, student_id, action):
    """Promote a student to the next class."""
    student = Student.query.get_or_404(student_id)
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    class_name = unquote(class_name).strip()
    if not current_session or not current_term:
        flash("No current session or term available.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    current_class = Classes.query.filter_by(name=class_name).first_or_404()
    session_choice = request.form.get("session_choice", "next")
    target_session = current_session if session_choice == "current" else Session.query.filter(Session.year > current_session.year).order_by(Session.year.asc()).first()
    if session_choice == "next" and not target_session:
        flash("No next academic session available.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    next_class = Classes.get_next_class(current_class.hierarchy)
    if not next_class:
        flash("This student has completed the highest class.", "alert-warning")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    try:
        current_enrollment = StudentClassHistory.query.filter_by(
            student_id=student.id,
            session_id=current_session.id,
            is_active=True,
            leave_date=None
        ).first()
        if session_choice == "current" and current_enrollment:
            current_enrollment.class_id = next_class.id
        else:
            if current_enrollment:
                current_enrollment.end_term = current_term.value
                current_enrollment.leave_date = datetime.utcnow()
                current_enrollment.is_active = False

            existing_record = StudentClassHistory.query.filter_by(
                student_id=student.id,
                session_id=target_session.id,
                is_active=True,
                leave_date=None
            ).first()
            if existing_record:
                existing_record.class_id = next_class.id
            else:
                new_class_history = StudentClassHistory(
                    student_id=student.id,
                    session_id=target_session.id,
                    class_id=next_class.id,
                    start_term=current_term.value if session_choice == "current" else TermEnum.FIRST.value,
                    join_date=datetime.utcnow(),
                    is_active=True
                )
                db.session.add(new_class_history)

        db.session.commit()
        session_label = "current session" if session_choice == "current" else f"{target_session.year}"
        flash(f"{student.first_name} promoted to {next_class.name} in {session_label}.", "alert-success")
        return redirect(url_for("admins.students_by_class", class_name=next_class.name, action=action))
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error promoting student {student_id}: {str(e)}")
        flash("Database error occurred.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

@admin_bp.route("/demote_student/<string:class_name>/<int:student_id>/<string:action>", methods=["POST"])
@login_required
def demote_student(class_name, student_id, action):
    """Demote a student to the previous class."""
    student = Student.query.get_or_404(student_id)
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    class_name = unquote(class_name).strip()
    if not current_session or not current_term:
        flash("No current session or term available.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    current_class = Classes.query.filter_by(name=class_name).first_or_404()
    session_choice = request.form.get("session_choice", "next")
    target_session = current_session if session_choice == "current" else Session.query.filter(Session.year > current_session.year).order_by(Session.year.asc()).first()
    if session_choice == "next" and not target_session:
        flash("No next academic session available.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    previous_class = Classes.get_previous_class(current_class.hierarchy)
    if not previous_class:
        flash("This student is already in the lowest class.", "alert-warning")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    try:
        current_enrollment = StudentClassHistory.query.filter_by(
            student_id=student.id,
            session_id=current_session.id,
            is_active=True,
            leave_date=None
        ).first()
        if session_choice == "current" and current_enrollment:
            current_enrollment.class_id = previous_class.id
        else:
            if current_enrollment:
                current_enrollment.end_term = current_term.value
                current_enrollment.leave_date = datetime.utcnow()
                current_enrollment.is_active = False

            existing_record = StudentClassHistory.query.filter_by(
                student_id=student.id,
                session_id=target_session.id,
                is_active=True,
                leave_date=None
            ).first()
            if existing_record:
                existing_record.class_id = previous_class.id
            else:
                new_class_history = StudentClassHistory(
                    student_id=student.id,
                    session_id=target_session.id,
                    class_id=previous_class.id,
                    start_term=current_term.value if session_choice == "current" else TermEnum.FIRST.value,
                    join_date=datetime.utcnow(),
                    is_active=True
                )
                db.session.add(new_class_history)

        db.session.commit()
        session_label = "current session" if session_choice == "current" else f"{target_session.year}"
        flash(f"{student.first_name} demoted to {previous_class.name} in {session_label}.", "alert-success")
        return redirect(url_for("admins.students_by_class", class_name=previous_class.name, action=action))
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error demoting student {student_id}: {str(e)}")
        flash("Database error occurred.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

@admin_bp.route("/delete_student_class_record/<string:class_name>/<int:student_id>/<string:action>", methods=["POST"])
@login_required
def delete_student_class_record(class_name, student_id, action):
    """Mark a student's class record as inactive."""
    student = Student.query.get_or_404(student_id)
    class_name = unquote(class_name).strip()
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        flash("No current session or term available.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    try:
        class_record = StudentClassHistory.query.filter_by(
            student_id=student.id,
            session_id=current_session.id,
            class_id=Classes.query.filter_by(name=class_name).first().id,
            is_active=True,
            leave_date=None
        ).first()
        if not class_record:
            flash(f"No active class record found for {student.first_name} in {class_name}.", "alert-warning")
            return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

        class_record.end_term = current_term.value
        class_record.leave_date = datetime.utcnow()
        class_record.is_active = False
        db.session.commit()
        flash(f"Class record for {student.first_name} marked inactive in {current_term.value} term.", "alert-success")
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error deleting student record {student_id}: {str(e)}")
        flash("Database error occurred.", "alert-danger")
    return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

# ------------------------------
# Subject Management
# ------------------------------

@admin_bp.route("/manage_subjects", methods=["GET", "POST"])
@login_required
def manage_subjects():
    """Manage subjects (add, deactivate)."""
    form = SubjectForm()
    if form.validate_on_submit():
        subjects_input = form.name.data
        subject_names = [name.strip() for name in subjects_input.split(",")]
        try:
            for subject_name in subject_names:
                for section in form.section.data:
                    if not Subject.query.filter_by(name=subject_name, section=section, deactivated=False).first():
                        subject = Subject(name=subject_name, section=section)
                        db.session.add(subject)
                    else:
                        flash(f"Subject '{subject_name}' already exists!", "alert-warning")
            db.session.commit()
            flash("Subject(s) added successfully!", "alert-success")
            return redirect(url_for("admins.manage_subjects"))
        except IntegrityError as e:
            db.session.rollback()
            app.logger.error(f"Integrity error adding subjects: {str(e)}")
            flash("Failed to add subjects: Duplicate name/section.", "alert-danger")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error adding subjects: {str(e)}")
            flash("Database error occurred.", "alert-danger")

    if request.method == "POST" and "deactivate_subject_id" in request.form:
        try:
            subject_id = int(request.form.get("deactivate_subject_id"))
            subject = Subject.query.get(subject_id)
            if subject:
                subject.deactivated = True
                db.session.commit()
                flash(f"Subject '{subject.name}' deactivated.", "alert-warning")
            else:
                flash("Subject not found.", "alert-warning")
            return redirect(url_for("admins.manage_subjects"))
        except ValueError:
            flash("Invalid subject ID.", "alert-danger")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error deactivating subject: {str(e)}")
            flash("Database error occurred.", "alert-danger")

    subjects = Subject.query.order_by(Subject.section).all()
    subjects_by_section = {subject.section: [] for subject in subjects}
    for subject in subjects:
        subjects_by_section[subject.section].append(subject)

    delete_form = DeleteForm()
    return render_template(
        "admin/subjects/subject_admin.html",
        form=form,
        subjects_by_section=subjects_by_section,
        delete_form=delete_form
    )

@admin_bp.route("/edit_subject/<int:subject_id>", methods=["GET", "POST"])
@login_required
def edit_subject(subject_id):
    """Edit an existing subject."""
    subject = Subject.query.get_or_404(subject_id)
    form = SubjectForm(obj=subject)
    if form.validate_on_submit():
        try:
            subject.name = form.name.data
            subject.section = form.section.data
            db.session.commit()
            flash("Subject updated successfully!", "alert-success")
            return redirect(url_for("admins.manage_subjects"))
        except IntegrityError as e:
            db.session.rollback()
            app.logger.error(f"Integrity error updating subject {subject_id}: {str(e)}")
            flash("Update failed: Duplicate name/section.", "alert-danger")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error updating subject {subject_id}: {str(e)}")
            flash("Database error occurred.", "alert-danger")
    return render_template("admin/subjects/edit_subject.html", form=form, subject=subject)

@admin_bp.route("/delete_subject/<int:subject_id>", methods=["POST"])
@login_required
def delete_subject(subject_id):
    """Delete a subject and its associated scores."""
    form = DeleteForm()
    if form.validate_on_submit():
        try:
            subject = Subject.query.get_or_404(subject_id)
            Result.query.filter_by(subject_id=subject_id).delete()
            db.session.delete(subject)
            db.session.commit()
            flash("Subject and associated scores deleted successfully!", "alert-success")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error deleting subject {subject_id}: {str(e)}")
            flash("Database error occurred.", "alert-danger")
    return redirect(url_for("admins.manage_subjects"))

@admin_bp.route("/assign_subject_to_class", methods=["GET", "POST"])
@login_required
def assign_subject_to_class():
    """Assign multiple subjects to multiple classes and display assigned subjects."""
    form = AssignSubjectToClassForm()

    try:
        class_subject_data = (
            db.session.query(Classes, Subject)
            .select_from(Classes)
            .outerjoin(class_subject, Classes.id == class_subject.c.class_id)
            .outerjoin(Subject, class_subject.c.subject_id == Subject.id)
            .order_by(Classes.name, Subject.name)
            .all()
        )

        classes_with_subjects = {}
        for class_, subject in class_subject_data:
            if class_.name not in classes_with_subjects:
                classes_with_subjects[class_.name] = []
            if subject:
                classes_with_subjects[class_.name].append(subject)

        all_classes = Classes.query.order_by(Classes.name).all()
        for class_ in all_classes:
            if class_.name not in classes_with_subjects:
                classes_with_subjects[class_.name] = []

    except OperationalError as e:
        app.logger.error(f"Database error fetching classes and subjects: {str(e)}")
        flash("Database error occurred while loading data.", "alert-danger")
        classes_with_subjects = {}

    if form.validate_on_submit():
        selected_classes = form.classes.data
        selected_subjects = form.subjects.data
        try:
            changes_made = False
            class_objects = Classes.query.filter(Classes.id.in_(selected_classes)).all()
            subject_objects = Subject.query.filter(Subject.id.in_(selected_subjects)).all()
            for class_ in class_objects:
                for subject in subject_objects:
                    if subject not in class_.subjects:
                        class_.subjects.append(subject)
                        changes_made = True
                        app.logger.info(f"Assigned subject {subject.id} to class {class_.id} by user {current_user.username}")
            if changes_made:
                db.session.commit()
                flash(f"Assigned {len(selected_subjects)} subject(s) to {len(selected_classes)} class(es) successfully!", "alert-success")
            else:
                flash("No new assignments were made; all selected subjects were already assigned.", "alert-warning")
            return redirect(url_for("admins.assign_subject_to_class"))
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error during bulk assignment: {str(e)}")
            flash("Database error occurred.", "alert-danger")
    return render_template(
        "admin/subjects/assign_subject_to_class.html",
        form=form,
        classes_with_subjects=classes_with_subjects
    )

@admin_bp.route("/remove_subject_from_class", methods=["POST"])
@login_required
def remove_subject_from_class():
    """Remove a subject from a class."""
    class_id = request.form.get("class_id", type=int)
    subject_id = request.form.get("subject_id", type=int)
    form = DeleteForm()

    if not class_id or not subject_id:
        flash("Invalid class or subject ID.", "alert-danger")
        return redirect(url_for("admins.assign_subject_to_class"))

    try:
        class_ = Classes.query.get(class_id)
        subject = Subject.query.get(subject_id)
        if not class_ or not subject:
            flash("Class or subject not found.", "alert-danger")
            return redirect(url_for("admins.assign_subject_to_class"))

        if subject in class_.subjects:
            class_.subjects.remove(subject)
            db.session.commit()
            flash(f"Removed {subject.name} from {class_.name} successfully.", "alert-success")
        else:
            flash(f"{subject.name} was not assigned to {class_.name}.", "alert-warning")
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error removing subject {subject_id} from class {class_id}: {str(e)}")
        flash("Database error occurred during removal.", "alert-danger")
    return redirect(url_for("admins.assign_subject_to_class", form=form))

@admin_bp.route("/edit_subject_assignment/<class_name>", methods=["GET", "POST"])
@login_required
def edit_subject_assignment(class_name):
    """Edit subject assignments for a specific class."""
    class_ = Classes.query.filter_by(name=class_name).first_or_404()
    form = AssignSubjectToClassForm()

    if request.method == "GET":
        form.classes.data = [class_.id]
        form.subjects.data = [subject.id for subject in class_.subjects.all()]

    if form.validate_on_submit():
        selected_subjects = form.subjects.data
        try:
            subject_objects = Subject.query.filter(Subject.id.in_(selected_subjects)).all()
            class_.subjects.clear()
            for subject in subject_objects:
                class_.subjects.append(subject)
            db.session.commit()
            flash(f"Updated subjects for {class_name} successfully.", "alert-success")
            return redirect(url_for("admins.assign_subject_to_class"))
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error updating subjects for class {class_.id}: {str(e)}")
            flash("Database error occurred.", "alert-danger")
    return render_template(
        "admin/subjects/edit_subject_assignment.html",
        form=form,
        class_name=class_name
    )

@admin_bp.route("/merge_subjects", methods=["GET", "POST"])
@login_required
def merge_subjects():
    """Merge duplicate subjects into a single subject."""
    if not current_user.privileges or not current_user.privileges.can_manage_subjects:
        flash("You do not have permission to merge subjects.", "alert-danger")
        return redirect(url_for("admins.admin_dashboard"))

    form = SubjectForm()

    if request.method == "POST":
        fully_common_subjects = {
            "Mathematics": {"old_ids": [40, 95, 125], "new_id": 200},
            "English Language": {"old_ids": [43, 109, 126], "new_id": 201},
            "Agricultural Science": {"old_ids": [58, 73, 100], "new_id": 202},
            "Christian Religious Studies": {"old_ids": [67, 87, 105, 129], "new_id": 203},
            "Civic Education": {"old_ids": [66, 83, 104, 133], "new_id": 204},
            "Home Economics": {"old_ids": [74, 91, 101], "new_id": 205},
            "Information Technology": {"old_ids": [71, 79, 96, 136], "new_id": 206},
            "Igbo Language": {"old_ids": [63, 94, 107], "new_id": 207},
            "Physical and Health Education": {"old_ids": [81, 110, 119], "new_id": 208},
        }
        partially_common_subjects = {
            "Calligraphy": {"old_ids": [209], "new_id": 221, "section": "Nursery/Basic"},
            "Security Education": {"old_ids": [68, 89, 103], "new_id": 210, "section": "Nursery/Basic/Secondary"},
            "Basic Science": {"old_ids": [46, 98], "new_id": 211, "section": "Basic/Secondary"},
            "Basic Technology": {"old_ids": [48, 99], "new_id": 212, "section": "Basic/Secondary"},
            "Creative and Cultural Arts": {"old_ids": [75, 106], "new_id": 213, "section": "Nursery/Basic"},
            "Social Studies": {"old_ids": [85, 102], "new_id": 214, "section": "Basic/Secondary"},
            "General Studies": {"old_ids": [215], "new_id": 216, "section": "Nursery/Basic"},
            "Quantitative Reasoning": {"old_ids": [64, 97], "new_id": 217, "section": "Nursery/Basic"},
            "Verbal Reasoning": {"old_ids": [62, 111], "new_id": 218, "section": "Nursery/Basic"},
            "Poetry": {"old_ids": [61, 114], "new_id": 219, "section": "Nursery/Basic"},
            "History": {"old_ids": [54, 108], "new_id": 220, "section": "Basic/Secondary"},
        }

        try:
            for name, info in fully_common_subjects.items():
                if not Subject.query.get(info["new_id"]):
                    new_subject = Subject(id=info["new_id"], name=name, section=None, deactivated=False)
                    db.session.add(new_subject)
            for name, info in partially_common_subjects.items():
                if not Subject.query.get(info["new_id"]):
                    new_subject = Subject(id=info["new_id"], name=name, section=info["section"], deactivated=False)
                    db.session.add(new_subject)
            db.session.commit()

            for name, info in fully_common_subjects.items():
                old_ids = info["old_ids"]
                new_id = info["new_id"]
                Result.query.filter(Result.subject_id.in_(old_ids)).update(
                    {Result.subject_id: new_id}, synchronize_session=False
                )
                db.session.execute(
                    text("UPDATE class_subject SET subject_id = :new_id WHERE subject_id IN :old_ids"),
                    {"new_id": new_id, "old_ids": tuple(old_ids)}
                )
                db.session.execute(
                    text("UPDATE teacher_subject SET subject_id = :new_id WHERE subject_id IN :old_ids"),
                    {"new_id": new_id, "old_ids": tuple(old_ids)}
                )
            for name, info in partially_common_subjects.items():
                old_ids = info["old_ids"]
                new_id = info["new_id"]
                Result.query.filter(Result.subject_id.in_(old_ids)).update(
                    {Result.subject_id: new_id}, synchronize_session=False
                )
                db.session.execute(
                    text("UPDATE class_subject SET subject_id = :new_id WHERE subject_id IN :old_ids"),
                    {"new_id": new_id, "old_ids": tuple(old_ids)}
                )
                db.session.execute(
                    text("UPDATE teacher_subject SET subject_id = :new_id WHERE subject_id IN :old_ids"),
                    {"new_id": new_id, "old_ids": tuple(old_ids)}
                )

            db.session.commit()

            for name, info in fully_common_subjects.items():
                Subject.query.filter(Subject.id.in_(info["old_ids"])).delete(synchronize_session=False)
            for name, info in partially_common_subjects.items():
                Subject.query.filter(Subject.id.in_(info["old_ids"])).delete(synchronize_session=False)

            db.session.commit()
            flash("Subjects merged successfully!", "alert-success")
            return redirect(url_for("admins.manage_subjects"))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error merging subjects: {str(e)}")
            flash(f"Error merging subjects: {str(e)}", "alert-danger")
    return render_template("admin/subjects/merge_subjects.html", form=form)

# ------------------------------
# Result Management
# ------------------------------

@admin_bp.route("/manage_results/<string:class_name>/<int:student_id>/<string:action>", methods=["GET"])
@login_required
def manage_results(class_name, student_id, action):
    """Manage a student's results for a specific class."""
    student = Student.query.get_or_404(student_id)
    class_name = unquote(class_name).strip()
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        flash("No current session or term available.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    class_record = Classes.query.filter_by(name=class_name).first_or_404()
    enrollment = StudentClassHistory.query.filter_by(
        student_id=student.id,
        session_id=current_session.id,
        is_active=True,
        leave_date=None,
        class_id=class_record.id
    ).first()
    if not enrollment:
        flash("Student not enrolled in this class.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    subjects = get_subjects_by_class_name(class_record.id, include_deactivated=(current_session.year == "2023/2024"))
    result_form = ResultForm(term=current_term.value, session=current_session.id)
    form = ManageResultsForm()

    results = Result.query.filter_by(
        student_id=student.id,
        term=current_term.value,
        session_id=current_session.id,
        class_id=class_record.id
    ).all()
    results_dict = {result.subject_id: result for result in results}
    populate_form_with_results(form, subjects, results_dict)

    # Fetch term summary for aggregates
    term_summary = StudentTermSummary.query.filter_by(
        student_id=student.id,
        term=current_term.value,
        session_id=current_session.id,
        class_id=class_record.id
    ).first()

    details = {
        "grand_total": term_summary.grand_total if term_summary and term_summary.grand_total is not None else "",
        "last_term_average": term_summary.last_term_average if term_summary and term_summary.last_term_average is not None else "",
        "average": term_summary.term_average if term_summary and term_summary.term_average is not None else "",
        "cumulative_average": term_summary.cumulative_average if term_summary and term_summary.cumulative_average is not None else "",
        "subjects_offered": term_summary.subjects_offered if term_summary and term_summary.subjects_offered is not None else "",
        "next_term_begins": term_summary.next_term_begins if term_summary and term_summary.next_term_begins is not None else "",
        "position": term_summary.position if term_summary and term_summary.position is not None else "",
        "date_issued": term_summary.date_issued if term_summary and term_summary.date_issued is not None else "",
        "principal_remark": term_summary.principal_remark if term_summary and term_summary.principal_remark is not None else "",
        "teacher_remark": term_summary.teacher_remark if term_summary and term_summary.teacher_remark is not None else ""
    }

    return render_template(
        "admin/results/manage_results.html",
        student=student,
        subjects=subjects,
        form=form,
        result_form=result_form,
        term=current_term.value,
        subject_results=zip(subjects, form.subjects),
        class_name=class_name,
        session=current_session.id,
        session_year=current_session.year,
        class_record=class_record,
        results_dict=results_dict,
        results=results,
        action=action,
        school_name=app.config.get("SCHOOL_NAME", "Aunty Anne's International School"),
        **details
    )

@admin_bp.route("/update_result/<string:class_name>/<int:student_id>/<string:action>", methods=["POST"])
@login_required
def update_result(class_name, student_id, action):
    """Update a student's results for a specific class."""
    student = Student.query.get_or_404(student_id)
    class_name = unquote(class_name).strip()
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        flash("No current session or term available.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    class_record = Classes.query.filter_by(name=class_name).first_or_404()
    enrollment = StudentClassHistory.query.filter_by(
        student_id=student.id,
        session_id=current_session.id,
        is_active=True,
        leave_date=None,
        class_id=class_record.id
    ).first()
    if not enrollment:
        flash("Student not enrolled in this class.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    result_form = ResultForm(term=current_term.value, session=current_session.id)
    form = ManageResultsForm()
    if form.validate_on_submit():
        try:
            update_results_helper(
                student=student,
                term=current_term.value,
                session_id=current_session.id,
                form=form,
                result_form=result_form,
                class_id=class_record.id
            )
            db.session.commit()
            flash("Results updated successfully.", "alert-success")
            return redirect(url_for("admins.manage_results", class_name=class_name, student_id=student.id, action=action))
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error updating results for student {student_id}: {str(e)}")
            flash("Database error occurred.", "alert-danger")
    return redirect(url_for("admins.manage_results", class_name=class_name, student_id=student.id, action=action))

class ResultUpdateSchema(Schema):
    student_id = fields.Integer(required=True)
    subject_id = fields.Integer(required=False, allow_none=False)
    class_id = fields.Integer(required=True)
    class_assessment = fields.Integer(allow_none=True, load_default=None)
    summative_test = fields.Integer(allow_none=True, load_default=None)
    exam = fields.Integer(allow_none=True, load_default=None)
    position = fields.Str(allow_none=True, load_default=None)

    @validates_schema
    def validate_student_specific_fields(self, data, **kwargs):
        if any(data.get(field) is not None for field in ["class_assessment", "summative_test", "exam"]):
            if data.get("subject_id") is None:
                raise ValidationError("subject_id is required for score updates.", "subject_id")


@admin_bp.route("/update_result_field", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def update_result_field():
    """Update a specific result field via AJAX."""
    try:
        data = ResultUpdateSchema().load(request.get_json())
        data['next_term_begins'] = bleach.clean(data.get('next_term_begins', '')) if data.get('next_term_begins') else None
        data['position'] = bleach.clean(data.get('position', '')) if data.get('position') else None
        data['date_issued'] = bleach.clean(data.get('date_issued', '')) if data.get('date_issued') else None

        current_session, current_term = Session.get_current_session_and_term(include_term=True)
        if not current_session or not current_term:
            return jsonify({"status": "error", "message": "No active session or term found."}), 400

        # Save the result and get the updated object
        result = save_result(
            student_id=data["student_id"],
            subject_id=data["subject_id"],
            term=current_term.value,
            session_id=current_session.id,
            data=data,
            class_id=data["class_id"]
        )
        db.session.add(AuditLog(user_id=current_user.id, action=f"Updated result for student {data['student_id']} in subject {data['subject_id']}"))
        db.session.commit()
        app.logger.info(f"Result updated for student {data['student_id']} in subject {data['subject_id']} by user {current_user.username}")

        # Fetch term summary for aggregates
        term_summary = StudentTermSummary.query.filter_by(
            student_id=data["student_id"],
            term=current_term.value,
            session_id=current_session.id,
            class_id=data["class_id"]
        ).first()

        return jsonify({
            "status": "success",
            "message": "Result saved successfully.",
            "total": result.total,
            "grade": result.grade,
            "remark": result.remark,
            "principal_remark": term_summary.principal_remark if term_summary else None,
            "teacher_remark": term_summary.teacher_remark if term_summary else None,
            "grand_total": term_summary.grand_total if term_summary else None,
            "term_average": term_summary.term_average if term_summary else None,
            "cumulative_average": term_summary.cumulative_average if term_summary else None,
            "subjects_offered": term_summary.subjects_offered if term_summary else None
        })
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e.messages)}), 400
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error in update_result_field: {str(e)}")
        return jsonify({"status": "error", "message": "Database error occurred."}), 500

@admin_bp.route("/broadsheet/<string:class_name>/<string:action>", methods=["GET", "POST"])
@login_required
def broadsheet(class_name, action):
    """Generate and display a broadsheet for a class."""
    class_name = unquote(class_name).strip()
    form = classForm()
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        flash("Current session or term not set.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

    class_record = Classes.query.filter_by(name=class_name).first_or_404()
    student_class_histories = (
        StudentClassHistory.query.filter(
            StudentClassHistory.session_id == current_session.id,
            StudentClassHistory.class_id == class_record.id,
            StudentClassHistory.is_active == True,
            StudentClassHistory.leave_date.is_(None)
        ).options(joinedload(StudentClassHistory.student)).all()
    )
    students = [history.student for history in student_class_histories]
    subjects = get_subjects_by_class_name(class_record.id)

    if not students or not subjects:
        flash(f"No active students or subjects for {class_name}.", "alert-info")
        return render_template(
            "admin/results/broadsheet.html",
            students=[],
            subjects=[],
            broadsheet_data=[],
            subject_averages={},
            class_name=class_name,
            action=action
        )

    broadsheet_data, subject_averages = prepare_broadsheet_data(
        students=students,
        subjects=subjects,
        term=current_term.value,
        session_year=current_session.year,
        class_id=class_record.id,
        session_id=current_session.id
    )
    return render_template(
        "admin/results/broadsheet.html",
        students=students,
        subjects=subjects,
        broadsheet_data=broadsheet_data,
        subject_averages=subject_averages,
        class_name=class_name,
        class_record=class_record,
        current_session=current_session.id,
        session_year=current_session.year,
        current_term=current_term.value,
        form=form,
        action=action
    )

@admin_bp.route("/update-broadsheet/<string:class_name>/<string:action>", methods=["POST"])
@login_required
def update_broadsheet(class_name, action):
    """Update broadsheet data for a class."""
    class_name = unquote(class_name).strip()
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        flash("Current session or term not set.", "alert-danger")
        return redirect(url_for("admins.broadsheet", class_name=class_name, action=action))

    class_record = Classes.query.filter_by(name=class_name).first_or_404()
    student_class_histories = (
        StudentClassHistory.query.filter(
            StudentClassHistory.session_id == current_session.id,
            StudentClassHistory.class_id == class_record.id,
            StudentClassHistory.is_active == True,
            StudentClassHistory.leave_date.is_(None)
        ).options(joinedload(StudentClassHistory.student)).all()
    )
    students = [history.student for history in student_class_histories]
    subjects = get_subjects_by_class_name(class_name)

    # Parse form data
    results_data = {}
    for key, value in request.form.items():
        if key.startswith('results['):
            match = re.match(r'results\[(\d+)\]\[(\d+)\]\[(\w+)\]', key)
            if match:
                student_id, subject_id, field = match.groups()
                student_id, subject_id = int(student_id), int(subject_id)
                value = None if not value.strip() else int(value)
                results_data.setdefault(student_id, {}).setdefault(subject_id, {})[field] = value
        elif key.startswith('position['):
            match = re.match(r'position\[(\d+)\]', key)
            if match:
                student_id = int(match.group(1))
                results_data.setdefault(student_id, {}).setdefault('position', value.strip() or None)
        elif key.startswith('next_term_begins['):
            match = re.match(r'next_term_begins\[(\d+)\]', key)
            if match:
                student_id = int(match.group(1))
                results_data.setdefault(student_id, {}).setdefault('next_term_begins', value.strip() or None)
        elif key.startswith('date_issued['):
            match = re.match(r'date_issued\[(\d+)\]', key)
            if match:
                student_id = int(match.group(1))
                results_data.setdefault(student_id, {}).setdefault('date_issued', value.strip() or None)

    if not results_data:
        flash("No data submitted for update.", "alert-danger")
        return redirect(url_for('admins.broadsheet', class_name=class_name, action=action))

    try:
        for student_id, data in results_data.items():
            subject_scores = {k: v for k, v in data.items() if k not in ['position', 'next_term_begins', 'date_issued']}
            position = data.get('position')
            next_term_begins = data.get('next_term_begins')
            date_issued = data.get('date_issued')
            for subject_id, scores in subject_scores.items():
                update_data = {
                    "class_assessment": scores.get("class_assessment"),
                    "summative_test": scores.get("summative_test"),
                    "exam": scores.get("exam"),
                    "next_term_begins": next_term_begins,
                    "date_issued": date_issued,
                    "position": position
                }
                save_result(
                    student_id=student_id,
                    subject_id=subject_id,
                    term=current_term.value,
                    session_id=current_session.id,
                    data=update_data,
                    class_id=class_record.id
                )
        db.session.commit()
        flash("Broadsheet updated successfully.", "alert-success")
    except ValueError as e:
        db.session.rollback()
        app.logger.error(f"Invalid data updating broadsheet for {class_name}: {str(e)}")
        flash("Invalid data submitted.", "alert-danger")
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error updating broadsheet for {class_name}: {str(e)}")
        flash("Database error occurred.", "alert-danger")
    return redirect(url_for('admins.broadsheet', class_name=class_name, action=action))

@admin_bp.route("/download_broadsheet/<string:class_name>/<string:action>", methods=["GET"])
@login_required
def download_broadsheet(class_name, action):
    """Download a broadsheet as an Excel file."""
    class_name = unquote(class_name).strip()
    if not re.match(r'^[a-zA-Z0-9-_ ]+$', class_name):
        flash("Invalid class name.", "alert-danger")
        return redirect(url_for("admins.broadsheet", class_name=class_name, action=action))

    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        flash("No current session or term set.", "alert-danger")
        return redirect(url_for("admins.broadsheet", class_name=class_name, action=action))

    class_record = Classes.query.filter_by(name=class_name).first_or_404()
    student_class_histories = (
        StudentClassHistory.query.filter(
            StudentClassHistory.session_id == current_session.id,
            StudentClassHistory.class_id == class_record.id,
            StudentClassHistory.is_active == True,
            StudentClassHistory.leave_date.is_(None)
        ).options(joinedload(StudentClassHistory.student)).all()
    )
    students = [history.student for history in student_class_histories]
    subjects = get_subjects_by_class_name(class_record.id)

    if not students or not subjects:
        flash(f"No active students or subjects found for {class_name}.", "alert-info")
        return redirect(url_for("admins.broadsheet", class_name=class_name, action=action))

    broadsheet_data, subject_averages = prepare_broadsheet_data(
        students=students,
        subjects=subjects,
        term=current_term.value,
        session_year=current_session.year,
        class_id=class_record.id,
        session_id=current_session.id
    )
    output = generate_excel_broadsheet(class_name, current_term.value, current_session.year, broadsheet_data, subjects, subject_averages)

    filename = f"Broadsheet_{class_name}_{current_term.value}_{current_session.year}.xlsx"
    db.session.add(AuditLog(user_id=current_user.id, action=f"Downloaded broadsheet for {class_name}"))
    db.session.commit()
    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@admin_bp.route("/update_broadsheet_field", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def update_broadsheet_field():
    try:
        data = ResultUpdateSchema().load(request.get_json())
        app.logger.info(f"Received data: {data}")
        position = data.get('position')
        data['position'] = bleach.clean(position) if position is not None else None  # Only clean if position is provided

        current_session, current_term = Session.get_current_session_and_term(include_term=True)
        if not current_session or not current_term:
            app.logger.error("No active session or term found.")
            return jsonify({"status": "error", "message": "No active session or term found."}), 400

        class_id = data["class_id"]
        student_id = data["student_id"]
        subject_id = data.get("subject_id")

        student = Student.query.get(student_id)
        if not student:
            app.logger.error(f"Student with ID {student_id} not found.")
            return jsonify({"status": "error", "message": f"Student with ID {student_id} not found."}), 400

        if subject_id:
            subject = Subject.query.get(subject_id)
            if not subject:
                app.logger.error(f"Subject with ID {subject_id} not found.")
                return jsonify({"status": "error", "message": f"Subject with ID {subject_id} not found."}), 400

        class_obj = Classes.query.get(class_id)
        if not class_obj:
            app.logger.error(f"Class with ID {class_id} not found.")
            return jsonify({"status": "error", "message": f"Class with ID {class_id} not found."}), 400

        result = save_result(
            student_id=student_id,
            subject_id=subject_id if subject_id else None,
            term=current_term.value,
            session_id=current_session.id,
            data=data,
            class_id=class_id
        )
        db.session.add(AuditLog(user_id=current_user.id, action=f"Updated broadsheet field for student {student_id} {'in subject ' + str(subject_id) if subject_id else 'position'}"))
        db.session.commit()

        term_summary = StudentTermSummary.query.filter_by(
            student_id=student_id,
            term=current_term.value,
            session_id=current_session.id,
            class_id=class_id
        ).first()

        response = {
            "status": "success",
            "message": "Result saved successfully.",
            "class_assessment": result.class_assessment if result and result.class_assessment is not None else '',
            "summative_test": result.summative_test if result and result.summative_test is not None else '',
            "exam": result.exam if result and result.exam is not None else '',
            "total": result.total if result and result.total is not None else '',
            "grade": result.grade or '' if result else '',
            "remark": result.remark or '' if result else '',
            "grand_total": term_summary.grand_total if term_summary and term_summary.grand_total is not None else '',
            "term_average": term_summary.term_average if term_summary and term_summary.term_average is not None else '',
            "cumulative_average": term_summary.cumulative_average if term_summary and term_summary.cumulative_average is not None else '',
            "subjects_offered": term_summary.subjects_offered if term_summary and term_summary.subjects_offered is not None else '',
            "position": term_summary.position if term_summary and term_summary.position is not None else '',
            "principal_remark": term_summary.principal_remark if term_summary else '',
            "teacher_remark": term_summary.teacher_remark if term_summary else '',
            "next_term_begins": term_summary.next_term_begins if term_summary and term_summary.next_term_begins else '',
            "date_issued": term_summary.date_issued if term_summary and term_summary.date_issued else ''
        }
        return jsonify(response)

    except ValidationError as e:
        db.session.rollback()
        app.logger.error(f"Validation error: {str(e.messages)}")
        return jsonify({"status": "error", "message": str(e.messages)}), 400
    except ValueError as e:
        db.session.rollback()
        app.logger.error(f"Value error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error: {str(e)}")
        return jsonify({"status": "error", "message": "Database error occurred."}), 500
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error: {str(e)}, Data: {request.get_json()}")
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}), 500

class ClassWideUpdateSchema(Schema):
    class_id = fields.Integer(required=True)
    next_term_begins = fields.Str(allow_none=True, load_default=None)
    date_issued = fields.Str(allow_none=True, load_default=None)

    # @validates_schema
    # def validate_at_least_one_field(self, data, **kwargs):
    #     if data.get("next_term_begins") is None and data.get("date_issued") is None:
    #         raise ValidationError("At least one of next_term_begins or date_issued must be provided.")


@admin_bp.route("/update_broadsheet_class_fields", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def update_broadsheet_class_fields():
    """Update class-wide fields (next_term_begins, date_issued) via AJAX."""
    try:
        data = ClassWideUpdateSchema().load(request.get_json())
        app.logger.info(f"Received data: {data}")

        next_term_begins = data.get('next_term_begins')
        date_issued = data.get('date_issued')
        data['next_term_begins'] = bleach.clean(next_term_begins) if next_term_begins is not None else None
        data['date_issued'] = bleach.clean(date_issued) if date_issued is not None else None

        current_session, current_term = Session.get_current_session_and_term(include_term=True)
        if not current_session or not current_term:
            return jsonify({"status": "error", "message": "No active session or term found."}), 400

        class_id = data["class_id"]
        updated_count = save_class_wide_fields(
            class_id=class_id,
            session_id=current_session.id,
            term=current_term.value,
            data=data
        )

        if updated_count > 0:
            db.session.add(AuditLog(user_id=current_user.id, action=f"Updated next_term_begins/date_issued for class {class_id}"))
            db.session.commit()
            return jsonify({"status": "success", "message": "Class-wide update successful."})
        else:
            db.session.rollback()
            return jsonify({"status": "success", "message": "No changes detected or no students found."})

    except ValidationError as e:
        app.logger.error(f"Validation error in update_broadsheet_class_fields: {str(e.messages)}")
        return jsonify({"status": "error", "message": str(e.messages)}), 400
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error in update_broadsheet_class_fields: {str(e)}")
        return jsonify({"status": "error", "message": "Database error occurred."}), 500
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error in update_broadsheet_class_fields: {str(e)}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

# ------------------------------
# Teacher Management
# ------------------------------

@admin_bp.route("/teachers", methods=["GET", "POST"])
@login_required
def manage_teachers():
    """Manage teachers (add, edit)."""
    teachers = Teacher.query.all()
    form = TeacherForm()
    if form.validate_on_submit():
        teacher_id = form.id.data
        first_name = form.first_name.data.strip()
        last_name = form.last_name.data.strip()
        phone_number = form.phone_number.data.strip() if form.phone_number.data else None
        section = form.section.data

        if not teacher_id:
            if phone_number and Teacher.query.filter_by(phone_number=phone_number).first():
                flash("Phone number already associated with another teacher!", "alert-danger")
            else:
                employee_id = generate_employee_id(first_name, last_name)
                if Teacher.query.filter_by(employee_id=employee_id).first():
                    flash("Employee ID already exists! Try again.", "alert-danger")
                else:
                    user = User(username=employee_id, role=RoleEnum.TEACHER.value)
                    user.set_password(employee_id)
                    db.session.add(user)
                    db.session.commit()

                    new_teacher = Teacher(
                        user_id=user.id,
                        first_name=first_name,
                        last_name=last_name,
                        phone_number=phone_number,
                        section=section,
                        employee_id=employee_id
                    )
                    db.session.add(new_teacher)
                    db.session.commit()
                    flash("Teacher added successfully.", "alert-success")
            return redirect(url_for("admins.manage_teachers"))
    return render_template("admin/teachers/teachers.html", teachers=teachers, form=form)

@admin_bp.route("/delete_teacher/<int:teacher_id>", methods=["POST"])
@login_required
def delete_teacher(teacher_id):
    """Delete a teacher and their associated user account."""
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        flash("Teacher not found!", "alert-warning")
        return redirect(url_for("admins.manage_teachers"))

    try:
        # Step 1: Delete class_teacher assignments
        db.session.execute(
            class_teacher.delete().where(class_teacher.c.teacher_id == teacher_id)
        )

        # Step 2: Handle the user and its dependencies
        user = User.query.get(teacher.user_id)
        if user:
            # Delete audit_log entries (from previous fix)
            db.session.execute(
                db.delete(AuditLog).where(AuditLog.user_id == user.id)
            )
            # Delete user_session_preference entries
            db.session.execute(
                db.delete(UserSessionPreference).where(UserSessionPreference.user_id == user.id)
            )

        # Step 3: Delete the teacher and user
        db.session.delete(teacher)
        if user:
            db.session.delete(user)

        # Step 4: Commit the transaction
        db.session.commit()
        flash("Teacher and associated user deleted successfully.", "alert-success")
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error deleting teacher {teacher_id}: {str(e)}")
        flash("Database error occurred.", "alert-danger")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error deleting teacher {teacher_id}: {str(e)}")
        flash("An unexpected error occurred.", "alert-danger")

    return redirect(url_for("admins.manage_teachers"))

@admin_bp.route("/assign_subject_to_teacher", methods=["GET", "POST"])
@login_required
def assign_subject_to_teacher():
    """Assign a subject to a teacher."""
    form = AssignSubjectToTeacherForm()
    if form.validate_on_submit():
        teacher = form.teacher.data
        subject = form.subject.data
        try:
            if subject not in teacher.subjects:
                teacher.subjects.append(subject)
                db.session.commit()
                flash(f"Subject '{subject.name}' assigned to teacher '{teacher.last_name}, {teacher.first_name}'!", "alert-success")
            else:
                flash(f"Subject '{subject.name}' already assigned to teacher.", "alert-warning")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error assigning subject to teacher {teacher.id}: {str(e)}")
            flash("Database error occurred.", "alert-danger")
    return render_template("admin/teachers/assign_subject_to_teacher.html", form=form)

@admin_bp.route("/assign_teacher_to_class", methods=["GET", "POST"])
@login_required
def assign_teacher_to_class():
    """Assign a teacher to a class for a specific session and term."""
    form = AssignTeacherToClassForm()
    grouped_assignments = None

    if form.validate_on_submit():
        teacher = form.teacher.data
        class_ = form.class_name.data
        session = form.session.data
        term = form.term.data
        is_form_teacher = form.is_form_teacher.data

        try:
            existing_assignment = db.session.query(class_teacher).filter_by(
                class_id=class_.id,
                session_id=session.id,
                term=term,
                teacher_id=teacher.id
            ).first()
            if existing_assignment:
                flash(f"Teacher '{teacher.last_name}, {teacher.first_name}' already assigned to {class_.name} for {session.year} {term}.", "alert-warning")
            else:
                db.session.execute(
                    class_teacher.insert().values(
                        class_id=class_.id,
                        teacher_id=teacher.id,
                        session_id=session.id,
                        term=term,
                        is_form_teacher=is_form_teacher
                    )
                )
                db.session.commit()
                flash(f"Teacher '{teacher.last_name}, {teacher.first_name}' assigned to {class_.name} for {session.year} {term}!", "alert-success")
            return redirect(url_for("admins.assign_teacher_to_class"))
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error assigning teacher {teacher.id} to class {class_.id}: {str(e)}")
            flash("Database error occurred.", "alert-danger")

    try:
        assignments = (
            db.session.query(Teacher, Classes, Session, class_teacher.c.term, class_teacher.c.is_form_teacher)
            .select_from(Teacher)
            .join(class_teacher, Teacher.id == class_teacher.c.teacher_id)
            .join(Classes, Classes.id == class_teacher.c.class_id)
            .join(Session, Session.id == class_teacher.c.session_id)
            .order_by(Teacher.last_name, Classes.name, Session.year.desc())
            .all()
        )
        grouped_assignments = {}
        for teacher, class_, session, term, is_form_teacher in assignments:
            if teacher not in grouped_assignments:
                grouped_assignments[teacher] = []
            grouped_assignments[teacher].append((teacher, class_, session, term, is_form_teacher))
    except OperationalError as e:
        app.logger.error(f"Database error fetching teacher assignments: {str(e)}")
        flash("Database error occurred while loading assignments.", "alert-danger")

    return render_template(
        "admin/teachers/assign_teacher_to_class.html",
        form=form,
        grouped_assignments=grouped_assignments
    )


@admin_bp.route("/remove_teacher_from_class", methods=["POST"])
@login_required
def remove_teacher_from_class():
    """Remove a teacher from a class assignment."""
    form = DeleteForm()  # Assuming DeleteForm handles CSRF
    teacher_id = request.form.get("teacher_id", type=int)
    class_id = request.form.get("class_id", type=int)
    session_id = request.form.get("session_id", type=int)
    term = request.form.get("term")

    if not form.validate_on_submit():  # Check CSRF token
        flash("Invalid form submission.", "alert-danger")
        return redirect(url_for("admins.assign_teacher_to_class"))

    if not all([teacher_id, class_id, session_id, term]):
        flash("Invalid assignment details.", "alert-danger")
        return redirect(url_for("admins.assign_teacher_to_class"))

    try:
        teacher = Teacher.query.get_or_404(teacher_id)
        class_ = Classes.query.get_or_404(class_id)
        session = Session.query.get_or_404(session_id)
        assignment = db.session.query(class_teacher).filter_by(
            teacher_id=teacher_id,
            class_id=class_id,
            session_id=session_id,
            term=term
        ).first()
        if assignment:
            db.session.execute(
                class_teacher.delete().where(
                    class_teacher.c.teacher_id == teacher_id,
                    class_teacher.c.class_id == class_id,
                    class_teacher.c.session_id == session_id,
                    class_teacher.c.term == term
                )
            )
            db.session.commit()
            flash(f"Removed {teacher.last_name}, {teacher.first_name} from {class_.name} for {session.year} {term}.", "alert-success")
        else:
            flash("Assignment not found.", "alert-warning")
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error removing teacher {teacher_id} from class {class_id}: {str(e)}")
        flash("Database error occurred during removal.", "alert-danger")
    return redirect(url_for("admins.assign_teacher_to_class"))


@admin_bp.route("/edit_teacher/<int:teacher_id>", methods=["GET", "POST"])
@login_required
def edit_teacher(teacher_id):
    """Edit an existing teacher's details."""
    teacher = Teacher.query.get_or_404(teacher_id)
    form = TeacherForm(obj=teacher)
    if form.validate_on_submit():
        try:
            teacher.first_name = form.first_name.data.strip()
            teacher.last_name = form.last_name.data.strip()
            teacher.phone_number = form.phone_number.data.strip() if form.phone_number.data else None
            teacher.section = form.section.data
            db.session.commit()
            flash("Teacher updated successfully!", "alert-success")
            return redirect(url_for("admins.manage_teachers"))
        except IntegrityError as e:
            db.session.rollback()
            app.logger.error(f"Integrity error updating teacher {teacher_id}: {str(e)}")
            flash("Update failed: Duplicate phone number.", "alert-danger")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error updating teacher {teacher_id}: {str(e)}")
            flash("Database error occurred.", "alert-danger")
    return render_template("admin/teachers/edit_teacher.html", form=form, teacher=teacher)

# ------------------------------
# Utility Routes
# ------------------------------

@admin_bp.route("/approve/<int:student_id>", methods=["GET", "POST"])
@login_required
def approve(student_id):
    """Approve a student's registration."""
    student = Student.query.get_or_404(student_id)
    form = ApproveForm()
    if form.validate_on_submit():
        try:
            student.approved = True
            db.session.commit()
            flash(f"Student {student.first_name} {student.last_name} approved successfully!", "alert-success")
            return redirect(url_for("admins.students", action="view"))
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error approving student {student_id}: {str(e)}")
            flash("Database error occurred.", "alert-danger")
    return render_template("admin/students/approve.html", form=form, student=student)

@admin_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    term = request.args.get('term', current_term.value)
    term_order = {t.value: i for i, t in enumerate(TermEnum, 1)}
    target_term_order = term_order.get(term, 1)

    students_query = get_students_query(current_session, term).filter(
        StudentClassHistory.is_active == True,
        StudentClassHistory.leave_date.is_(None),
        case(
            *[(StudentClassHistory.start_term == t.value, i) for i, t in enumerate(TermEnum, 1)],
            else_=1
        ) <= target_term_order,
        or_(
            StudentClassHistory.end_term.is_(None),
            case(
                *[(StudentClassHistory.end_term == t.value, i) for i, t in enumerate(TermEnum, 1)],
                else_=4
            ) >= target_term_order
        )
    )
    total_students = students_query.count()
    approved_students = students_query.filter(Student.approved == True).count()
    fees_paid = FeePayment.query.filter_by(
        session_id=current_session.id,
        term=term,
        has_paid_fee=True
    ).join(Student).join(StudentClassHistory).filter(
        StudentClassHistory.session_id == current_session.id,
        StudentClassHistory.is_active == True,
        StudentClassHistory.leave_date.is_(None),
        case(
            *[(StudentClassHistory.start_term == t.value, i) for i, t in enumerate(TermEnum, 1)],
            else_=1
        ) <= target_term_order,
        or_(
            StudentClassHistory.end_term.is_(None),
            case(
                *[(StudentClassHistory.end_term == t.value, i) for i, t in enumerate(TermEnum, 1)],
                else_=4
            ) >= target_term_order
        )
    ).count()
    fees_unpaid = total_students - fees_paid

    return jsonify({
        "total_students": total_students,
        "approved_students": approved_students,
        "fees_paid": fees_paid,
        "fees_unpaid": fees_unpaid
    })

@admin_bp.route('/toggle_fee_status/<int:student_id>', methods=['POST'])
@login_required
def toggle_fee_status(student_id):
    """Toggle a student's fee payment status (AJAX)."""
    if current_user.role != RoleEnum.ADMIN.value:
        return jsonify({"success": False, "error": "Unauthorized access"}), 403

    student = Student.query.get_or_404(student_id)
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        return jsonify({"success": False, "error": "No active session or term found"}), 400

    try:
        fee_payment = FeePayment.query.filter_by(
            student_id=student_id,
            session_id=current_session.id,
            term=current_term.value
        ).first()
        if not fee_payment:
            fee_payment = FeePayment(
                student_id=student_id,
                session_id=current_session.id,
                term=current_term.value,
                has_paid_fee=True
            )
            db.session.add(fee_payment)
        else:
            fee_payment.has_paid_fee = not fee_payment.has_paid_fee

        db.session.commit()
        status = "paid" if fee_payment.has_paid_fee else "unpaid"
        return jsonify({
            "success": True,
            "message": f"Fee status for {student.first_name} {student.last_name} marked as {status}.",
            "has_paid_fee": fee_payment.has_paid_fee
        })
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error toggling fee status for student {student_id}: {str(e)}")
        return jsonify({"success": False, "error": "Database error occurred"}), 500

@admin_bp.route('/toggle_approval_status/<int:student_id>', methods=['POST'])
@login_required
def toggle_approval_status(student_id):
    """Toggle a student's approval status (AJAX)."""
    if current_user.role != RoleEnum.ADMIN.value:
        return jsonify({"success": False, "error": "Unauthorized access"}), 403

    student = Student.query.get_or_404(student_id)
    try:
        student.approved = not student.approved
        db.session.commit()
        status = "approved" if student.approved else "deactivated"
        return jsonify({
            "success": True,
            "message": f"{student.first_name} {student.last_name} {status} successfully",
            "approved": student.approved,
        })
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error toggling approval for student {student_id}: {str(e)}")
        return jsonify({"success": False, "error": "Database error occurred"}), 500

@admin_bp.route('/class/student_stats/<string:class_name>', methods=['GET'])
@login_required
def get_student_stats_by_class(class_name):
    class_name = unquote(class_name).strip()
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    term = request.args.get('term', current_term.value)
    term_order = {t.value: i for i, t in enumerate(TermEnum, 1)}
    target_term_order = term_order.get(term, 1)

    class_record = Classes.query.filter_by(name=class_name).first_or_404()
    students_query = get_students_query(current_session, term).filter(
        StudentClassHistory.class_id == class_record.id,
        StudentClassHistory.is_active == True,
        StudentClassHistory.leave_date.is_(None),
        case(
            *[(StudentClassHistory.start_term == t.value, i) for i, t in enumerate(TermEnum, 1)],
            else_=1
        ) <= target_term_order,
        or_(
            StudentClassHistory.end_term.is_(None),
            case(
                *[(StudentClassHistory.end_term == t.value, i) for i, t in enumerate(TermEnum, 1)],
                else_=4
            ) >= target_term_order
        )
    )
    total_students = students_query.count()
    approved_students = students_query.filter(Student.approved == True).count()
    fees_paid = FeePayment.query.filter_by(
        session_id=current_session.id,
        term=term,
        has_paid_fee=True
    ).join(Student).join(StudentClassHistory).filter(
        StudentClassHistory.class_id == class_record.id,
        StudentClassHistory.session_id == current_session.id,
        StudentClassHistory.is_active == True,
        StudentClassHistory.leave_date.is_(None),
        case(
            *[(StudentClassHistory.start_term == t.value, i) for i, t in enumerate(TermEnum, 1)],
            else_=1
        ) <= target_term_order,
        or_(
            StudentClassHistory.end_term.is_(None),
            case(
                *[(StudentClassHistory.end_term == t.value, i) for i, t in enumerate(TermEnum, 1)],
                else_=4
            ) >= target_term_order
        )
    ).count()
    fees_unpaid = total_students - fees_paid

    return jsonify({
        "total_students": total_students,
        "approved_students": approved_students,
        "fees_paid": fees_paid,
        "fees_unpaid": fees_unpaid
    })



# @admin_bp.route("/search_students", methods=["GET"])
# @login_required
# def search_students():
#     """Search students by name or registration number."""
#     query = request.args.get("query", "").strip()
#     if not query:
#         return jsonify([])

#     try:
#         current_session, current_term = Session.get_current_session_and_term(include_term=True)
#         if not current_session or not current_term:
#             return jsonify([])

#         students = (
#             Student.query.join(StudentClassHistory)
#             .filter(
#                 StudentClassHistory.session_id == current_session.id,
#                 StudentClassHistory.is_active == True,
#                 StudentClassHistory.leave_date.is_(None),
#                 or_(
#                     Student.first_name.ilike(f"%{query}%"),
#                     Student.last_name.ilike(f"%{query}%"),
#                     Student.reg_no.ilike(f"%{query}%")
#                 )
#             )
#             .limit(10)
#             .all()
#         )
#         results = [
#             {
#                 "id": student.id,
#                 "name": f"{student.first_name} {student.last_name}",
#                 "reg_no": student.reg_no,
#                 "class_name": student.current_class(current_session.id).class_ref.name if student.current_class(current_session.id) else "Unassigned"
#             }
#             for student in students
#         ]
#         return jsonify(results)
#     except OperationalError as e:
#         app.logger.error(f"Database error searching students: {str(e)}")
#         return jsonify({"error": "Database error occurred"}), 500

@admin_bp.route('/search_students/<string:action>', methods=['GET'])
@login_required
def search_students(action):
    """Search students across all classes with filtering."""
    search_query = request.args.get('query', '', type=str).strip()
    page = request.args.get('page', 1, type=int)
    enrollment_status = request.args.get('enrollment_status', 'active')
    fee_status = request.args.get('fee_status', '')
    approval_status = request.args.get('approval_status', '')

    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        flash("No active session or term found.", "alert-danger")
        return redirect(url_for("admins.manage_sessions"))

    form = DeleteForm()
    try:
        students_query = get_students_query(current_session)
        students_query = apply_filters_to_students_query(
            students_query,
            enrollment_status,
            fee_status,
            approval_status,
            current_session,
            current_term
        )
        if search_query:
            search_filter = or_(
                func.lower(Student.first_name).contains(search_query.lower()),
                func.lower(Student.last_name).contains(search_query.lower()),
                func.lower(Student.reg_no).contains(search_query.lower()),
                func.lower(Classes.name).contains(search_query.lower())
            )
            students_query = students_query.filter(search_filter)

        students_query = students_query.order_by(Classes.hierarchy, Student.last_name.asc())
        pagination = students_query.paginate(page=page, per_page=10, error_out=False)
        students_classes = group_students_by_class(pagination.items)

        if not students_classes and enrollment_status == 'active' and not fee_status and not approval_status:
            flash("No students found matching the current filters.", "alert-info")
            return render_template(
                "ajax/students/pagination.html",
                students_classes={},
                pagination=pagination,
                action=action,
                session=current_session,
                current_term=current_term.value,
                form=form,
                search_query=search_query,
                enrollment_status=enrollment_status,
                fee_status=fee_status,
                approval_status=approval_status,
                message="No students found matching the current filters."
            )

        return render_template(
            "ajax/students/pagination.html",
            students_classes=students_classes,
            current_session=current_session.year,
            current_term=current_term.value,
            pagination=pagination,
            action=action,
            form=form,
            search_query=search_query,
            session=current_session,
            enrollment_status=enrollment_status,
            fee_status=fee_status,
            approval_status=approval_status
        )
    except OperationalError as e:
        app.logger.error(f"Database error searching students: {str(e)}")
        flash("Database error occurred while searching students.", "alert-danger")
        return redirect(url_for("admins.students", action=action))

@admin_bp.route('/search_students_by_class/<string:class_name>/<string:action>', methods=['GET'])
@login_required
def search_students_by_class(class_name, action):
    """Search students within a specific class."""
    search_query = request.args.get('query', '', type=str).strip()
    page = request.args.get('page', 1, type=int)
    class_name = unquote(class_name).strip()
    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        flash("No active session or term found.", "alert-danger")
        return redirect(url_for("admins.select_class", action=action))

    class_record = Classes.query.filter_by(name=class_name).first_or_404()
    form = DeleteForm()
    try:
        students_query = StudentClassHistory.query.filter(
            StudentClassHistory.session_id == current_session.id,
            StudentClassHistory.class_id == class_record.id,
            StudentClassHistory.is_active == True,
            StudentClassHistory.leave_date.is_(None)
        ).join(Student)
        if search_query:
            search_filter = or_(
                func.lower(Student.first_name).contains(search_query.lower()),
                func.lower(Student.last_name).contains(search_query.lower()),
                func.lower(Student.reg_no).contains(search_query.lower()),
            )
            students_query = students_query.filter(search_filter)

        pagination = students_query.order_by(Student.last_name.asc()).paginate(page=page, per_page=5, error_out=False)
        student_histories = pagination.items
        students = [history.student for history in student_histories]

        return render_template(
            "ajax/classes/students_by_class.html",
            students=students,
            session=current_session.year,
            current_session=current_session.year,
            form=form,
            current_term=current_term.value,
            pagination=pagination,
            action=action,
            class_name=class_name,
        )
    except OperationalError as e:
        app.logger.error(f"Database error searching students in class {class_name}: {str(e)}")
        flash("Database error occurred.", "alert-danger")
        return redirect(url_for("admins.students_by_class", class_name=class_name, action=action))

@admin_bp.route("/print_student_message", methods=["GET", "POST"])
@login_required
def print_student_message():
    """Render a page to select multiple students and print their login credentials for active students in the current session and term."""
    if current_user.role != RoleEnum.ADMIN.value:
        flash("Only administrators can access this page.", "alert-danger")
        app.logger.warning(f"Unauthorized access attempt by {current_user.username} to print_student_message")
        return redirect(url_for("main.index"))

    current_session, current_term = Session.get_current_session_and_term(include_term=True)
    if not current_session or not current_term:
        flash("No active session or term is set.", "alert-danger")
        app.logger.error("No current session or term found for print_student_message")
        return redirect(url_for("admins.admin_dashboard"))

    form = ApproveForm()
    try:
        active_students = (
            db.session.query(Student)
            .join(StudentClassHistory, Student.id == StudentClassHistory.student_id)
            .filter(
                StudentClassHistory.session_id == current_session.id,
                StudentClassHistory.is_active == True,
                StudentClassHistory.leave_date.is_(None),
                StudentClassHistory.start_term <= current_term.value,
                (StudentClassHistory.end_term.is_(None) | (StudentClassHistory.end_term >= current_term.value))
            )
            .order_by(Student.last_name, Student.first_name)
            .all()
        )

        if not active_students:
            flash(f"No active students found for {current_term.value} Term, {current_session.year}.", "alert-info")
            return render_template(
                "admin/students/print_student_message.html",
                students=[],
                selected_students=[],
                current_session=current_session.year,
                current_term=current_term.value,
                form=form,
            )

        selected_students = []
        if request.method == "POST":
            student_ids = request.form.getlist("student_ids")  # Get list of selected student IDs
            app.logger.debug(f"Received student_ids: {student_ids}")  # Debug log
            if not student_ids or all(not sid for sid in student_ids):  # Check if empty or all None/empty strings
                flash("No students selected.", "alert-warning")
                app.logger.warning("No valid student IDs received in POST request for print_student_message")
            else:
                # Filter out invalid IDs and limit to 4
                valid_student_ids = [int(sid) for sid in student_ids if sid and sid.isdigit()]
                if not valid_student_ids:
                    flash("Invalid student IDs provided.", "alert-warning")
                    app.logger.warning(f"Invalid student_ids received: {student_ids}")
                else:
                    valid_student_ids = valid_student_ids[:4]
                    selected_students = (
                        Student.query
                        .filter(Student.id.in_(valid_student_ids))
                        .filter(Student.id.in_([s.id for s in active_students]))
                        .all()
                    )
                    if not selected_students:
                        flash("No valid active students selected.", "alert-warning")
                        app.logger.warning(f"No active students found for IDs: {valid_student_ids}")
                    elif len(selected_students) != len(valid_student_ids):
                        flash("Some selected students are not active in the current term/session.", "alert-warning")
                        app.logger.warning(f"Partial match for student IDs: {valid_student_ids}, found: {[s.id for s in selected_students]}")

        return render_template(
            "admin/students/print_student_message.html",
            students=active_students,
            selected_students=selected_students,
            current_session=current_session.year,
            current_term=current_term.value,
            form=form,
        )
    except OperationalError as e:
        app.logger.error(f"Database error fetching active students: {str(e)}")
        flash("A database error occurred. Please try again later.", "alert-danger")
        return redirect(url_for("admins.admin_dashboard"))

@admin_bp.route("/get-student/<int:student_id>", methods=["GET"])
@login_required
def get_student(student_id):
    """AJAX endpoint to fetch student details."""
    if current_user.role != RoleEnum.ADMIN.value:
        return jsonify({"error": "Unauthorized"}), 403

    student = Student.query.get_or_404(student_id)
    try:
        # For security, avoid sending password hashes; use reg_no as default password
        return jsonify({
            "first_name": student.first_name,
            "last_name": student.last_name,
            "reg_no": student.reg_no,
        })
    except Exception as e:
        app.logger.error(f"Error fetching student {student_id}: {str(e)}")
        return jsonify({"error": "Failed to fetch student data"}), 500

# @admin_bp.route('/get-student/<int:student_id>', methods=['GET'])
# @login_required
# def get_student(student_id):
#     """Get student details via AJAX."""
#     try:
#         student = Student.query.get(student_id)
#         if student:
#             return jsonify({
#                 "first_name": student.first_name,
#                 "last_name": student.last_name,
#                 "reg_no": student.reg_no
#             })
#         return jsonify({"error": "Student not found"}), 404
#     except OperationalError as e:
#         app.logger.error(f"Database error fetching student {student_id}: {str(e)}")
#         return jsonify({"error": "Database error occurred"}), 500


