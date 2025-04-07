# teacher/routes.py
import re
from datetime import datetime
from sqlalchemy import or_, case, func, desc
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.sql import text
from urllib.parse import unquote
from sqlalchemy.orm import joinedload
from itertools import groupby
from operator import itemgetter
from flask import (
    render_template, redirect, url_for, flash, request, jsonify, Response, current_app as app,
)
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFError, generate_csrf
from . import teacher_bp
from ..helpers import (
    get_subjects_by_class_name, update_results_helper, save_result, calculate_average,
    calculate_cumulative_average, calculate_results, db, populate_form_with_results,
    generate_excel_broadsheet, prepare_broadsheet_data, group_students_by_class,
    get_teacher_classes, save_class_wide_fields
)
from ..models import (
    Student, User, Subject, Result, Session, StudentClassHistory, RoleEnum, Classes,
    Teacher, TermEnum, class_teacher, AuditLog, class_subject, StudentTermSummary
)
from ..auth.forms import (
    ResultForm, ManageResultsForm, DeleteForm, TeacherForm, EditStudentForm,
    classForm, SubjectForm,
)
import bleach
from marshmallow import Schema, fields, ValidationError, validates_schema
from application import limiter
import pyotp
import qrcode
from io import BytesIO
import base64

# Error Handlers (unchanged)
@teacher_bp.errorhandler(CSRFError)
def handle_csrf_error(e):
    return jsonify({"status": "error", "message": "CSRF token missing or invalid"}), 400

@teacher_bp.before_request
@login_required
def teacher_before_request():
    if current_user.role != RoleEnum.TEACHER.value:
        flash("You are not authorized to access this page.", "alert-danger")
        app.logger.warning(f"Unauthorized access attempt by user {current_user.username}")
        return redirect(url_for("auth.login"))

@teacher_bp.after_request
def add_csrf_token(response):
    response.headers['X-CSRFToken'] = generate_csrf()
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

# Dashboard: Show all assignments across sessions and terms
@teacher_bp.route("/dashboard")
def teacher_dashboard():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    current_session, current_term = Session.get_current_session_and_term(include_term=True)

    # Fetch all assignments for the teacher
    assignments = db.session.query(
        Classes, Session, class_teacher.c.term, class_teacher.c.is_form_teacher
    ).join(class_teacher, Classes.id == class_teacher.c.class_id)\
     .join(Session, Session.id == class_teacher.c.session_id)\
     .filter(class_teacher.c.teacher_id == teacher.id)\
     .order_by(Session.year.desc(), class_teacher.c.term)\
     .all()

    assigned_subjects = teacher.subjects.all()
    current_classes = get_teacher_classes(teacher.id, current_session.id, current_term.value)

    return render_template(
        "teacher/dashboard.html",
        teacher=teacher,
        assignments=assignments,
        assigned_subjects=assigned_subjects,
        current_classes=current_classes,
        current_session=current_session.id if current_session else "Not Set",
        current_session_year=current_session.year if current_session else "Not Set",
        current_term=current_term.value if current_term else "Not Set",
        session_id=current_session.id if current_session else "Not Set",
        term=current_term.value if current_term else "Not Set"
    )

# View All Classes: Detailed view of assignments
@teacher_bp.route("/classes")
def view_classes():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    assignments = db.session.query(
        Classes, Session, class_teacher.c.term, class_teacher.c.is_form_teacher
    ).join(class_teacher, Classes.id == class_teacher.c.class_id)\
     .join(Session, Session.id == class_teacher.c.session_id)\
     .filter(class_teacher.c.teacher_id == teacher.id)\
     .order_by(Session.year.desc(), class_teacher.c.term)\
     .all()

    return render_template(
        "teacher/view_classes.html",
        teacher=teacher,
        assignments=assignments,
    )

# View Subjects (unchanged)
@teacher_bp.route("/subjects")
def view_subjects():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    assigned_subjects = teacher.subjects.all()
    return render_template(
        "teacher/view_subjects.html",
        teacher=teacher,
        assigned_subjects=assigned_subjects,
    )

