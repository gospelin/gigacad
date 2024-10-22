import random, string, time
from . import db
from flask import request, abort, flash, current_app as app
from .models import Student, Subject, Result, StudentClassHistory
from sqlalchemy.exc import SQLAlchemyError
from functools import wraps
from datetime import datetime


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
    #return sum(result.total for result in results if result.total is not None)
    return sum(result.total for result in results)


def get_last_term(current_term):
    """
    Get the last term in the academic sequence.

    Args:
        current_term (str): The current term in the academic sequence.

    Returns:
        str or None: The last term in the academic sequence, or None if the current term is not found in the sequence.
    """
    term_sequence = ["First Term", "Second Term", "Third Term"]
    if current_term in term_sequence:
        current_index = term_sequence.index(current_term)
        last_index = current_index - 1 if current_index > 0 else None
        return term_sequence[last_index] if last_index is not None else None
    return None


def calculate_average(results):
    """
    Calculate the average score from the results.

    Args:
        results (list): A list of result objects.

    Returns:
        float: The average score calculated from the valid results. If there are no valid results, returns 0.
    """
    grand_total = 0
    non_zero_subjects = 0

    for result in results:
        if result.total > 0:
            grand_total += result.total
            non_zero_subjects += 1

    average = grand_total / non_zero_subjects if non_zero_subjects > 0 else 0
    return average 


def calculate_cumulative_average(results, current_term_average):
    """
    Calculate the cumulative average from the current and last term averages.

    Args:
        results (list): A list of objects containing the last term average.
        current_term_average (float): The average for the current term.

    Returns:
        float: The calculated cumulative average.

    """
    # last_term_average = (
    #    float(results[0].last_term_average)
    #    if results and results[0].last_term_average
    #    else 0
    # )

    # if last_term_average and current_term_average:
    #    cumulative_average = (last_term_average + current_term_average) / 2
    # else:
    #    cumulative_average = current_term_average

    # return cumulative_average

    last_term_average = 0
    cumulative_average = current_term_average
    if results:
        last_term_average = (
            float(results[0].last_term_average) if results[0].last_term_average else 0
        )

    if last_term_average and current_term_average:
        cumulative_average = (last_term_average + current_term_average) / 2

    return cumulative_average


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


# def update_results(student, subjects, term, session, form):

#    # Proceed with updating results for each subject
#    for subject in subjects:
#        class_assessment = request.form.get(f"class_assessment_{subject.id}", '')
#        summative_test = request.form.get(f"summative_test_{subject.id}", '')
#        exam = request.form.get(f"exam_{subject.id}", '')

#        # Convert empty values to zero for calculations
#        class_assessment_value = int(class_assessment) if class_assessment else None
#        summative_test_value = int(summative_test) if summative_test else None
#        exam_value = int(exam) if exam else None
#        total = (
#            (class_assessment_value or 0)
#            + (summative_test_value or 0)
#            + (exam_value or 0)
#        )
#        grade = calculate_grade(total)
#        remark = generate_remark(total)

#        # Query existing result
#        result = Result.query.filter_by(
#            student_id=student.id,
#            subject_id=subject.id,
#            term=term,
#            session=session,
#        ).first()

#        if result:
#            result.class_assessment = class_assessment_value
#            result.summative_test = summative_test_value
#            result.exam = exam_value
#            result.total = total
#            result.grade = grade
#            result.remark = remark
#            result.next_term_begins = form.next_term_begins.data
#            result.last_term_average = form.last_term_average.data
#            result.position = form.position.data
#            result.date_issued = form.date_issued.data
#        else:
#            new_result = Result(
#                student_id=student.id,
#                subject_id=subject.id,
#                term=term,
#                session=session,
#                class_assessment=class_assessment_value,
#                summative_test=summative_test_value,
#                exam=exam_value,
#                total=total,
#                grade=grade,
#                remark=remark,
#                next_term_begins=form.next_term_begins.data,
#                last_term_average=form.last_term_average.data,
#                position=form.position.data,
#                date_issued=form.date_issued.data,
#            )
#            db.session.add(new_result)

#    db.session.commit()
#    flash("Results updated successfully", "alert alert-success")


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


# def calculate_results(student_id, term, session):
#    """
#    Calculate student results and averages.
#    """

#    # Fetch results for the current term and session
#    results = Result.query.filter_by(
#        student_id=student_id,
#        term=term,
#        session=session,  # Use session_year directly
#    ).all()

#    flash(
#        f"Fetched {len(results)} results for the current term and session",
#        "alert alert-info",
#    )

#    grand_total = calculate_grand_total(results)
#    average = round(calculate_average(results), 1)
#    flash(f"Grand total: {grand_total}, Average: {average}", "alert alert-info")

#    last_term = get_last_term(term)
#    last_term_results = Result.query.filter_by(
#        student_id=student_id,
#        term=last_term,
#        session=session,
#    ).all()

#    if last_term_results:
#        flash(
#            f"Fetched {len(last_term_results)} results for the last term",
#            "alert alert-info",
#        )
#    else:
#        flash("No results found for the last term", "alert alert-warning")

#    last_term_average = round(calculate_average(last_term_results), 1) if last_term_results else 0

#    flash(f"Last term average: {last_term_average}", "alert alert-info")

#    for res in results:
#        res.last_term_average = last_term_average

#    cumulative_average = round(calculate_cumulative_average(results, average), 1)
#    flash(f"Cumulative average: {cumulative_average}", "alert alert-info")

#    results_dict = {result.subject_id: result for result in results}
#    return results, grand_total, average, cumulative_average, results_dict


def calculate_results(student_id, term, session_year):
    """
    Calculate student results and averages.
    """

    # Fetch results for the current term and session
    results = Result.query.filter_by(
        student_id=student_id,
        term=term,
        session=session_year,  # Use session_year directly
    ).all()

    flash(
        f"Fetched {len(results)} results for the current term and session",
        "alert alert-info",
    )

    # Calculate grand total and average for the current term
    grand_total = calculate_grand_total(results)
    average = round(calculate_average(results), 1)
    flash(f"Grand total: {grand_total}, Average: {average}", "alert alert-info")

    # Fetch results for the last term
    last_term = get_last_term(term)
    last_term_results = Result.query.filter_by(
        student_id=student_id,
        term=last_term,
        session=session_year,
    ).all()

    if last_term_results:
        flash(
            f"Fetched {len(last_term_results)} results for the last term",
            "alert alert-info",
        )
    else:
        flash("No results found for the last term", "alert alert-warning")

    # Calculate last term average
    last_term_average = (
        round(calculate_average(last_term_results), 1) if last_term_results else 0
    )
    flash(f"Last term average: {last_term_average}", "alert alert-info")

    # Update current results with the last term average
    for res in results:
        res.last_term_average = last_term_average

    # Calculate cumulative average
    cumulative_average = round(calculate_cumulative_average(results, average), 1)
    flash(f"Cumulative average: {cumulative_average}", "alert alert-info")

    
    return grand_total, average, cumulative_average
