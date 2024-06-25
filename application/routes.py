from . import app, db
import logging
from flask_wtf.csrf import CSRFError
from flask import (
    abort,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    make_response,
)
from flask_login import login_required, login_user, logout_user, current_user
from .models import Student, User, Subject, Result
from collections import defaultdict
from .forms import (
    StudentRegistrationForm,
    LoginForm,
    ResultForm,
    EditStudentForm,
    SubjectForm,
    DeleteForm,
    ApproveForm,
)
from .helpers import (
    generate_unique_username,
    calculate_grade,
    get_remark,
    calculate_grand_total,
    get_last_term,
    calculate_average,
    calculate_cumulative_average,
    random,
    string,
)
#from weasyprint import HTML


@app.route("/")
@app.route("/index")
@app.route("/home")
def index():
    return render_template(
        "index.html", title="Home", school_name="Aunty Anne's Int'l School"
    )


@app.route("/about_us")
def about_us():
    return render_template(
        "about_us.html", title="About Us", school_name="Aunty Anne's Int'l School"
    )


""" Manage Student Section

This section includes functionalities like:

Register Student - Add a new student to the database and generate username and password
Login - Authenticate a user and log them in
Logout - Log a user out
Approve Students - Approve or deactivate students
Manage Classes - View all students by class
Manage Results - Add, edit, and delete student results
View Results - View student results
Manage Students - View all students
Add Students - Add a new student
Edit Student - Edit a student's details
Delete Student - Delete a student
Manage Subjects - Add, edit, and delete subjects
Regenerate Password - Generate a new password for a student

"""


# @app.route("/register/student", methods=["GET", "POST"])
# def student_registration():
#     form = StudentRegistrationForm()
#     if form.validate_on_submit():
#         username = generate_unique_username(form.first_name.data, form.last_name.data)
#         temporary_password = "".join(
#             random.choices(string.ascii_letters + string.digits, k=8)
#         )
#         student = Student(
#             first_name=form.first_name.data,
#             last_name=form.last_name.data,
#             middle_name = form.middle_name.data,
#             gender=form.gender.data,
#             date_of_birth=form.date_of_birth.data,
#             parent_name=form.parent_name.data,
#             parent_phone_number=form.parent_phone_number.data,
#             address=form.address.data,
#             parent_occupation=form.parent_occupation.data,
#             entry_class=form.entry_class.data,
#             previous_class=form.previous_class.data,
#             state_of_origin=form.state_of_origin.data,
#             local_government_area=form.local_government_area.data,
#             religion=form.religion.data,
#             username=username,
#             password=temporary_password,
#         )
#         user = User(username=student.username, is_admin=False)
#         user.set_password(student.password)
#         student.user = user
#         try:
#             db.session.add(student)
#             db.session.add(user)
#             db.session.commit()
#             flash(
#                 f"Student registered successfully. Username: {username}, Password: {temporary_password}",
#                 "alert alert-success",
#             )
#         except Exception as e:
#             db.session.rollback()
#             flash(f"An error occurred. Please try again later. {e}",  "alert alert-danger")
#         return redirect(url_for("student_registration"))
#     return render_template(
#         "student_registration.html",
#         title="Register",
#         form=form,
#         school_name="Aunty Anne's Int'l School",
#     )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/register/student", methods=["GET", "POST"])
def student_registration():
    form = StudentRegistrationForm()
    try:
        if form.validate_on_submit():
            username = generate_unique_username(
                form.first_name.data, form.last_name.data
            )
            temporary_password = "".join(
                random.choices(string.ascii_letters + string.digits, k=8)
            )

            student = Student(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                middle_name=form.middle_name.data,
                gender=form.gender.data,
                date_of_birth=form.date_of_birth.data,
                parent_name=form.parent_name.data,
                parent_phone_number=form.parent_phone_number.data,
                address=form.address.data,
                parent_occupation=form.parent_occupation.data,
                entry_class=form.entry_class.data,
                previous_class=form.previous_class.data,
                state_of_origin=form.state_of_origin.data,
                local_government_area=form.local_government_area.data,
                religion=form.religion.data,
                username=username,
                password=temporary_password,
            )

            user = User(username=student.username, is_admin=False)
            user.set_password(temporary_password)
            student.user = user

            db.session.add(student)
            db.session.add(user)
            db.session.commit()

            logger.info(f"Student registered successfully: {username}")
            flash(
                f"Student registered successfully. Username: {username}, Password: {temporary_password}",
                "alert alert-success",
            )
            return redirect(url_for("student_registration"))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error registering student: {e}")
        flash("An error occurred. Please try again later.", "alert alert-danger")

    return render_template(
        "student_registration.html",
        title="Register",
        form=form,
        school_name="Aunty Anne's Int'l School",
    )