@teacher_bp.route("/manage_students_select", methods=["GET", "POST"])
def manage_students_select():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    form = classForm()

    # Get distinct classes assigned to the teacher, ordered by hierarchy
    assigned_classes = db.session.query(Classes)\
        .join(class_teacher, Classes.id == class_teacher.c.class_id)\
        .filter(class_teacher.c.teacher_id == teacher.id)\
        .distinct(Classes.id)\
        .order_by(Classes.hierarchy.asc()).all()
    form.class_name.choices = [(cls.id, cls.name) for cls in assigned_classes]

    # Get all sessions and terms the teacher was assigned to
    assignments = db.session.query(Session, class_teacher.c.term)\
        .join(class_teacher, Session.id == class_teacher.c.session_id)\
        .filter(class_teacher.c.teacher_id == teacher.id)\
        .distinct().all()
    sessions = sorted(set(session for session, _ in assignments), key=lambda s: s.year, reverse=True)
    terms = sorted(set(term for _, term in assignments))

    if form.validate_on_submit():
        class_id = form.class_name.data
        session_id = request.form.get("session_id")
        term = request.form.get("term")

        # Verify the assignment exists for this combination
        assignment = db.session.query(class_teacher).filter_by(
            class_id=class_id, teacher_id=teacher.id, session_id=session_id, term=term
        ).first()
        if not assignment:
            flash("You were not assigned to this class for the selected session and term.", "alert-danger")
            return redirect(url_for("teachers.manage_students_select"))

        return redirect(url_for("teachers.manage_students", class_id=class_id, session_id=session_id, term=term))

    return render_template(
        "teacher/select_class.html",
        form=form,
        teacher=teacher,
        sessions=sessions,
        terms=terms,
        action="Manage Students",
    )

# Manage Students: Full CRUD access if form teacher
@teacher_bp.route("/students/<int:class_id>/<int:session_id>/<term>", methods=["GET", "POST"])
def manage_students(class_id, session_id, term):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    cls = Classes.query.get_or_404(class_id)
    session_obj = Session.query.get_or_404(session_id)

    assignment = db.session.query(class_teacher).filter_by(
        class_id=class_id, teacher_id=teacher.id, session_id=session_id, term=term
    ).first()
    if not assignment:
        flash("You are not assigned to this class for this session and term.", "alert-danger")
        return redirect(url_for("teachers.teacher_dashboard"))

    is_form_teacher = assignment.is_form_teacher
    form = EditStudentForm()
    form.class_id.choices = [(c.id, c.name) for c in Classes.query.order_by(Classes.hierarchy).all()]

    if form.validate_on_submit() and is_form_teacher:
        student_id = request.form.get("student_id")
        student = Student.query.get_or_404(student_id)
        try:
            student.first_name = form.first_name.data
            student.last_name = form.last_name.data
            student.middle_name = form.middle_name.data
            student.gender = form.gender.data
            history = StudentClassHistory.query.filter_by(
                student_id=student.id, session_id=session_obj.id, is_active=True
            ).first()
            if history:
                history.class_id = form.class_id.data
            db.session.commit()
            flash("Student details updated successfully.", "alert-success")
        except OperationalError as e:
            db.session.rollback()
            flash("Database error occurred.", "alert-danger")
            app.logger.error(f"Database error occurred. {str(e.messages)}")

    student_class_histories = (
        StudentClassHistory.query.filter(
            StudentClassHistory.session_id == session_id,
            StudentClassHistory.class_id == class_id,
            StudentClassHistory.is_active == True,
            StudentClassHistory.leave_date.is_(None)
        ).options(joinedload(StudentClassHistory.student)).all()
    )

    students = [h.student for h in student_class_histories]

    return render_template(
        "teacher/manage_students.html",
        teacher=teacher,
        cls=cls,
        students=students,
        session=session_obj,
        term=term,
        is_form_teacher=is_form_teacher,
        form=form,
    )

