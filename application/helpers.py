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
    return sum(result.total for result in results)


def get_last_term(current_term):
    term_sequence = ["First Term", "Second Term", "Third Term"]
    if current_term in term_sequence:
        current_index = term_sequence.index(current_term)
        last_index = current_index - 1 if current_index > 0 else None
        return term_sequence[last_index] if last_index is not None else None
    return None


def calculate_average(results):
    grand_total = 0
    non_zero_subjects = 0

    for result in results:
        if result.total > 0:
            grand_total += result.total
            non_zero_subjects += 1

    average = grand_total / non_zero_subjects if non_zero_subjects > 0 else 0

    return average

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




# def update_results(student, subjects, term, session, form):
#     try:
#         for subject in subjects:
#             class_assessment = request.form.get(f"class_assessment_{subject.id}", '')
#             summative_test = request.form.get(f"summative_test_{subject.id}", '')
#             exam = request.form.get(f"exam_{subject.id}", '')

#             # class_assessment = request.form.get(f"class_assessment_{subject.id}", "")
#             # summative_test = request.form.get(f"summative_test_{subject.id}", "")
#             # exam = request.form.get(f"exam_{subject.id}", "")
#             # total = int(class_assessment or 0) + int(summative_test or 0) + int(exam or 0)

#             # Convert empty values to zero for calculations
#             class_assessment_value = int(class_assessment) if class_assessment else None
#             summative_test_value = int(summative_test) if summative_test else None
#             exam_value = int(exam) if exam else None
#             total = (class_assessment_value or 0) + (summative_test_value or 0) + (exam_value or 0)
#             grade = calculate_grade(total)
#             remark = generate_remark(total)


#             result = Result.query.filter_by(student_id=student.id, subject_id=subject.id, term=term, session=session).first()

#             if result:
#                 result.class_assessment = class_assessment_value
#                 result.summative_test = summative_test_value
#                 result.exam = exam_value
#                 result.total = total
#                 result.grade = grade  # Adjust this to your grade calculation logic
#                 result.remark = remark
#                 result.next_term_begins = form.next_term_begins.data
#                 result.last_term_average = form.last_term_average.data
#                 result.position = form.position.data
#                 result.date_issued=form.date_issued.data

#             else:
#                 new_result = Result(
#                     student_id=student.id,
#                     subject_id=subject.id,
#                     term=term,
#                     session=session,
#                     class_assessment=class_assessment_value,
#                     summative_test=summative_test_value,
#                     exam=exam_value,
#                     total=total,
#                     grade=grade,  # Adjust this to your grade calculation logic
#                     remark=remark,
#                     next_term_begins=form.next_term_begins.data,
#                     last_term_average=form.last_term_average.data,
#                     position=form.position.data,
#                     date_issued=form.date_issued.data,
#                 )
#                 db.session.add(new_result)

#         db.session.commit()
#     except Exception as e:
#         db.session.rollback()
#         raise e

# def calculate_results(student_id, term, session):
#     results = Result.query.filter_by(
#         student_id=student_id, term=term, session=session
#     ).all()
#     grand_total = calculate_grand_total(results)
#     average = round(calculate_average(results), 1)

#     last_term = get_last_term(term)
#     last_term_results = Result.query.filter_by(
#         student_id=student_id, term=last_term, session=session
#     ).all()
#     last_term_average = round(
#         calculate_average(last_term_results) if last_term_results else 0, 1
#     )

#     for res in results:
#         res.last_term_average = last_term_average

#     cumulative_average = round(calculate_cumulative_average(results, average), 1)
#     results_dict = {result.subject_id: result for result in results}

#     return results, grand_total, average, cumulative_average, results_dict


def update_results(student, subjects, term, session, form):
    try:
        # Proceed with updating results for each subject
        for subject in subjects:
            class_assessment = request.form.get(f"class_assessment_{subject.id}", '')
            summative_test = request.form.get(f"summative_test_{subject.id}", '')
            exam = request.form.get(f"exam_{subject.id}", '')

            # Convert empty values to zero for calculations
            class_assessment_value = int(class_assessment) if class_assessment else None
            summative_test_value = int(summative_test) if summative_test else None
            exam_value = int(exam) if exam else None
            total = (
                (class_assessment_value or 0)
                + (summative_test_value or 0)
                + (exam_value or 0)
            )
            grade = calculate_grade(total)
            remark = generate_remark(total)

            # Query existing result
            result = Result.query.filter_by(
                student_id=student.id,
                subject_id=subject.id,
                term=term,
                session=session,
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
    """
    Calculate student results and averages.
    """

    # Fetch results for the current term and session
    results = Result.query.filter_by(
        student_id=student_id,
        term=term,
        session=session,  # Use session_year directly
    ).all()

    flash(
        f"Fetched {len(results)} results for the current term and session",
        "alert alert-info",
    )

    grand_total = calculate_grand_total(results)
    average = round(calculate_average(results), 1)
    flash(f"Grand total: {grand_total}, Average: {average}", "alert alert-info")

    last_term = get_last_term(term)
    last_term_results = Result.query.filter_by(
        student_id=student_id,
        term=last_term,
        session=session,
    ).all()

    if last_term_results:
        flash(
            f"Fetched {len(last_term_results)} results for the last term",
            "alert alert-info",
        )
    else:
        flash("No results found for the last term", "alert alert-warning")

    last_term_average = round(calculate_average(last_term_results), 1) if last_term_results else 0

    flash(f"Last term average: {last_term_average}", "alert alert-info")

    for res in results:
        res.last_term_average = last_term_average

    cumulative_average = round(calculate_cumulative_average(results, average), 1)
    flash(f"Cumulative average: {cumulative_average}", "alert alert-info")

    results_dict = {result.subject_id: result for result in results}
    return results, grand_total, average, cumulative_average, results_dict