# CSRF error handler
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    logger.warning(f"CSRF error: {e.description}")
    flash("The form submission has expired. Please try again.", "alert alert-danger")
    return redirect(url_for("student_registration"))


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if user.student and not user.student.approved:
                flash(
                    "Your account is not approved yet. Please contact admin.",
                    "alert alert-danger",
                )
                return redirect(url_for("login"))
            login_user(user)
            next_page = request.args.get("next")
            return (
                redirect(next_page)
                if next_page
                else redirect(url_for("student_portal"))
            )
        else:
            flash(
                "Login Unsuccessful. Please check username and password",
                "alert alert-danger",
            )
    return render_template("login.html", title="Login", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("login"))

    # total_students = Student.query.count()

    total_students = 234
    total_teachers = 30
    total_parents = 105
    total_classes = 13

    # Example data for charts (replace with actual dynamic data)
    student_enrollment_data = [12, 19, 3, 5, 2]  # Example data
    teacher_distribution_data = [3, 5, 2, 4, 6]  # Example data

    return render_template(
        "/admin/index.html",
        total_students=total_students,
        total_teachers=total_teachers,
        total_parents=total_parents,
        total_classes=total_classes,
        student_enrollment_data=student_enrollment_data,
        teacher_distribution_data=teacher_distribution_data,
    )


@app.route("/admin/approve_students", methods=["GET", "POST"])
@login_required
def approve_students():
    if not current_user.is_admin:
        abort(403)  # Forbidden access

    approve_form = ApproveForm()
    deactivate_form = ApproveForm()
    regenerate_form = ApproveForm()

    students = Student.query.all()
    students = Student.query.all()
    students_by_class = defaultdict(list)
    for student in students:
        students_by_class[student.entry_class].append(student)

    return render_template(
        "admin/approve_students.html",
        students_by_class=students_by_class,
        approve_form=approve_form,
        deactivate_form=deactivate_form,
        regenerate_form=regenerate_form,
    )


@app.route("/admin/approve_student/<int:student_id>", methods=["POST"])
@login_required
def approve_student(student_id):
    if not current_user.is_admin:
        abort(403)  # Forbidden access

    form = ApproveForm()

    if form.validate_on_submit():
        student = Student.query.get_or_404(student_id)
        student.approved = True
        db.session.commit()
        flash(
            f"Student {student.first_name} {student.last_name} has been approved.",
            "alert alert-success",
        )
    else:
        flash("An error occurred. Please try again.", "alert alert-danger")
    return redirect(url_for("approve_students"))


@app.route("/admin/deactivate_student/<int:student_id>", methods=["POST"])
@login_required
def deactivate_student(student_id):
    if not current_user.is_admin:
        abort(403)  # Forbidden access

    form = ApproveForm()
    if form.validate_on_submit():
        student = Student.query.get_or_404(student_id)
        student.approved = False
        db.session.commit()
        flash(
            f"Student {student.first_name} {student.last_name} has been deactivated.",
            "alert alert-success",
        )
    else:
        flash("An error occurred. Please try again.", "alert alert-danger")
    return redirect(url_for("approve_students"))


@app.route("/admin/regenerate_password/<int:student_id>", methods=["POST"])
@login_required
def regenerate_password(student_id):
    if not current_user.is_admin:
        abort(403)  # Forbidden access

    form = ApproveForm()
    student = Student.query.get_or_404(student_id)
    if form.validate_on_submit() and student:

        # Generate a new temporary password
        new_temporary_password = "".join(
            random.choices(string.ascii_letters + string.digits, k=8)
        )
        # Update student's password
        student.password = new_temporary_password

        # Update user's password
        student.user.set_password(new_temporary_password)
        db.session.commit()
        flash(
            f"New password generated for {student.first_name} {student.last_name}: {new_temporary_password}",
            "alert alert-success",
        )
    else:
        flash("Student not found.", "alert alert-danger")
    return redirect(url_for("approve_students"))


@app.route("/admin/students_by_class/<string:entry_class>")
@login_required
def students_by_class(entry_class):
    students = Student.query.filter_by(entry_class=entry_class).all()
    form = DeleteForm()  # Create an instance of the DeleteForm
    return render_template(
        "admin/students_by_class.html",
        students=students,
        entry_class=entry_class,
        form=form,
    )