# View Class Details
@teacher_bp.route("/classes/<int:class_id>/<int:session_id>/<term>")
def view_class(class_id, session_id, term):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    cls = Classes.query.get_or_404(class_id)
    session_obj = Session.query.get_or_404(session_id)

    assignment = db.session.query(class_teacher).filter_by(
        class_id=class_id, teacher_id=teacher.id, session_id=session_id, term=term
    ).first()
    if not assignment:
        flash("You are not assigned to this class for this session and term.", "alert-danger")
        return redirect(url_for("teachers.teacher_dashboard"))

    is_form_teacher = assignment.is_form_teacher
    # students = [h.student for h in StudentClassHistory.query.filter_by(
    #     session_id=session_id, class_id=class_id
    # ).join(Student).order_by(Student.last_name.asc()).all()]

    student_class_histories = (
        StudentClassHistory.query.filter(
            StudentClassHistory.session_id == session_id,
            StudentClassHistory.class_id == class_id,
            StudentClassHistory.is_active == True,
            StudentClassHistory.leave_date.is_(None)
        ).options(joinedload(StudentClassHistory.student)).all()
    )

    students = [h.student for h in student_class_histories]

    subjects = get_subjects_by_class_name(cls.id) if is_form_teacher else [
        s for s in get_subjects_by_class_name(cls.id) if s in teacher.subjects
    ]

    return render_template(
        "teacher/class_view.html",
        teacher=teacher,
        cls=cls,
        students=students,
        subjects=subjects,
        session=session_obj,
        term=term,
        is_form_teacher=is_form_teacher,
    )

# Select Class for Results
@teacher_bp.route("/manage_results_select", methods=["GET", "POST"])
def manage_results_select():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    form = classForm()

    # Get distinct classes assigned to the teacher, ordered by hierarchy
    assigned_classes = db.session.query(Classes)\
        .join(class_teacher, Classes.id == class_teacher.c.class_id)\
        .filter(class_teacher.c.teacher_id == teacher.id)\
        .distinct(Classes.id)\
        .order_by(Classes.hierarchy.asc()).all()
    form.class_name.choices = [(cls.id, cls.name) for cls in assigned_classes]

    # Get all sessions and terms the teacher was assigned to
    assignments = db.session.query(Session, class_teacher.c.term)\
        .join(class_teacher, Session.id == class_teacher.c.session_id)\
        .filter(class_teacher.c.teacher_id == teacher.id)\
        .distinct().all()
    sessions = sorted(set(session for session, _ in assignments), key=lambda s: s.year, reverse=True)
    terms = sorted(set(term for _, term in assignments))

    if form.validate_on_submit():
        class_id = form.class_name.data
        session_id = request.form.get("session_id")
        term = request.form.get("term")

        # Verify the assignment exists for this combination
        assignment = db.session.query(class_teacher).filter_by(
            class_id=class_id, teacher_id=teacher.id, session_id=session_id, term=term
        ).first()
        if not assignment:
            flash("You were not assigned to this class for the selected session and term.", "alert-danger")
            return redirect(url_for("teachers.manage_results_select"))

        return redirect(url_for("teachers.view_class", class_id=class_id, session_id=session_id, term=term))

    return render_template(
        "teacher/select_class.html",
        form=form,
        teacher=teacher,
        sessions=sessions,
        terms=terms,
        action="Manage Results",
    )

@teacher_bp.route("/manage_results/<int:class_id>/<int:student_id>/<int:session_id>/<term>", methods=["GET"])
def manage_results(class_id, student_id, session_id, term):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    cls = Classes.query.get_or_404(class_id)
    student = Student.query.get_or_404(student_id)
    session_obj = Session.query.get_or_404(session_id)

    assignment = db.session.query(class_teacher).filter_by(
        class_id=class_id, teacher_id=teacher.id, session_id=session_id, term=term
    ).first()
    if not assignment:
        flash("You are not assigned to this class for this session and term.", "alert-danger")
        return redirect(url_for("teachers.teacher_dashboard"))

    is_form_teacher = assignment.is_form_teacher
    enrollment = StudentClassHistory.query.filter_by(
        student_id=student_id, session_id=session_id, class_id=class_id
    ).first()
    if not enrollment:
        flash("Student not enrolled in this class for this session.", "alert-danger")
        return redirect(url_for("teachers.view_class", class_id=class_id, session_id=session_id, term=term))

    subjects = get_subjects_by_class_name(class_id) if is_form_teacher else [
        s for s in get_subjects_by_class_name(class_id) if s in teacher.subjects
    ]
    result_form = ResultForm(term=term, session=session_id)
    form = ManageResultsForm()  # Unbound form for display

    results = Result.query.filter_by(student_id=student_id, term=term, session_id=session_id).all()
    results_dict = {result.subject_id: result for result in results}
    populate_form_with_results(form, subjects, results_dict)

    # Fetch term summary for aggregates
    term_summary = StudentTermSummary.query.filter_by(
        student_id=student_id,
        term=term,
        session_id=session_id,
        class_id=class_id
    ).first()

    details = term_summary.__dict__ if term_summary else {}
    return render_template(
        "teacher/manage_results.html",
        teacher=teacher,
        cls=cls,
        student=student,
        subjects=subjects,
        subject_results=zip(subjects, form.subjects),
        form=form,
        result_form=result_form,
        session=session_obj,
        is_form_teacher=is_form_teacher,
        results_dict=results_dict,
        results=results,
        school_name=app.config.get("SCHOOL_NAME", "Aunty Anne's International School"),
        **details,
    )

