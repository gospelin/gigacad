from . import student_bp
import os
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    current_app as app,
    make_response,
)
from flask_login import login_required, current_user
from ..models import Student, Result, Session, StudentClassHistory
from ..auth.forms import ResultForm
from ..helpers import (
    get_last_term,
    datetime,
    calculate_average,
    calculate_cumulative_average,
)

from weasyprint import HTML


@student_bp.route("/student_portal")
@login_required
def student_portal():
    try:
        if current_user.is_admin:
            return redirect(url_for("admins.admin_dashboard"))

        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            flash("Student not found", "alert alert-danger")
            app.logger.warning(f"Student not found for user_id: {current_user.id}")
            return redirect(url_for("auth.login"))

        app.logger.info(
            f"Accessing student portal for student_id: {student.id}, {student.first_name = } {student.last_name = }"
        )
        return render_template(
            "student/student_portal.html", student_id=student.id, student=student,
            logo_url="auntyannesschools.com.ng/AAIS/application/static/images/MY_SCHOOL_LOGO.png",
        )

    except Exception as e:
        app.logger.error(f"Error accessing student portal: {str(e)}")
        flash("An error occurred. Please try again later.", "alert alert-danger")
        return redirect(url_for("auth.login"))


@student_bp.route("/student/<int:student_id>/profile", subdomain="portal")
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
        if current_user.id != student.user_id and not current_user.is_admin:
            flash("You are not authorized to view this profile.", "alert alert-danger")
            app.logger.warning(
                f"Unauthorized access attempt by user_id: {current_user.id} for student_id: {student_id}"
            )
            return redirect(url_for("main.index"))

        term = request.args.get("term")
        session = request.args.get("session")

        if not term or not session:
            return redirect(
                url_for("students.select_term_session", student_id=student.id)
            )

        # Fetch session and student class history in a single query

        student_class = StudentClassHistory.get_class_by_session(
            student_id=student.id, session_year_str=session
        )

        if not student_class:

            app.logger.error(f"No class history for {student.id} in {session}")

            app.logger.error(f"{student.first_name} {student.last_name} is not in any class as at {session}")
            flash(f"{student.first_name} {student.last_name} is not in any class as at {session}")
            return redirect(url_for("students.select_results", student_id=student.id))

        results = Result.query.filter_by(
            student_id=student.id, term=term, session=session
        ).all()

        if not results:
            flash("No results found for this term or session")
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

        average = round(calculate_average(results), 1)
        app.logger.info(f"Grand total: {grand_total}, Average: {average}")

        # Fetch and calculate last term's average
        last_term = get_last_term(term)
        last_term_results = Result.query.filter_by(
            student_id=student_id, term=last_term, session=session
        ).all()

        last_term_average = (
            round(calculate_average(last_term_results), 1) if last_term_results else 0
        )
        app.logger.info(f"Last term average: {last_term_average}")

        # Update current results with the last term average
        for res in results:
            res.last_term_average = last_term_average

        # Fetch all results for the academic year (cumulative calculation)
        yearly_results = Result.query.filter_by(
            student_id=student_id, session=session
        ).all()

        app.logger.info(
            f"Fetched {len(yearly_results)} results for the entire academic year"
        )

        # Calculate cumulative average across the academic year
        cumulative_average = round(calculate_cumulative_average(yearly_results), 1)
        app.logger.info(f"Cumulative average: {cumulative_average}")

        next_term_begins = results[0].next_term_begins if results else None
        position = results[0].position if results else None
        date_issued = results[0].date_issued if results else None

        date_printed = datetime.now().strftime("%dth %B, %Y")


        app.logger.info(
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
            date_issued=date_issued,
            date_printed=date_printed,
            position=position,
            student_class=student_class,
        )

    except Exception as e:
        app.logger.error(
            f"Error viewing results for student_id: {student_id} - {str(e)}"
        )
        flash("An error occurred. Please try again later.", "alert alert-danger")
        return redirect(url_for("students.select_results", student_id=student.id))


@student_bp.route("/download_results_pdf/<int:student_id>")
@login_required
def download_results_pdf(student_id):
    try:
        student = Student.query.get_or_404(student_id)

        # Ensure the current user is authorized to download the student's results PDF
        if current_user.id != student.user_id and not current_user.is_admin:
            flash("You are not authorized to view this profile.", "alert alert-danger")
            app.logger.warning(
                f"Unauthorized access attempt by user_id: {current_user.id} for student_id: {student_id}"
            )
            return redirect(url_for("main.index"))

        term = request.args.get("term")
        session = request.args.get("session")

        if not term or not session:
            flash("Term and session must be specified.", "alert alert-info")
            return redirect(url_for("students.select_term_session", student_id=student.id))
            
        # Fetch session and student class history in a single query
        student_class = StudentClassHistory.get_class_by_session(
            student_id=student.id, session_year_str=session
        )

        if not student_class:
            app.logger.error(f"No class history for {student.id} in {session.year}")

        results = Result.query.filter_by(
            student_id=student.id, term=term, session=session
        ).all()
        if not results:
            flash("No results found for this term or session", "alert alert-info")
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

        average = round(calculate_average(results), 1)
        app.logger.info(f"Grand total: {grand_total}, Average: {average}")

        # Fetch and calculate last term's average
        last_term = get_last_term(term)
        last_term_results = Result.query.filter_by(
            student_id=student_id, term=last_term, session=session
        ).all()

        last_term_average = (
            round(calculate_average(last_term_results), 1) if last_term_results else 0
        )
        app.logger.info(f"Last term average: {last_term_average}")

        # Update current results with the last term average
        for res in results:
            res.last_term_average = last_term_average

        # Fetch all results for the academic year (cumulative calculation)
        yearly_results = Result.query.filter_by(
            student_id=student_id, session=session
        ).all()

        app.logger.info(
            f"Fetched {len(yearly_results)} results for the entire academic year"
        )

        # Calculate cumulative average across the academic year
        cumulative_average = round(calculate_cumulative_average(yearly_results), 1)
        app.logger.info(f"Cumulative average: {cumulative_average}")

        next_term_begins = results[0].next_term_begins if results else None
        position = results[0].position if results else None
        date_issued = results[0].date_issued if results else None

        # Get the absolute path to the static directory
        static_path = os.path.join(app.root_path, "static", "images", "MY_SCHOOL_LOGO.png")
        static_url = f"file://{static_path}"

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
            static_url=static_url,
            student_class=student_class,
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
            "alert alert-danger",
        )
        return redirect(url_for("students.select_results", student_id=student.id))
