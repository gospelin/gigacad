import random, string, time
from . import db
from flask import request, abort, flash
from .models import Student, Subject, Result
from sqlalchemy.exc import SQLAlchemyError
from functools import wraps
from datetime import datetime


login_attempts = {}


def rate_limit(limit, per):
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
    return sum(result.total for result in results if result.total is not None)


def get_last_term(current_term):
    """Get the last term in the academic sequence."""
    term_sequence = ["First Term", "Second Term", "Third Term"]
    if current_term in term_sequence:
        current_index = term_sequence.index(current_term)
        last_index = current_index - 1 if current_index > 0 else None
        return term_sequence[last_index] if last_index is not None else None
    return None


def calculate_average(results):
    """Calculate the average score from the results."""
    grand_total = 0
    non_zero_subjects = 0

    for result in results:
        if result.total and result.total > 0:  # Ensure total is valid
            grand_total += result.total
            non_zero_subjects += 1

    return grand_total / non_zero_subjects if non_zero_subjects > 0 else 0


def calculate_cumulative_average(results, current_term_average):
    """Calculate the cumulative average from the current and last term averages."""
    last_term_average = (
        float(results[0].last_term_average)
        if results and results[0].last_term_average
        else 0
    )

    if last_term_average and current_term_average:
        cumulative_average = (last_term_average + current_term_average) / 2
    else:
        cumulative_average = current_term_average

    return cumulative_average


def get_subjects_by_class_name(student_class_history):
    """Get subjects based on the student's entry class."""
    # Assuming 'student_class_history' has an attribute 'class_name' that contains the class name
    class_name = (
        student_class_history.class_name
    )  # Adjust this if the attribute name is different

    if "Nursery" in class_name:
        return Subject.query.filter_by(section="Nursery").all()
    elif "Basic" in class_name:
        return Subject.query.filter_by(section="Basic").all()
    else:
        return Subject.query.filter_by(section="Secondary").all()


def update_results(student, subjects, term, session, form):
    """Update or create results for the student based on form data."""
    try:
        for subject in subjects:
            class_assessment = request.form.get(f"class_assessment_{subject.id}", "0")
            summative_test = request.form.get(f"summative_test_{subject.id}", "0")
            exam = request.form.get(f"exam_{subject.id}", "0")

            # Convert string values to integers
            class_assessment_value = int(class_assessment) if class_assessment else 0
            summative_test_value = int(summative_test) if summative_test else 0
            exam_value = int(exam) if exam else 0

            total = class_assessment_value + summative_test_value + exam_value
            grade = calculate_grade(total)  # Ensure this function is defined
            remark = generate_remark(total)  # Ensure this function is defined

            result = Result.query.filter_by(
                student_id=student.id, subject_id=subject.id, term=term, session=session
            ).first()

            if result:
                result.class_assessment = class_assessment_value
                result.summative_test = summative_test_value
                result.exam = exam_value
                result.total = total
                result.grade = grade
                result.remark = remark
                result.next_term_begins = form.next_term_begins.data
                result.last_term_average = form.last_term_average.data
                result.position = form.position.data
                result.date_issued = form.date_issued.data
            else:
                new_result = Result(
                    student_id=student.id,
                    subject_id=subject.id,
                    term=term,
                    session=session,
                    class_assessment=class_assessment_value,
                    summative_test=summative_test_value,
                    exam=exam_value,
                    total=total,
                    grade=grade,
                    remark=remark,
                    next_term_begins=form.next_term_begins.data,
                    last_term_average=form.last_term_average.data,
                    position=form.position.data,
                    date_issued=form.date_issued.data,
                )
                db.session.add(new_result)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


def calculate_results(student_id, term, session):
    # Assuming session is an object, get the session ID
    session_id = session.id if hasattr(session, "id") else session

    student_class = Student.query.get(student_id).get_class_by_session(session)

    results = Result.query.filter_by(
        student_id=student_id,
        term=term,
        session_id=session_id,  # Use session_id here instead of session
    ).all()

    grand_total = calculate_grand_total(results)
    average = round(calculate_average(results), 1)

    last_term = get_last_term(term)
    last_term_results = Result.query.filter_by(
        student_id=student_id,
        term=last_term,
        session_id=session_id,  # Use session_id here as well
    ).all()

    last_term_average = round(
        calculate_average(last_term_results) if last_term_results else 0, 1
    )

    for res in results:
        res.last_term_average = last_term_average

    cumulative_average = round(calculate_cumulative_average(results, average), 1)
    results_dict = {result.subject_id: result for result in results}

    return results, grand_total, average, cumulative_average, results_dict
