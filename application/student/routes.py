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
from ..models import Student, Result, Session, StudentClassHistory, RoleEnum, Classes
from ..auth.forms import ResultForm
from ..helpers import (
    get_last_term,
    datetime,
    calculate_average,
    calculate_grade,
    calculate_cumulative_average,
    generate_excel_broadsheet,
    prepare_broadsheet_data,
)

from weasyprint import HTML


@student_bp.route("/dashboard")
@login_required
def student_portal():
    try:
        if current_user.role == RoleEnum.STUDENT:
            app.logger.info(
                f"Accessing student portal for student_id: {current_user.id}"
            )

            # Check if session data exists for overall performance, attendance, etc.
            overall_performance = session.get('average', 0)
            total_attendance = session.get('total_attendance', 95)
            total_subjects = session.get('total_subjects', 18)
            best_grade = session.get('best_grade', 'N/A')
            average = session.get('average', 0)

            return render_template(
                "student/student_portal.html",
                overall_performance=overall_performance,
                total_attendance=total_attendance,
                total_subjects=total_subjects,
                best_grade=best_grade,
                average=average,
            )
        else:
            redirect(url_for("auth.login"))

    except Exception as e:
        app.logger.error(f"Error accessing student portal: {str(e)}")
        flash("An error occurred. Please try again later.", "alert-danger")
        return redirect(url_for("auth.login"))


@student_bp.route("/student/<int:student_id>/profile", subdomain="portal")
@login_required
def student_profile(student_id):
    # Fetch the student details from the database
    student = Student.query.get_or_404(student_id)
    session_year = Session.get_current_session()


    # Ensure the logged-in user is authorized to view this profile
    if current_user.id != student.user_id:
        flash("You are not authorized to view this profile.", "alert-danger")
        return redirect(url_for("main.index"))

    class_name = student.get_class_by_session(session_year=session_year)

    return render_template("student/student_profile.html", student=student, class_name=class_name)



@student_bp.route("/select_results/<int:student_id>", methods=["GET", "POST"])
@login_required
def select_results(student_id):
    student = Student.query.get_or_404(student_id)
    form = ResultForm()

    # Fetch available sessions from the database
    sessions = Session.query.all()
    form.session.choices = [(s.year, s.year) for s in sessions]

    if form.validate_on_submit():
        term = form.term.data
        session = form.session.data
        return redirect(
            url_for(
                "students.view_results",
                student_id=student.id,
                term=term,
                session=session,
            )
        )
    return render_template("student/select_results.html", student=student, form=form)


@student_bp.route("/view_results/<int:student_id>", methods=["GET", "POST"])
@login_required
def view_results(student_id):
    try:
        student = Student.query.get_or_404(student_id)

        # Ensure the current user is authorized to view the student's results
        # if current_user.id != student.user_id and not current_user.is_admin:
        if current_user.id != student.user_id:
            flash("You are not authorized to view this profile.", "alert-danger")
            app.logger.warning(
                f"Unauthorized access attempt by user_id: {current_user.id} for student_id: {student_id}"
            )
            return redirect(url_for("main.index"))

        term = request.args.get("term")
        session_year = request.args.get("session")

        if not term or not session_year:
            return redirect(
                url_for("students.select_term_session", student_id=student.id)
            )

        # Fetch session and student class history in a single query

        class_name = student.get_class_by_session(session_year=session_year)

        if not class_name:
            flash(f"{student.first_name} {student.last_name} is not in any class as at {session_year}", "alert-info")
            return redirect(url_for("students.select_results", student_id=student.id))

        results = Result.query.filter_by(
            student_id=student.id, term=term, session=session_year
        ).all()

        if not results:
            flash("No results found for this term or session", "alert-danger")
            return redirect(url_for("students.select_results", student_id=student.id))

        # Calculate grand total and average based on non-zero totals
        grand_total = {
            "class_assessment": sum(result.class_assessment or 0 for result in results),
            "summative_test": sum(result.summative_test or 0 for result in results),
            "exam": sum(result.exam or 0 for result in results),
            "total": sum(result.total or 0 for result in results),
        }

        last_term_average = results[0].last_term_average if results else None
        average = results[0].term_average if results else None
        cumulative_average = results[0].cumulative_average if results else None
        subjects_offered = results[0].subjects_offered if results else None


        # Extract additional details from the first result (if available)
        next_term_begins = results[0].next_term_begins if results else None
        position = results[0].position if results else None
        date_issued = results[0].date_issued if results else None

        principal_remark = results[0].principal_remark if results else None
        teacher_remark = results[0].teacher_remark if results else None

        date_printed = datetime.now().strftime("%dth %B, %Y")

        session["average"] = average if average else 0
        session["total_attendance"] = 95
        session["total_subjects"] = subjects_offered if subjects_offered else 0
        grade = max([result.total or 0 for result in results])
        session["best_grade"] = calculate_grade(grade)


        app.logger.info(
            f"Results viewed for student_id: {student_id}, term: {term}, session: {session}"
        )
        return render_template(
            "student/view_results.html",
            title=f"{student.first_name}_{student.last_name}_{term}_{session}_Result",
            student=student,
            results=results,
            term=term,
            session=session_year,
            grand_total=grand_total,
            average=average,
            cumulative_average=cumulative_average,
            school_name="Aunty Anne's Int'l School",
            next_term_begins=next_term_begins,
            last_term_average=last_term_average,
            date_issued=date_issued,
            date_printed=date_printed,
            position=position,
            class_name=class_name,
        )

    except Exception as e:
        app.logger.error(
            f"Error viewing results for student_id: {student_id} - {str(e)}"
        )
        flash("An error occurred. Please try again later.", "alert-danger")
        return redirect(url_for("students.select_results", student_id=student.id))