@app.route("/admin/manage_classes")
@login_required
def manage_classes():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("login"))
    students = Student.query.all()
    return render_template("admin/classes.html", students=students)


@app.route("/select_term_session/<int:student_id>", methods=["GET", "POST"])
@login_required
def select_term_session(student_id):
    student = Student.query.get_or_404(student_id)
    form = ResultForm()
    if form.validate_on_submit():
        term = form.term.data
        session = form.session.data
        return redirect(
            url_for("manage_results", student_id=student.id, term=term, session=session)
        )
    return render_template("admin/select_term_session.html", form=form, student=student)


@app.route("/manage_results/<int:student_id>", methods=["GET", "POST"])
@login_required
def manage_results(student_id):
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("login"))

    student = Student.query.get_or_404(student_id)
    term = request.args.get("term")
    session = request.args.get("session")

    if not term or not session:
        return redirect(url_for("select_term_session", student_id=student.id))

    form = ResultForm(term=term, session=session)
    if "Nursery" in student.entry_class:
        subjects = Subject.query.filter_by(section="Nursery").all()
    elif "Basic" in student.entry_class:
        subjects = Subject.query.filter_by(section="Basic").all()
    else:
        subjects = Subject.query.filter_by(section="Secondary").all()

    if form.validate_on_submit():
        next_term_begins = form.next_term_begins.data
        last_term_average = form.last_term_average.data
        position = form.position.data

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
                    next_term_begins=next_term_begins,
                    last_term_average=last_term_average,
                    position=position,
                )
                db.session.add(result)
            else:
                result.class_assessment = class_assessment
                result.summative_test = summative_test
                result.exam = exam
                result.total = total
                result.grade = grade
                result.remark = remark
                result.next_term_begins = next_term_begins
                result.last_term_average = last_term_average
                result.position = position
        db.session.commit()
        flash("Results updated successfully", "alert alert-success")
        return redirect(
            url_for("manage_results", student_id=student.id, term=term, session=session)
        )

    results = Result.query.filter_by(
        student_id=student.id, term=term, session=session
    ).all()
    grand_total = calculate_grand_total(results)
    average = calculate_average(results)
    average = round(average, 1)

    # Calculate last term's average
    last_term = get_last_term(term)
    last_term_results = Result.query.filter_by(
        student_id=student.id, term=last_term, session=session
    ).all()
    last_term_average = calculate_average(last_term_results) if last_term_results else 0
    last_term_average = round(last_term_average, 1)

    # Add last_term_average to each result in results for cumulative calculation
    for res in results:
        res.last_term_average = last_term_average

    cumulative_average = calculate_cumulative_average(results, average)
    cumulative_average = round(cumulative_average, 1)

    results_dict = {result.subject_id: result for result in results}

    return render_template(
        "admin/manage_results.html",
        student=student,
        subjects=subjects,
        results=results,
        grand_total=grand_total,
        average=average,
        cumulative_average=cumulative_average,
        results_dict=results_dict,
        form=form,
        selected_term=term,
        selected_session=session,
    )


@app.route("/admin/delete_result/<int:result_id>", methods=["POST"])
@login_required
def delete_result(result_id):
    form = DeleteForm()
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("login"))

    result = Result.query.get_or_404(result_id)

    student_id = result.student_id
    term = result.term
    session = result.session

    try:
        db.session.delete(result)
        db.session.commit()
        flash("Result deleted successfully!", "alert alert-success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting result: {e}", "alert alert-danger")

    return redirect(
        url_for(
            "manage_results",
            form=form,
            student_id=student_id,
            term=term,
            session=session,
        )
    )


@app.route("/student_portal")
@login_required
def student_portal():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))

    student = Student.query.filter_by(user_id=current_user.id).first()

    # if current_user.id != student.user_id and not current_user.is_admin:
    #     flash('You are not authorized to view this profile.', 'alert alert-danger')
    #     return redirect(url_for('index'))

    if not student:
        flash("Student not found", "alert alert-danger")
        return redirect(url_for("login"))

    return render_template(
        "student_portal.html", student_id=student.id, student=student
    )