@teacher_bp.route("/update_results_helper/<int:class_id>/<int:student_id>/<int:session_id>/<term>", methods=["POST"])
def update_results(class_id, student_id, session_id, term):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    cls = Classes.query.get_or_404(class_id)
    student = Student.query.get_or_404(student_id)
    session_obj = Session.query.get_or_404(session_id)

    assignment = db.session.query(class_teacher).filter_by(
        class_id=class_id, teacher_id=teacher.id, session_id=session_id, term=term
    ).first()
    if not assignment:
        flash("You are not assigned to this class for this session and term.", "alert-danger")
        return redirect(url_for("teachers.teacher_dashboard"))

    is_form_teacher = assignment.is_form_teacher
    if not is_form_teacher:
        flash("Only form teachers can update results.", "alert-danger")
        return redirect(url_for("teachers.manage_results", class_id=class_id, student_id=student_id, session_id=session_id, term=term))

    enrollment = StudentClassHistory.query.filter_by(
        student_id=student_id, session_id=session_id, class_id=class_id
    ).first()
    if not enrollment:
        flash("Student not enrolled in this class for this session.", "alert-danger")
        return redirect(url_for("teachers.view_class", class_id=class_id, session_id=session_id, term=term))

    result_form = ResultForm(term=term, session=session_id)
    form = ManageResultsForm()  # Bind form to submitted data

    if form.validate_on_submit():
        try:
            app.logger.debug(f"Submitted form data: {form.data}")
            update_results_helper(
                student=student, term=term, session_id=session_id, form=form,
                result_form=result_form, class_id=class_id
            )
            db.session.commit()
            flash("Results updated successfully.", "alert-success")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error updating results: {str(e)}")
            flash("Database error occurred.", "alert-danger")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Unexpected error updating results: {str(e)}")
            flash("An unexpected error occurred.", "alert-danger")
    else:
        app.logger.debug(f"Form validation failed: {form.errors}")
        flash(f"Form validation failed: {form.errors}", "alert-danger")

    return redirect(url_for("teachers.manage_results", class_id=class_id, student_id=student_id, session_id=session_id, term=term))

# Delete Result (new route)
@teacher_bp.route("/delete_result/<int:class_id>/<int:student_id>/<int:subject_id>/<int:session_id>/<term>", methods=["POST"])
def delete_result(class_id, student_id, subject_id, session_id, term):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    assignment = db.session.query(class_teacher).filter_by(
        class_id=class_id, teacher_id=teacher.id, session_id=session_id, term=term
    ).first()
    if not assignment or not assignment.is_form_teacher:
        flash("You are not authorized to delete results for this class.", "alert-danger")
        return redirect(url_for("teachers.teacher_dashboard"))

    result = Result.query.filter_by(
        student_id=student_id, subject_id=subject_id, session_id=session_id, term=term
    ).first()
    if result:
        try:
            db.session.delete(result)
            db.session.commit()
            flash("Result deleted successfully.", "alert-success")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error deleting result: {str(e)}")
            flash("Database error occurred.", "alert-danger")
    return redirect(url_for("teachers.manage_results", class_id=class_id, student_id=student_id, session_id=session_id, term=term))


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


