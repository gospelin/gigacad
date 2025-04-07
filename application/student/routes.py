# student/routes.py
from . import student_bp
import os
from flask import (
    render_template,
    redirect,
    url_for,
    session,
    flash,
    request,
    jsonify,
    current_app as app,
    make_response,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy.exc import OperationalError
from datetime import datetime
from sqlalchemy import func, desc
from flask_wtf.csrf import CSRFError, generate_csrf
from ..models import Student, Result, Session, Subject, FeePayment, StudentTermSummary, StudentClassHistory, RoleEnum, Classes, TermEnum
from ..auth.forms import ResultForm
from ..helpers import (
    db,
    # get_last_term,
    # calculate_average,
    calculate_grade,
    # calculate_cumulative_average,
    generate_excel_broadsheet,
    prepare_broadsheet_data,
)
from weasyprint import HTML

@student_bp.route("/dashboard")
@login_required
def student_portal():
    try:
        if current_user.role != RoleEnum.STUDENT.value:
            flash("You are not authorized to access the student portal.", "alert-danger")
            app.logger.warning(f"Unauthorized access attempt by user {current_user.username}")
            return redirect(url_for("auth.login"))

        student = Student.query.filter_by(user_id=current_user.id).first()
        if not student:
            flash("Student profile not found.", "alert-danger")
            return redirect(url_for("auth.login"))

        # Fetch the latest result to determine current term and session
        latest_result = Result.query.filter_by(student_id=student.id).order_by(desc(Result.created_at)).first()
        if latest_result:
            current_term = latest_result.term
            current_session = Session.query.get(latest_result.session_id)
            if not current_session:
                flash("Session for latest result not found.", "alert-danger")
                return redirect(url_for("auth.login"))
        else:
            # Fallback to global current session and term if no results exist
            current_session, current_term_enum = Session.get_current_session_and_term(include_term=True)
            if not current_session or not current_term_enum:
                flash("No active session or term set and no results found.", "alert-danger")
                return redirect(url_for("auth.login"))
            current_term = current_term_enum.value

        # Aggregated results
        results_summary = db.session.query(
            func.avg(Result.total).label('average'),
            func.count(Result.subject_id.distinct()).label('total_subjects'),
            func.max(Result.total).label('max_score')
        ).filter(
            Result.student_id == student.id,
            Result.term == current_term,
            Result.session_id == current_session.id
        ).one_or_none()

        average = float(results_summary.average or 0)
        total_subjects = results_summary.total_subjects or 0
        best_grade = calculate_grade(results_summary.max_score) if results_summary.max_score else "N/A"

        # Fetch subjects offered this term (still includes all subjects with results, even if total is NULL)
        subjects_offered = db.session.query(Subject).join(Result).filter(
            Result.student_id == student.id,
            Result.term == current_term,
            Result.session_id == current_session.id
        ).distinct().all()
        subject_names = [subject.name for subject in subjects_offered]

        # Historical performance (for the current session)
        historical_results = db.session.query(
            Result.term,
            func.avg(Result.total).label('term_average')
        ).filter(
            Result.student_id == student.id,
            Result.session_id == current_session.id,
            Result.total.isnot(None)  # Exclude NULL totals for consistency
        ).group_by(Result.term).all()
        performance_trend = {term: float(avg) for term, avg in historical_results}

        # Peer comparison
        current_enrollment = student.get_current_enrollment()
        if current_enrollment:
            class_average = db.session.query(
                func.avg(Result.total)
            ).join(
                Classes,
                Result.class_id == Classes.id
            ).join(
                StudentTermSummary,
                StudentTermSummary.class_id == Classes.id
            ).filter(
                StudentTermSummary.class_id == current_enrollment.class_id,
                Result.term == current_term,
                Result.session_id == current_session.id
            ).scalar() or 0

            rank_query = db.session.query(
                Student.id,
                func.avg(Result.total).label('avg_score')
            ).join(
                Result,
                Student.id == Result.student_id
            ).join(
                Classes,
                Result.class_id == Classes.id
            ).join(
                StudentTermSummary,
                StudentTermSummary.class_id == Classes.id
            ).filter(
                Result.session_id == current_session.id,
                Result.term == current_term,
                StudentTermSummary.class_id == current_enrollment.class_id
            ).group_by(Student.id).order_by(func.avg(Result.total).desc()).all()
            student_rank = next((i + 1 for i, (sid, _) in enumerate(rank_query) if sid == student.id), None)
            total_students = len(rank_query)
        else:
            class_average = 0
            student_rank = None
            total_students = 0

        # Subject scores for chart - Filter out subjects with no results
        subject_scores = db.session.query(
            Subject.name,
            func.avg(Result.total).label('avg_score')
        ).join(Result).filter(
            Result.student_id == student.id,
            Result.term == current_term,
            Result.session_id == current_session.id,
            Result.total.isnot(None)  # Only include subjects with non-NULL totals
        ).group_by(Subject.name).having(
            func.avg(Result.total).isnot(None)  # Ensure average exists
        ).all()
        subject_names_chart = [name for name, _ in subject_scores]
        subject_avg_scores = [float(score) for _, score in subject_scores]  # No need for 'or 0' since None is filtered

        return render_template(
            "student/student_portal.html",
            student=student,
            average=average,
            total_subjects=total_subjects,
            best_grade=best_grade,
            subjects_offered=subject_names,
            performance_trend=performance_trend,
            subject_names=subject_names_chart,
            subject_scores=subject_avg_scores,
            class_average=class_average,
            student_rank=student_rank,
            total_students=total_students,
            current_term=current_term,
            current_session=current_session.year
        )
    except OperationalError as e:
        app.logger.error(f"Database error in student portal for user {current_user.id}: {str(e)}")
        flash("Database error occurred. Please try again later.", "alert-danger")
        return redirect(url_for("auth.login"))


@student_bp.route("/select_results/<int:student_id>", methods=["GET", "POST"])
@login_required
def select_results(student_id):
    try:
        student = Student.query.get_or_404(student_id)
        if current_user.id != student.user_id:
            flash("You are not authorized to access this student’s results.", "alert-danger")
            return redirect(url_for("main.index"))

        form = ResultForm()
        sessions = Session.query.all()
        form.session.choices = [(s.id, s.year) for s in sessions]  # Use session_id as value, year as label
        form.term.choices = [(t.value, t.value) for t in TermEnum]

        if form.validate_on_submit():
            term = form.term.data
            session_id = form.session.data  # Now an ID
            session_obj = Session.query.get_or_404(session_id)
            return redirect(url_for("students.view_results", student_id=student.id, term=term, session_id=session_obj.id))

        return render_template("student/select_results.html", student=student, form=form)
    except OperationalError as e:
        app.logger.error(f"Database error in select_results for student_id {student_id}: {str(e)}")
        flash("Database error occurred. Please try again.", "alert-danger")
        return redirect(url_for("main.index"))


@student_bp.route("/view_results/<int:student_id>", methods=["GET"])
@login_required
def view_results(student_id):
    try:
        student = Student.query.get_or_404(student_id)
        if current_user.id != student.user_id:
            flash("You are not authorized to view these results.", "alert-danger")
            app.logger.warning(f"Unauthorized results access by {current_user.username} for student_id {student_id}")
            return redirect(url_for("main.index"))

        # Get term and session_id from query parameters
        term = request.args.get("term")
        session_id = request.args.get("session_id", type=int)

        # Redirect to select_results if term or session_id is missing or invalid
        if not term or not session_id or term not in [t.value for t in TermEnum]:
            flash("Please select a term and session to view results.", "alert-info")
            return redirect(url_for("students.select_results", student_id=student.id))

        session_obj = Session.query.get_or_404(session_id)

        # Check fee payment status for students (admins bypass this)
        if current_user.role != RoleEnum.ADMIN.value:
            fee_payment = FeePayment.query.filter_by(
                student_id=student.id,
                session_id=session_id,
                term=term
            ).first()
            if not fee_payment or not fee_payment.has_paid_fee:
                flash(f"You must pay your fees for {term} Term, {session_obj.year} to view your results.", "alert-warning")
                app.logger.info(f"Student {student_id} denied result access due to unpaid fees for {term}, {session_obj.year}")
                return redirect(url_for("students.student_portal"))

        # Fetch class name for the session
        class_name = student.get_class_by_session(session_obj.year)
        if not class_name:
            flash(f"{student.first_name} {student.last_name} is not in any class as at {session_obj.year}", "alert-info")
            return redirect(url_for("students.select_results", student_id=student.id))

        # Fetch results for the selected term and session
        results = Result.query.filter_by(
            student_id=student.id,
            term=term,
            session_id=session_obj.id
        ).all()

        if not results:
            flash(f"No results found for {term} in {session_obj.year}", "alert-info")
            return redirect(url_for("students.select_results", student_id=student.id))

        # Calculate grand_total from results
        grand_total = {
            "class_assessment": sum(result.class_assessment or 0 for result in results),
            "summative_test": sum(result.summative_test or 0 for result in results),
            "exam": sum(result.exam or 0 for result in results),
            "total": sum(result.total or 0 for result in results),
        }

        # Fetch term summary for aggregates
        term_summary = StudentTermSummary.query.filter_by(
            student_id=student.id,
            term=term,
            session_id=session_obj.id
        ).first()

        # Extract summary data, defaulting to calculated values if not in summary
        average = term_summary.term_average if term_summary else (grand_total["total"] / len(results) if results else 0)
        cumulative_average = term_summary.cumulative_average if term_summary else None
        last_term_average = term_summary.last_term_average if term_summary else None
        subjects_offered = term_summary.subjects_offered if term_summary else len(results)
        position = term_summary.position if term_summary else None
        principal_remark = term_summary.principal_remark if term_summary else None
        teacher_remark = term_summary.teacher_remark if term_summary else None
        next_term_begins = term_summary.next_term_begins if term_summary else None
        date_issued = term_summary.date_issued if term_summary else None
        date_printed = datetime.now().strftime("%dth %B, %Y")

        # Log successful access
        app.logger.info(f"Results viewed for student_id: {student_id}, term: {term}, session_id: {session_id}")
        return render_template(
            "student/view_results.html",
            title=f"{student.first_name}_{student.last_name}_{term}_{session_obj.year}_Result",
            student=student,
            results=results,
            term=term,
            session_id=session_obj.id,
            session_year=session_obj.year,
            grand_total=grand_total,
            average=average,
            cumulative_average=cumulative_average,
            last_term_average=last_term_average,
            subjects_offered=subjects_offered,
            position=position,
            principal_remark=principal_remark,
            teacher_remark=teacher_remark,
            next_term_begins=next_term_begins,
            date_issued=date_issued,
            date_printed=date_printed,
            class_name=class_name,
            school_name=app.config.get("SCHOOL_NAME", "Aunty Anne's Int'l School"),
        )
    except OperationalError as e:
        app.logger.error(f"Database error viewing results for student_id {student_id}: {str(e)}")
        flash("Database error occurred. Please try again.", "alert-danger")
        return redirect(url_for("students.select_results", student_id=student_id))

@student_bp.route("/download_results_pdf/<int:student_id>", methods=["GET", "POST"])
@login_required
def download_results_pdf(student_id):
    try:
        student = Student.query.get_or_404(student_id)
        if current_user.id != student.user_id and current_user.role != RoleEnum.ADMIN.value:
            flash("You are not authorized to download these results.", "alert-danger")
            app.logger.warning(f"Unauthorized PDF download attempt by {current_user.username} for student_id {student_id}")
            return redirect(url_for("main.index"))

        term = request.args.get("term")
        session_id = request.args.get("session_id")  # Now an ID
        session_obj = Session.query.get_or_404(session_id)

        if not term or not session_id or term not in [t.value for t in TermEnum]:
            flash("Invalid term or session specified.", "alert-danger")
            return redirect(url_for("students.select_results", student_id=student.id))

        # Check fee payment status for students (admins bypass this)
        if current_user.role != RoleEnum.ADMIN.value:
            fee_payment = FeePayment.query.filter_by(
                student_id=student.id,
                session_id=session_id,
                term=term
            ).first()
            if not fee_payment or not fee_payment.has_paid_fee:
                flash(f"You must pay your fees for {term} Term, {session_obj.year} to download your results.", "alert-warning")
                app.logger.info(f"Student {student_id} denied PDF download due to unpaid fees for {term}, {session_obj.year}")
                return redirect(url_for("students.student_portal"))

        class_name = student.get_class_by_session(session_obj.year)
        if not class_name:
            app.logger.info(f"No class history for {student.id} in {session_obj.year}")
            flash(f"No class history found for {session_obj.year}", "alert-info")
            return redirect(url_for("students.select_results", student_id=student.id))

        results = Result.query.filter_by(
            student_id=student.id,
            term=term,
            session_id=session_obj.id  # Use session_id
        ).all()
        if not results:
            flash(f"No results found for {term} in {session_obj.year}", "alert-info")
            app.logger.info(f"No results found for student_id: {student_id}, term: {term}, session_id: {session_id}")
            return redirect(url_for("students.select_results", student_id=student.id))

        # Calculate grand_total from subject-specific totals
        grand_total = {
            "class_assessment": sum(result.class_assessment or 0 for result in results),
            "summative_test": sum(result.summative_test or 0 for result in results),
            "exam": sum(result.exam or 0 for result in results),
            "total": sum(result.total or 0 for result in results),
        }

        # Fetch term summary for aggregates
        term_summary = StudentTermSummary.query.filter_by(
            student_id=student.id,
            term=term,
            session_id=session_obj.id
        ).first()

        last_term_average = term_summary.last_term_average if term_summary else None
        average = term_summary.term_average if term_summary else None
        cumulative_average = term_summary.cumulative_average if term_summary else None
        subjects_offered = term_summary.subjects_offered if term_summary else len(results)
        next_term_begins = term_summary.next_term_begins if term_summary else None
        position = term_summary.position if term_summary else None
        date_issued = term_summary.date_issued if term_summary else None
        principal_remark = term_summary.principal_remark if term_summary else None
        teacher_remark = term_summary.teacher_remark if term_summary else None
        date_printed = datetime.now().strftime('%dth %B, %Y')

        logo_path = os.path.join(app.root_path, "static", "images", "school_logo.png")
        logo_url = f"file://{logo_path}" if os.path.exists(logo_path) else ""
        signature_path = os.path.join(app.root_path, "static", "images", "signature_anne.png")
        signature_url = f"file://{signature_path}" if os.path.exists(signature_path) else ""

        rendered = render_template(
            "student/pdf_results.html",
            title=f"{student.first_name}_{student.last_name}_{term}_{session_obj.year}_Result",
            student=student,
            results=results,
            term=term,
            session_id=session_obj.id,
            session_year=session_obj.year,  # For display
            grand_total=grand_total,
            school_name=app.config.get("SCHOOL_NAME", "Aunty Anne's Int'l School"),
            average=average,
            cumulative_average=cumulative_average,
            next_term_begins=next_term_begins,
            last_term_average=last_term_average,
            position=position,
            date_issued=date_issued,
            date_printed=date_printed,
            logo_url=logo_url,
            signature_url=signature_url,
            class_name=class_name,
            principal_remark=principal_remark,
            teacher_remark=teacher_remark,
        )

        pdf = HTML(string=rendered).write_pdf()
        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = (
            f"inline; filename={student.first_name}_{student.last_name}_{term}_{session_obj.year}_Result.pdf"
        )

        app.logger.info(f"PDF results downloaded for student_id: {student_id}, term: {term}, session_id: {session_id}")
        return response
    except OperationalError as e:
        app.logger.error(f"Database error downloading PDF for student_id {student_id}: {str(e)}")
        flash("Database error occurred. Please try again.", "alert-danger")
        return redirect(url_for("students.select_results", student_id=student_id))


@student_bp.route("/student/<int:student_id>/profile")
@login_required
def student_profile(student_id):
    student = Student.query.get_or_404(student_id)
    form = ResultForm()
    if current_user.id != student.user_id:
        flash("Unauthorized access.", "alert-danger")
        app.logger.warning(f"Unauthorized profile access by {current_user.username} for student_id {student_id}")
        return redirect(url_for("main.index"))

    latest_result = Result.query.filter_by(student_id=student.id).order_by(desc(Result.created_at)).first()
    if latest_result:
        current_term = latest_result.term
        current_session = Session.query.get(latest_result.session_id)
        if not current_session:
            flash("Session for latest result not found.", "alert-danger")
            return redirect(url_for("auth.login"))
    else:
        # Fallback to global current session and term if no results exist
        current_session, current_term_enum = Session.get_current_session_and_term(include_term=True)
        if not current_session or not current_term_enum:
            flash("No active session or term set and no results found.", "alert-danger")
            return redirect(url_for("auth.login"))
        current_term = current_term_enum.value

    class_obj = Classes.query.get(latest_result.class_id)
    return render_template(
        "student/student_profile.html",
        student=student,
        form=form,
        class_name=class_obj.name,
        # current_session=current_session.id,
        # current_term=current_term
    )

@student_bp.route("/student/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_profile(student_id):
    student = Student.query.get_or_404(student_id)
    if current_user.id != student.user_id:
        return redirect(url_for("main.index"))

    form = ResultForm()
    upload_folder = get_upload_folder()
    os.makedirs(upload_folder, exist_ok=True)

    if request.method == "POST":
        try:
            if 'first_name' in request.form and request.form['first_name']:
                student.first_name = request.form['first_name']
            if 'last_name' in request.form and request.form['last_name']:
                student.last_name = request.form['last_name']
            if 'middle_name' in request.form:
                student.middle_name = request.form['middle_name']
            if 'gender' in request.form and request.form['gender']:
                student.gender = request.form['gender']
            if 'address' in request.form:
                student.address = request.form['address']
            if 'date_of_birth' in request.form and request.form['date_of_birth']:
                student.date_of_birth = datetime.strptime(request.form['date_of_birth'], "%Y-%m-%d")
            if 'parent_name' in request.form:
                student.parent_name = request.form['parent_name']
            if 'parent_phone_number' in request.form:
                student.parent_phone_number = request.form['parent_phone_number']
            if 'parent_occupation' in request.form:
                student.parent_occupation = request.form['parent_occupation']

            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"{student_id}_{file.filename}")
                    file.save(os.path.join(upload_folder, filename))
                    student.profile_pic = url_for('static', filename=f'images/uploads/profile_pics/{filename}')

            db.session.commit()
            flash("Profile updated successfully!", "alert-success")

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": True, "message": "Profile picture updated"})
            return redirect(url_for("students.student_profile", student_id=student_id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating profile: {str(e)}")
            flash("An error occurred while updating your profile.", "alert-danger")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": str(e)}), 500
            return redirect(url_for("students.student_profile", form=form, student_id=student_id))

    return render_template("student/edit_profile.html", form=form, student=student)

@student_bp.route("/student/<int:student_id>/update_field", methods=["POST"])
@login_required
def update_field(student_id):
    student = Student.query.get_or_404(student_id)
    if current_user.id != student.user_id:
        return jsonify({"error": "Unauthorized"}), 403

    field = request.json.get("field")
    value = request.json.get("value")
    try:
        if hasattr(student, field):
            if field == "date_of_birth" and value:
                value = datetime.strptime(value, "%Y-%m-%d")
            setattr(student, field, value)
            db.session.commit()
            return jsonify({"success": True, "message": f"{field.replace('_', ' ').title()} updated"})
        return jsonify({"error": "Invalid field"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@student_bp.route("/student/<int:student_id>/remove_profile_pic", methods=["POST"])
@login_required
def remove_profile_pic(student_id):
    student = Student.query.get_or_404(student_id)
    if current_user.id != student.user_id:
        flash("Unauthorized access.", "alert-danger")
        app.logger.warning(f"Unauthorized profile picture removal attempt by {current_user.username} for student_id {student_id}")
        return redirect(url_for("main.index"))

    try:
        if student.profile_pic:
            file_path = os.path.join(get_upload_folder(), os.path.basename(student.profile_pic))
            if os.path.exists(file_path):
                os.remove(file_path)
            student.profile_pic = None
            db.session.commit()
            flash("Profile picture removed successfully!", "alert-success")
        else:
            flash("No profile picture to remove.", "alert-info")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": True, "message": "Profile picture removed"})
        return redirect(url_for("students.student_profile", student_id=student_id))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error removing profile picture for student_id {student_id}: {str(e)}")
        flash("An error occurred while removing the profile picture.", "alert-danger")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": str(e)}), 500
        return redirect(url_for("students.student_profile", student_id=student_id))

def get_upload_folder():
    return os.path.join(app.static_folder, 'images', 'uploads', 'profile_pics')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