@app.route("/student/<int:student_id>/profile")
@login_required
def student_profile(student_id):
    # Fetch the student details from the database
    student = Student.query.get_or_404(student_id)

    # Ensure the logged-in user is authorized to view this profile
    if current_user.id != student.user_id and not current_user.is_admin:
        flash("You are not authorized to view this profile.", "alert alert-danger")
        return redirect(url_for("index"))

    return render_template("student_profile.html", student=student)


@app.route("/select_results/<int:student_id>", methods=["GET", "POST"])
@login_required
def select_results(student_id):
    student = Student.query.get_or_404(student_id)
    form = ResultForm()
    if form.validate_on_submit():
        term = form.term.data
        session = form.session.data
        return redirect(
            url_for("view_results", student_id=student.id, term=term, session=session)
        )
    return render_template("select_results.html", student=student, form=form)


@app.route("/view_results/<int:student_id>", methods=["GET", "POST"])
@login_required
def view_results(student_id):
    student = Student.query.get_or_404(student_id)

    term = request.args.get("term")
    session = request.args.get("session")

    if not term or not session:
        return redirect(url_for("select_term_session", student_id=student.id))

    results = Result.query.filter_by(
        student_id=student.id, term=term, session=session
    ).all()
    if not results:
        flash("No results found for this term or session", "alert alert-info")
        return redirect(url_for("select_results", student_id=student.id))

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
    last_term_average = calculate_average(last_term_results) if last_term_results else 0
    last_term_average = round(last_term_average, 1)

    # Add last_term_average to each result in results for cumulative calculation
    for res in results:
        res.last_term_average = last_term_average

    cumulative_average = calculate_cumulative_average(results, average)
    cumulative_average = round(cumulative_average, 1)

    next_term_begins = results[0].next_term_begins if results else None
    position = results[0].position if results else None

    return render_template(
        "view_results.html",
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


#import os


#@app.route("/download_results_pdf/<int:student_id>")
#@login_required
#def download_results_pdf(student_id):
#    student = Student.query.get_or_404(student_id)
#    term = request.args.get("term")
#    session = request.args.get("session")

#    results = Result.query.filter_by(
#        student_id=student.id, term=term, session=session
#    ).all()
#    if not results:
#        flash("No results found for this term or session", "alert alert-info")
#        return redirect(url_for("select_results", student_id=student.id))

#    grand_total = {
#        "class_assessment": sum(result.class_assessment for result in results),
#        "summative_test": sum(result.summative_test for result in results),
#        "exam": sum(result.exam for result in results),
#        "total": sum(result.total for result in results),
#    }

#    average = grand_total["total"] / len(results) if results else 0
#    average = round(average, 1)

#    last_term = get_last_term(term)
#    last_term_results = Result.query.filter_by(
#        student_id=student.id, term=last_term, session=session
#    ).all()
#    last_term_average = calculate_average(last_term_results) if last_term_results else 0

#    for res in results:
#        res.last_term_average = last_term_average

#    cumulative_average = calculate_cumulative_average(results, average)

#    next_term_begins = results[0].next_term_begins if results else None
#    position = results[0].position if results else None

#    # Get the absolute path to the static directory
#    static_path = os.path.join(app.root_path, "static", "images", "MY_SCHOOL_LOGO.png")
#    static_url = f"file://{static_path}"

#    rendered = render_template(
#        "pdf_results.html",
#        title=f"{student.first_name}_{student.last_name}_{term}_{session}_Result",
#        student=student,
#        results=results,
#        term=term,
#        session=session,
#        grand_total=grand_total,
#        school_name="Aunty Anne's Int'l School",
#        average=average,
#        cumulative_average=cumulative_average,
#        next_term_begins=next_term_begins,
#        last_term_average=last_term_average,
#        position=position,
#        static_url=static_url,
#    )

#    pdf = HTML(string=rendered).write_pdf()

#    response = make_response(pdf)
#    response.headers["Content-Type"] = "application/pdf"
#    response.headers["Content-Disposition"] = (
#        f"inline; filename={student.first_name}_{student.last_name}_{term}_{session}_Result.pdf"
#    )
#    return response


@app.route("/admin/manage_students", methods=["GET", "POST"])
@login_required
def manage_students():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("login"))
    students = Student.query.all()
    return render_template("admin/student_admin.html", students=students)