@student_bp.route("/download_results_pdf/<int:student_id>")
@login_required
def download_results_pdf(student_id):
    try:
        student = Student.query.get_or_404(student_id)

        # Ensure the current user is authorized to download the student's results PDF
        if current_user.id != student.user_id and not current_user.is_admin:
            flash("You are not authorized to view this profile.", "alert-danger")
            app.logger.warning(
                f"Unauthorized access attempt by user_id: {current_user.id} for student_id: {student_id}"
            )
            return redirect(url_for("main.index"))

        term = request.args.get("term")
        session = request.args.get("session")

        if not term or not session:
            flash("Term and session must be specified.", "alert-danger")
            return redirect(url_for("students.select_term_session", student_id=student.id))

        # Fetch session and student class history in a single query
        class_name = student.get_class_by_session(session_year=session)

        if not class_name:
            app.logger.error(f"No class history for {student.id} in {session.year}")

        results = Result.query.filter_by(
            student_id=student.id, term=term, session=session
        ).all()
        if not results:
            flash("No results found for this term or session", "alert-danger")
            app.logger.info(
                f"No results found for student_id: {student_id}, term: {term}, session: {session}"
            )
            return redirect(url_for("students.select_results", student_id=student.id))

        # Calculate grand total and average based on non-zero totals
        grand_total = {
            "class_assessment": sum(result.class_assessment or 0 for result in results),
            "summative_test": sum(result.summative_test or 0 for result in results),
            "exam": sum(result.exam or 0 for result in results),
            "total": sum(result.total or 0 for result in results),
        }

        last_term_average = results[0].last_term_average if results else None
        average = results[0].term_average if results else None
        cumulative_average = results[0].cumulative_average if results else None
        subjects_offered = results[0].subjects_offered if results else None


        # Extract additional details from the first result (if available)
        next_term_begins = results[0].next_term_begins if results else None
        position = results[0].position if results else None
        date_issued = results[0].date_issued if results else None

        principal_remark = results[0].principal_remark if results else None
        teacher_remark = results[0].teacher_remark if results else None

        # Get the absolute path to the static directory
        logo_path = os.path.join(app.root_path, "static", "images", "school_logo.png")
        logo_url = f"file://{logo_path}"

        signature_path = os.path.join(app.root_path, "static", "images", "signature_anne.png")
        signature_url = f"file://{signature_path}"

        date_printed = datetime.now().strftime('%dth %B, %Y')

        rendered = render_template(
            "student/pdf_results.html",
            title=f"{student.first_name}_{student.last_name}_{term}_{session}_Result",
            student=student,
            results=results,
            term=term,
            session=session,
            grand_total=grand_total,
            school_name="Aunty Anne's Int'l School",
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
            f"inline; filename={student.first_name}_{student.last_name}_{term}_{session}_Result.pdf"
        )

        app.logger.info(
            f"PDF results downloaded for student_id: {student_id}, term: {term}, session: {session}"
        )
        return response

    except Exception as e:
        app.logger.error(
            f"Error downloading PDF results for student_id: {student_id} - {str(e)}"
        )
        flash(
            "An error occurred while generating the PDF. Please try again later.",
            "alert-danger",
        )
        return redirect(url_for("students.select_results", student_id=student.id))