@teacher_bp.route("/update_result_field/<int:session_id>/<term>", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def update_result_field(session_id, term):
    """Update a specific result field via AJAX."""
    try:
        data = ResultUpdateSchema().load(request.get_json())
        data['next_term_begins'] = bleach.clean(data.get('next_term_begins', '')) if data.get('next_term_begins') else None
        data['position'] = bleach.clean(data.get('position', '')) if data.get('position') else None
        data['date_issued'] = bleach.clean(data.get('date_issued', '')) if data.get('date_issued') else None

        # Save the result and get the updated object
        result = save_result(
            student_id=data["student_id"],
            subject_id=data["subject_id"],
            term=term,
            session_id=session_id,
            data=data,
            class_id=data["class_id"]
        )
        db.session.add(AuditLog(user_id=current_user.id, action=f"Updated result for student {data['student_id']} in subject {data['subject_id']}"))
        db.session.commit()
        app.logger.info(f"Result updated for student {data['student_id']} in subject {data['subject_id']} by user {current_user.username}")

        # Fetch term summary for aggregates
        term_summary = StudentTermSummary.query.filter_by(
            student_id=data["student_id"],
            term=term,
            session_id=session_id,
            class_id=data["class_id"]
        ).first()

        # Return updated fields including remarks
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
        app.logger.error(f"Validation error in update_result_field: {str(e.messages)}")
        return jsonify({"status": "error", "message": str(e.messages)}), 400
    except ValueError as e:
        db.session.rollback()
        app.logger.error(f"Invalid data in update_result_field: {str(e)}")
        return jsonify({"status": "error", "message": "Invalid data provided."}), 400
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error in update_result_field: {str(e)}")
        return jsonify({"status": "error", "message": "Database error occurred."}), 500
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error in update_result_field: {str(e)}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@teacher_bp.route("/broadsheet_select", methods=["GET", "POST"])
def broadsheet_select():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    form = classForm()

    # Get distinct classes assigned to the teacher, ordered by hierarchy
    assigned_classes = db.session.query(Classes)\
        .join(class_teacher, Classes.id == class_teacher.c.class_id)\
        .filter(class_teacher.c.teacher_id == teacher.id)\
        .distinct(Classes.id)\
        .order_by(Classes.hierarchy.asc()).all()
    form.class_name.choices = [(cls.id, cls.name) for cls in assigned_classes]

    # Get all sessions and terms the teacher was assigned to
    assignments = db.session.query(Session, class_teacher.c.term)\
        .join(class_teacher, Session.id == class_teacher.c.session_id)\
        .filter(class_teacher.c.teacher_id == teacher.id)\
        .distinct().all()
    sessions = sorted(set(session for session, _ in assignments), key=lambda s: s.year, reverse=True)
    terms = sorted(set(term for _, term in assignments))

    if form.validate_on_submit():
        class_id = form.class_name.data
        session_id = request.form.get("session_id")
        term = request.form.get("term")

        # Verify the assignment exists for this combination
        assignment = db.session.query(class_teacher).filter_by(
            class_id=class_id, teacher_id=teacher.id, session_id=session_id, term=term
        ).first()
        if not assignment:
            flash("You were not assigned to this class for the selected session and term.", "alert-danger")
            return redirect(url_for("teachers.broadsheet_select"))

        return redirect(url_for("teachers.view_class", class_id=class_id, session_id=session_id, term=term))

    return render_template(
        "teacher/select_class.html",
        form=form,
        teacher=teacher,
        sessions=sessions,
        terms=terms,
        action="Manage Broadsheet",
    )

# Broadsheet
@teacher_bp.route("/broadsheet/<int:class_id>/<int:session_id>/<term>")
def broadsheet(class_id, session_id, term):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    cls = Classes.query.get_or_404(class_id)
    session_obj = Session.query.get_or_404(session_id)
    form = classForm()

    assignment = db.session.query(class_teacher).filter_by(
        class_id=class_id, teacher_id=teacher.id, session_id=session_id, term=term
    ).first()
    if not assignment:
        flash("You are not assigned to this class for this session and term.", "alert-danger")
        return redirect(url_for("teachers.teacher_dashboard"))

    is_form_teacher = assignment.is_form_teacher
    student_class_histories = (
        StudentClassHistory.query.filter(
            StudentClassHistory.session_id == session_id,
            StudentClassHistory.class_id == class_id,
            StudentClassHistory.is_active == True,
            StudentClassHistory.leave_date.is_(None)
        ).options(joinedload(StudentClassHistory.student)).all()
    )

    students = [h.student for h in student_class_histories]

    # students = [h.student for h in StudentClassHistory.query.filter_by(
    #     session_id=session_id, class_id=class_id
    # ).join(Student).order_by(Student.last_name.asc()).all()]
    subjects = get_subjects_by_class_name(cls.id) if is_form_teacher else [
        s for s in get_subjects_by_class_name(cls.id) if s in teacher.subjects
    ]

    if not students or not subjects:
        flash("No students or subjects available.", "alert-info")
        return render_template("teacher/broadsheet.html", cls=cls, students=[], subjects=[], broadsheet_data=[], subject_averages={})

    broadsheet_data, subject_averages = prepare_broadsheet_data(
        students=students, subjects=subjects, term=term, session_year=session_obj.year, session_id=session_id, class_id=class_id
    )
    return render_template(
        "teacher/broadsheet.html",
        cls=cls,
        students=students,
        subjects=subjects,
        broadsheet_data=broadsheet_data,
        subject_averages=subject_averages,
        session=session_obj,
        term=term,
        form=form,
    )

@teacher_bp.route("/update_broadsheet/<int:class_id>/<int:session_id>/<term>", methods=["POST"])
@login_required
def update_broadsheet(class_id, session_id, term):
    """Update broadsheet data for a class."""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    cls = Classes.query.get_or_404(class_id)
    session_obj = Session.query.get_or_404(session_id)
    form = classForm()

    assignment = db.session.query(class_teacher).filter_by(
        class_id=cls.id, teacher_id=teacher.id, session_id=session_obj.id, term=term
    ).first()
    if not assignment:
        flash("You are not assigned to this class for this session and term.", "alert-danger")
        return redirect(url_for("teachers.teacher_dashboard"))

    # is_form_teacher = assignment.is_form_teacher
    # student_class_histories = (
    #     StudentClassHistory.query.filter(
    #         StudentClassHistory.session_id == session_id,
    #         StudentClassHistory.class_id == class_id,
    #         StudentClassHistory.is_active == True,
    #         StudentClassHistory.leave_date.is_(None)
    #     ).options(joinedload(StudentClassHistory.student)).all()
    # )

    # students = [h.student for h in student_class_histories]

    # students = [h.student for h in StudentClassHistory.query.filter_by(
    #     session_id=session_id, class_id=class_id
    # ).join(Student).order_by(Student.last_name.asc()).all()]

    # subjects = get_subjects_by_class_name(cls.id) if is_form_teacher else [
    #     s for s in get_subjects_by_class_name(cls.id) if s in teacher.subjects
    # ]

    results_data = {}
    for key, value in request.form.items():
        if key.startswith('results['):
            match = re.match(r'results\[(\d+)\]\[(\d+)\]\[(\w+)\]', key)
            if match:
                student_id, subject_id, field = match.groups()
                student_id, subject_id = int(student_id), int(subject_id)
                value = None if not value.strip() else int(value)
                results_data.setdefault(student_id, {}).setdefault(subject_id, {})[field] = value

    if not results_data:
        flash("No data submitted for update.", "alert-danger")
        return redirect(url_for('teachers.broadsheet', form=form, class_id=class_id, session_id=session_id, term=term))

    try:
        for student_id, subject_scores in results_data.items():
            for subject_id, scores in subject_scores.items():
                data = {
                    "class_assessment": scores.get("class_assessment"),
                    "summative_test": scores.get("summative_test"),
                    "exam": scores.get("exam")
                }
                save_result(
                    student_id=student_id,
                    subject_id=subject_id,
                    term=term,
                    data=data,
                    class_id=class_id,
                    session_id=session_id
                )
        db.session.commit()
        flash("Broadsheet updated successfully.", "alert-success")
    except ValueError as e:
        db.session.rollback()
        app.logger.error(f"Invalid data updating broadsheet for {cls.name}: {str(e)}")
        flash("Invalid data submitted.", "alert-danger")
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error updating broadsheet for {cls.name}: {str(e)}")
        flash("Database error occurred.", "alert-danger")
    return redirect(url_for('teachers.broadsheet', class_id=class_id, session_id=session_id, term=term))

@teacher_bp.route("/update_broadsheet_field/<int:session_id>/<term>", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def update_broadsheet_field(session_id, term):
    """Update a specific broadsheet field via AJAX for teachers."""
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()

    try:
        data = ResultUpdateSchema().load(request.get_json())
        class_id = data["class_id"]

        # Verify teacher is assigned to this class for the session and term
        assignment = db.session.query(class_teacher).filter_by(
            class_id=class_id, teacher_id=teacher.id, session_id=session_id, term=term
        ).first()
        if not assignment:
            return jsonify({"status": "error", "message": "You are not assigned to this class for this session and term."}), 403

        position = data.get('position')
        data['position'] = bleach.clean(position) if position is not None else None
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

        # Save the result and get the updated object
        result = save_result(
            student_id=student_id,
            subject_id=subject_id if subject_id else None,
            term=term,
            session_id=session_id,
            data=data,
            class_id=class_id
        )
        db.session.add(AuditLog(user_id=current_user.id, action=f"Updated broadsheet field for student {student_id} {'in subject ' + str(subject_id) if subject_id else 'position'}"))
        db.session.commit()
        # app.logger.info(f"Broadsheet field updated for student {data['student_id']} in subject {data['subject_id']} by teacher {teacher.id}")

        # Fetch term summary for aggregates
        term_summary = StudentTermSummary.query.filter_by(
            student_id=data["student_id"],
            term=term,
            session_id=session_id,
            class_id=class_id
        ).first()

        response = {
            "status": "success",
            "message": "Result saved successfully.",
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
        app.logger.error(f"Validation error in update_broadsheet_field: {str(e.messages)}")
        return jsonify({"status": "error", "message": str(e.messages)}), 400
    except ValueError as e:
        db.session.rollback()
        app.logger.error(f"Value error in update_broadsheet_field: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except OperationalError as e:
        db.session.rollback()
        app.logger.error(f"Database error in update_broadsheet_field: {str(e)}")
        return jsonify({"status": "error", "message": "Database error occurred."}), 500
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error in update_broadsheet_field: {str(e)}, Data: {request.get_json()}")
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}), 500

class ClassWideUpdateSchema(Schema):
    class_id = fields.Integer(required=True)
    next_term_begins = fields.Str(allow_none=True, load_default=None)
    date_issued = fields.Str(allow_none=True, load_default=None)

    # @validates_schema
    # def validate_at_least_one_field(self, data, **kwargs):
    #     if data.get("next_term_begins") is None and data.get("date_issued") is None:
    #         raise ValidationError("At least one of next_term_begins or date_issued must be provided.")


@teacher_bp.route("/update_broadsheet_class_fields/<int:session_id>/<term>", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def update_broadsheet_class_fields(session_id, term):
    """Update class-wide fields (next_term_begins, date_issued) via AJAX."""

    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    try:
        data = ClassWideUpdateSchema().load(request.get_json())
        class_id = data["class_id"]

        # Verify teacher is assigned to this class for the session and term
        assignment = db.session.query(class_teacher).filter_by(
            class_id=class_id, teacher_id=teacher.id, session_id=session_id, term=term
        ).first()
        if not assignment:
            return jsonify({"status": "error", "message": "You are not assigned to this class for this session and term."}), 403

        next_term_begins = data.get('next_term_begins')
        date_issued = data.get('date_issued')
        data['next_term_begins'] = bleach.clean(next_term_begins) if next_term_begins is not None else None
        data['date_issued'] = bleach.clean(date_issued) if date_issued is not None else None

        updated_count = save_class_wide_fields(
            class_id=class_id,
            session_id=session_id,
            term=term,
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

# Profile (unchanged)
@teacher_bp.route("/profile", methods=["GET", "POST"])
def profile():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first_or_404()
    form = TeacherForm(obj=teacher)

    if form.validate_on_submit():
        try:
            form.populate_obj(teacher)
            db.session.commit()
            flash("Profile updated successfully.", "alert-success")
        except OperationalError as e:
            db.session.rollback()
            app.logger.error(f"Database error updating profile: {str(e)}")
            flash("Database error occurred.", "alert-danger")

    return render_template("teacher/profile.html", teacher=teacher, form=form)

