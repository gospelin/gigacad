import random, string, time
from . import db
from flask import request, abort, current_app as app
from .models import Student, Subject, Result
from functools import wraps
from datetime import datetime
from application.auth.forms import SubjectResultForm


login_attempts = {}


def rate_limit(limit, per):
    """
    Decorator function that limits the rate at which a function can be called.

    Args:
        limit (int): The maximum number of calls allowed within the specified time period.
        per (int): The time period (in seconds) within which the maximum number of calls is allowed.

    Returns:
        function: The decorated function.

    Raises:
        HTTPException: If the maximum number of calls has been exceeded, a 429 Too Many Requests error is raised.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr
            now = time.time()
            attempts = login_attempts.get(ip, [])
            attempts = [timestamp for timestamp in attempts if now - timestamp < per]

            if len(attempts) >= limit:
                abort(429)  # Too Many Requests

            attempts.append(now)
            login_attempts[ip] = attempts
            return f(*args, **kwargs)

        return wrapped

    return decorator


def generate_unique_username(first_name, last_name):
    """
    Generate a unique username based on the given first name and last name.

    Args:
        first_name (str): The first name of the user.
        last_name (str): The last name of the user.

    Returns:
        str: The generated unique username.
    """
    username = f"{first_name.strip().lower()}.{last_name.strip().lower()}"
    existing_user = Student.query.filter_by(username=username).first()
    if existing_user:
        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=4)
        )
        username = f"{username}{random_suffix}"
    return username


def calculate_grade(total):
    if total >= 95:
        return "A+"
    elif total >= 80:
        return "A"
    elif total >= 70:
        return "B+"
    elif total >= 65:
        return "B"
    elif total >= 60:
        return "C+"
    elif total >= 50:
        return "C"
    elif total >= 40:
        return "D"
    elif total >= 30:
        return "E"
    else:
        return "F"


def generate_remark(total):
    if total >= 95:
        return "Outstanding"
    elif total >= 80:
        return "Excellent"
    elif total >= 70:
        return "Very Good"
    elif total >= 65:
        return "Good"
    elif total >= 60:
        return "Credit"
    elif total >= 50:
        return "Credit"
    elif total >= 40:
        return "Poor"
    elif total >= 30:
        return "Very Poor"
    else:
        return "Failed"


def calculate_grand_total(results):
    """Calculate the total score from all results."""
    # return sum(result.total for result in results if result.total is not None)
    return sum(result.total for result in results)


def get_last_term(current_term):
    """
    Get the last term in sequence.
    """
    terms = ["First Term", "Second Term", "Third Term"]
    index = terms.index(current_term)
    return terms[index - 1] if index > 0 else None


def calculate_average(results):
    """
    Calculate the average score based on non-zero totals.
    """
    total_sum = sum(result.total for result in results if result.total > 0)
    non_zero_subjects = sum(1 for result in results if result.total > 0)

    return total_sum / non_zero_subjects if non_zero_subjects > 0 else 0


def calculate_cumulative_average(yearly_results):
    """
    Calculate the cumulative average over an academic year.
    Divides the total score by the number of subjects with non-zero totals.
    """
    total_sum = sum(result.total for result in yearly_results if result.total > 0)
    non_zero_subjects = sum(1 for result in yearly_results if result.total > 0)

    return total_sum / non_zero_subjects if non_zero_subjects > 0 else 0


def get_subjects_by_class_name(class_name):
    """Get subjects based on the student's class name from history.

    Args:
        student_class_history (object): The student's class history object.

    Returns:
        list: A list of subjects based on the student's class name.
    """

    if "Nursery" in class_name:
        return Subject.query.filter_by(section="Nursery").all()
    elif "Basic" in class_name:
        return Subject.query.filter_by(section="Basic").all()
    else:
        return Subject.query.filter_by(section="Secondary").all()


# Helper function to populate form with existing results
def populate_form_with_results(form, subjects, results_dict):
    for subject in subjects:
        result = results_dict.get(subject.id)
        subject_form = SubjectResultForm(
            subject_id=subject.id,
            class_assessment=result.class_assessment if result else 0,
            summative_test=result.summative_test if result else 0,
            exam=result.exam if result else 0,
            total=result.total if result else 0,
            grade=result.grade if result else "",
            remark=result.remark if result else "",
        )
        form.subjects.append_entry(subject_form)
        app.logger.info(f"Subject form added for subject ID {subject.id}")


def update_results(student, term, session_year, form, result_form):
    """
    Proceed with updating results for each subject.
    """

    # Proceed with updating results
    for subject_form in form.subjects:
        subject_id = subject_form.subject_id.data
        class_assessment = subject_form.class_assessment.data
        summative_test = subject_form.summative_test.data
        exam = subject_form.exam.data

        class_assessment_value = int(class_assessment) if class_assessment else 0
        summative_test_value = int(summative_test) if summative_test else 0
        exam_value = int(exam) if exam else 0
        total = class_assessment_value + summative_test_value + exam_value

        grade = calculate_grade(total)
        remark = generate_remark(total)

        # Save or update result in the database
        result = Result.query.filter_by(
            student_id=student.id,
            subject_id=subject_id,
            term=term,
            session=session_year,
        ).first()

        if result:
            # Update the existing result
            result.class_assessment = class_assessment_value
            result.summative_test = summative_test_value
            result.exam = exam_value
            result.total = total
            result.grade = grade
            result.remark = remark
            result.next_term_begins = result_form.next_term_begins.data
            result.last_term_average = result_form.last_term_average.data
            result.position = result_form.position.data
            result.date_issued = result_form.date_issued.data
        else:
            # Create a new result if it doesn't exist
            new_result = Result(
                student_id=student.id,
                subject_id=subject_id,
                term=term,
                session=session_year,
                class_assessment=class_assessment_value,
                summative_test=summative_test_value,
                exam=exam_value,
                total=total,
                grade=grade,
                remark=remark,
                next_term_begins=result_form.next_term_begins.data,
                last_term_average=result_form.last_term_average.data,
                position=result_form.position.data,
                date_issued=result_form.date_issued.data,
            )
            db.session.add(new_result)
            app.logger.info(f"Result added: {new_result}")
    db.session.commit()


def calculate_results(student_id, term, session_year):
    """
    Calculate student results and averages.
    """

    # Fetch results for the current term and session
    results = Result.query.filter_by(
        student_id=student_id, term=term, session=session_year
    ).all()

    app.logger.info(f"Fetched {len(results)} results for the current term and session")

    # Calculate grand total and average for the current term
    grand_total = sum(result.total for result in results)
    average = round(calculate_average(results), 1)
    app.logger.info(f"Grand total: {grand_total}, Average: {average}")

    # Fetch all results for the academic year (cumulative calculation)
    yearly_results = Result.query.filter_by(
        student_id=student_id, session=session_year
    ).all()

    app.logger.info(f"Fetched {len(yearly_results)} results for the entire academic year")

    # Calculate cumulative average across the academic year
    cumulative_average = round(calculate_cumulative_average(yearly_results), 1)
    app.logger.info(f"Cumulative average: {cumulative_average}")

    # Fetch and calculate last term's average
    last_term = get_last_term(term)
    last_term_results = Result.query.filter_by(
        student_id=student_id, term=last_term, session=session_year
    ).all()

    last_term_average = (
        round(calculate_average(last_term_results), 1) if last_term_results else 0
    )
    app.logger.info(f"Last term average: {last_term_average}")

    # Update current results with the last term average
    for res in results:
        res.last_term_average = last_term_average

    return grand_total, average, cumulative_average