@app.route("/admin/students", methods=["GET", "POST"])
@login_required
def add_students():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("login"))

    form = StudentRegistrationForm()
    if form.validate_on_submit():
        username = generate_unique_username(form.first_name.data, form.last_name.data)
        temporary_password = "".join(
            random.choices(string.ascii_letters + string.digits, k=8)
        )
        student = Student(
            first_name=form.first_name.data,
            middle_name=form.middle_name.data,
            last_name=form.last_name.data,
            gender=form.gender.data,
            date_of_birth=form.date_of_birth.data,
            entry_class=form.entry_class.data,
            username=username,
            password=temporary_password,
        )
        user = User(username=student.username, is_admin=False)
        user.set_password(student.password)
        student.user = user
        try:
            db.session.add(student)
            db.session.add(user)
            db.session.commit()
            flash(
                f"Student registered successfully. Username: {username}, Password: {temporary_password}",
                "alert alert-success",
            )
        except Exception as e:
            db.session.rollback()
            flash("An error occurred. Please try again later.", e, "alert alert-danger")
        return redirect(url_for("add_students"))

    students = Student.query.all()
    return render_template("admin/add_student.html", form=form, students=students)


@app.route("/admin/edit_student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    form = EditStudentForm()

    if form.validate_on_submit():
        student.username = form.username.data
        student.entry_class = form.entry_class.data
        student.first_name = form.first_name.data
        student.last_name = form.last_name.data
        student.middle_name = form.middle_name.data
        # Update other fields as needed
        db.session.commit()
        flash("Student updated successfully!", "alert alert-success")
        return redirect(url_for("students_by_class", entry_class=student.entry_class))
    elif request.method == "GET":
        form.username.data = student.username
        form.entry_class.data = student.entry_class
        form.first_name.data = student.first_name
        form.last_name.data = student.last_name
        form.middle_name.data = student.middle_name
        # Populate other fields as necessary
        db.session.commit()
        flash("Student updated successfully!", "alert alert-success")

    return render_template("admin/edit_student.html", form=form, student=student)


@app.route("/admin/delete_student/<int:student_id>", methods=["GET", "POST"])
def delete_student(student_id):
    form = DeleteForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated or not current_user.is_admin:
            return redirect(url_for("login"))

        student = Student.query.get_or_404(student_id)

        try:
            # Manually delete related results
            results = Result.query.filter_by(student_id=student.id).all()
            for result in results:
                db.session.delete(result)

            db.session.delete(student)
            db.session.commit()
            flash(
                "Student and associated results deleted successfully!",
                "alert alert-success",
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting student: {e}", "alert alert-danger")

    return redirect(url_for("students_by_class", entry_class=student.entry_class))


@app.route("/admin/manage_subjects", methods=["GET", "POST"])
@login_required
def manage_subjects():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("login"))

    form = SubjectForm()
    if form.validate_on_submit():
        for section in form.section.data:
            # Check if the subject already exists for the given section
            existing_subject = Subject.query.filter_by(
                name=form.name.data, section=section
            ).first()
            if existing_subject is None:
                subject = Subject(name=form.name.data, section=section)
                db.session.add(subject)
        db.session.commit()
        flash("Subject(s) added successfully!", "alert alert-success")
        return redirect(url_for("manage_subjects"))

    subjects = Subject.query.order_by(Subject.section).all()
    subjects_by_section = {}
    for subject in subjects:
        if subject.section not in subjects_by_section:
            subjects_by_section[subject.section] = []
        subjects_by_section[subject.section].append(subject)

    delete_form = DeleteForm()
    return render_template(
        "admin/subject_admin.html",
        form=form,
        subjects_by_section=subjects_by_section,
        delete_form=delete_form,
    )


@app.route("/admin/edit_subject/<int:subject_id>", methods=["GET", "POST"])
def edit_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    form = SubjectForm(obj=subject)
    if form.validate_on_submit():
        subject.name = form.name.data
        db.session.commit()
        flash("Subject updated successfully!", "alert alert-success")
        return redirect(url_for("manage_subjects"))
    return render_template("admin/edit_subject.html", form=form, subject=subject)


@app.route("/admin/delete_subject/<int:subject_id>", methods=["POST"])
def delete_subject(subject_id):
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("login"))

    form = DeleteForm()  # Instantiate the DeleteForm

    if form.validate_on_submit():
        try:
            # Find the subject
            subject = Subject.query.get_or_404(subject_id)

            # Delete all scores associated with the subject
            Result.query.filter_by(subject_id=subject_id).delete()

            # Delete the subject
            db.session.delete(subject)
            db.session.commit()

            flash(
                "Subject and associated scores deleted successfully!",
                "alert alert-success",
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting subject: {e}", "alert alert-danger")

    return redirect(url_for("manage_subjects"))
