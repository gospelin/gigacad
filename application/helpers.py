import random, string, time
from . import db
from flask import request, abort
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


def get_remark(total):
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
    return sum(result.total for result in results)


def get_last_term(current_term):
    term_sequence = ["First Term", "Second Term", "Third Term"]
    if current_term in term_sequence:
        current_index = term_sequence.index(current_term)
        last_index = current_index - 1 if current_index > 0 else None
        return term_sequence[last_index] if last_index is not None else None
    return None


def calculate_average(results):
    total = sum(result.total for result in results)
    return total / len(results) if results else 0


def calculate_cumulative_average(results, current_term_average):
    last_term_average = 0
    cumulative_average = current_term_average
    if results:
        last_term_average = (
            float(results[0].last_term_average) if results[0].last_term_average else 0
        )

    if last_term_average and current_term_average:
        cumulative_average = (last_term_average + current_term_average) / 2

    return cumulative_average


def get_subjects_by_entry_class(entry_class):
    if "Nursery" in entry_class:
        return Subject.query.filter_by(section="Nursery").all()
    elif "Basic" in entry_class:
        return Subject.query.filter_by(section="Basic").all()
    else:
        return Subject.query.filter_by(section="Secondary").all()


def update_results(student, subjects, term, session, form):
    try:
        for subject in subjects:
            class_assessment = request.form.get(f"class_assessment_{subject.id}", 0)
            summative_test = request.form.get(f"summative_test_{subject.id}", 0)
            exam = request.form.get(f"exam_{subject.id}", 0)
            total = int(class_assessment) + int(summative_test) + int(exam)
            grade = calculate_grade(total)
            remark = get_remark(total)

            result = Result.query.filter_by(
                student_id=student.id, subject_id=subject.id, term=term, session=session
            ).first()
            if not result:
                result = Result(
                    student_id=student.id,
                    subject_id=subject.id,
                    term=term,
                    session=session,
                    class_assessment=class_assessment,
                    summative_test=summative_test,
                    exam=exam,
                    total=total,
                    grade=grade,
                    remark=remark,
                    next_term_begins=form.next_term_begins.data,
                    last_term_average=form.last_term_average.data,
                    position=form.position.data,
                    date_issued=datetime.now(),
                )
                db.session.add(result)
            else:
                result.class_assessment = class_assessment
                result.summative_test = summative_test
                result.exam = exam
                result.total = total
                result.grade = grade
                result.remark = remark
                result.next_term_begins = form.next_term_begins.data
                result.last_term_average = form.last_term_average.data
                result.position = form.position.data

        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


def calculate_results(student_id, term, session):
    results = Result.query.filter_by(
        student_id=student_id, term=term, session=session
    ).all()
    grand_total = calculate_grand_total(results)
    average = round(calculate_average(results), 1)

    last_term = get_last_term(term)
    last_term_results = Result.query.filter_by(
        student_id=student_id, term=last_term, session=session
    ).all()
    last_term_average = round(
        calculate_average(last_term_results) if last_term_results else 0, 1
    )

    for res in results:
        res.last_term_average = last_term_average

    cumulative_average = round(calculate_cumulative_average(results, average), 1)
    results_dict = {result.subject_id: result for result in results}

    return results, grand_total, average, cumulative_average, results_dict
