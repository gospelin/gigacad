from . import student_bp
import logging
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    # make_response,
)
from flask_login import login_required, current_user
from ..models import Student, Result
from ..auth.forms import ResultForm
from ..helpers import (
    get_last_term,
    calculate_average,
    calculate_cumulative_average,
)

from weasyprint import HTML


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@student_bp.route("/student_portal")
@login_required
def student_portal():
    try:
        if current_user.is_admin:
            return redirect(url_for("admins.admin_dashboard"))

        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            flash("Student not found", "alert alert-danger")
            logger.warning(f"Student not found for user_id: {current_user.id}")
            return redirect(url_for("auth.login"))

        logger.info(f"Accessing student portal for student_id: {student.id}")
        return render_template(
            "student/student_portal.html", student_id=student.id, student=student
        )

    except Exception as e:
        logger.error(f"Error accessing student portal: {str(e)}")
        flash("An error occurred. Please try again later.", "alert alert-danger")
        return redirect(url_for("auth.login"))


@student_bp.route("/student/<int:student_id>/profile")
@login_required
def student_profile(student_id):
    # Fetch the student details from the database
    student = Student.query.get_or_404(student_id)

    # Ensure the logged-in user is authorized to view this profile
    if current_user.id != student.user_id and not current_user.is_admin:
        flash("You are not authorized to view this profile.", "alert alert-danger")
        return redirect(url_for("main.index"))

    return render_template("student/student_profile.html", student=student)


@student_bp.route("/select_results/<int:student_id>", methods=["GET", "POST"])
@login_required
def select_results(student_id):
    student = Student.query.get_or_404(student_id)
    form = ResultForm()
    if form.validate_on_submit():
        term = form.term.data
        session = form.session.data
        return redirect(
            url_for("students.view_results", student_id=student.id, term=term, session=session)
        )
    return render_template("student/select_results.html", student=student, form=form)


@student_bp.route("/view_results/<int:student_id>", methods=["GET", "POST"])
@login_required
def view_results(student_id):
    try:
        student = Student.query.get_or_404(student_id)

        # Ensure the current user is authorized to view the student's results
        if current_user.id != student.user_id and not current_user.is_admin:
            flash("You are not authorized to view this profile.", "alert alert-danger")
            logger.warning(
                f"Unauthorized access attempt by user_id: {current_user.id} for student_id: {student_id}"
            )
            return redirect(url_for("main.index"))

        term = request.args.get("term")
        session = request.args.get("session")

        if not term or not session:
            return redirect(url_for("students.select_term_session", student_id=student.id))

        results = Result.query.filter_by(
            student_id=student.id, term=term, session=session
        ).all()
        if not results:
            flash("No results found for this term or session", "alert alert-info")
            logger.info(
                f"No results found for student_id: {student_id}, term: {term}, session: {session}"
            )
            return redirect(url_for("students.select_results", student_id=student.id))

        grand_total = {
            "class_assessment": sum(result.class_assessment for result in results),
            "summative_test": sum(result.summative_test for result in results),
            "exam": sum(result.exam for result in results),
            "total": sum(result.total for result in results),
        }

        average = grand_total["total"] / len(results) if results else 0
        average = round(average, 1)

        last_term = get_last_term(term)
        last_term_results = Result.query.filter_by(
            student_id=student.id, term=last_term, session=session
        ).all()
        last_term_average = (
            calculate_average(last_term_results) if last_term_results else 0
        )
        last_term_average = round(last_term_average, 1)

        # Add last_term_average to each result in results for cumulative calculation
        for res in results:
            res.last_term_average = last_term_average

        cumulative_average = calculate_cumulative_average(results, average)
        cumulative_average = round(cumulative_average, 1)

        next_term_begins = results[0].next_term_begins if results else None
        position = results[0].position if results else None

        logger.info(
            f"Results viewed for student_id: {student_id}, term: {term}, session: {session}"
        )
        return render_template(
            "student/view_results.html",
            title=f"{student.first_name}_{student.last_name}_{term}_{session}_Result",
            student=student,
            results=results,
            term=term,
            session=session,
            grand_total=grand_total,
            average=average,
            cumulative_average=cumulative_average,
            school_name="Aunty Anne's Int'l School",
            next_term_begins=next_term_begins,
            last_term_average=last_term_average,
            position=position,
        )

    except Exception as e:
        logger.error(f"Error viewing results for student_id: {student_id} - {str(e)}")
        flash("An error occurred. Please try again later.", "alert alert-danger")
        return redirect(url_for("students.select_results"))


@student_bp.route("/download_results_pdf/<int:student_id>")
@login_required
def download_results_pdf(student_id):
    try:
        student = Student.query.get_or_404(student_id)

        # Ensure the current user is authorized to download the student's results PDF
        if current_user.id != student.user_id and not current_user.is_admin:
            flash("You are not authorized to view this profile.", "alert alert-danger")
            logger.warning(
                f"Unauthorized access attempt by user_id: {current_user.id} for student_id: {student_id}"
            )
            return redirect(url_for("main.index"))

        term = request.args.get("term")
        session = request.args.get("session")

        if not term or not session:
            flash("Term and session must be specified.", "alert alert-info")
            return redirect(url_for("students.select_term_session", student_id=student.id))

        results = Result.query.filter_by(
            student_id=student.id, term=term, session=session
        ).all()
        if not results:
            flash("No results found for this term or session", "alert alert-info")
            logger.info(
                f"No results found for student_id: {student_id}, term: {term}, session: {session}"
            )
            return redirect(url_for("students.select_results", student_id=student.id))

        grand_total = {
            "class_assessment": sum(result.class_assessment for result in results),
            "summative_test": sum(result.summative_test for result in results),
            "exam": sum(result.exam for result in results),
            "total": sum(result.total for result in results),
        }

        average = grand_total["total"] / len(results) if results else 0
        average = round(average, 1)

        last_term = get_last_term(term)
        last_term_results = Result.query.filter_by(
            student_id=student.id, term=last_term, session=session
        ).all()
        last_term_average = (
            calculate_average(last_term_results) if last_term_results else 0
        )

        for res in results:
            res.last_term_average = last_term_average

        cumulative_average = calculate_cumulative_average(results, average)

        next_term_begins = results[0].next_term_begins if results else None
        position = results[0].position if results else None

        # Get the absolute path to the static directory
        static_path = os.path.join(
            app.root_path, "static", "images", "MY_SCHOOL_LOGO.png"
        )
        static_url = f"file://{static_path}"

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
            static_url=static_url,
        )

        pdf = HTML(string=rendered).write_pdf()

        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = (
            f"inline; filename={student.first_name}_{student.last_name}_{term}_{session}_Result.pdf"
        )

        logger.info(
            f"PDF results downloaded for student_id: {student_id}, term: {term}, session: {session}"
        )
        return response

    except Exception as e:
        logger.error(
            f"Error downloading PDF results for student_id: {student_id} - {str(e)}"
        )
        flash(
            "An error occurred while generating the PDF. Please try again later.",
            "alert alert-danger",
        )
        return redirect(url_for("students.select_results"))
