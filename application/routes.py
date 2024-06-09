from . import app, db
from flask import abort, render_template, redirect, url_for, flash, request
from flask_login import login_required, login_user, logout_user, current_user
from .models import Student, User, Subject, Score
from collections import defaultdict
from .forms import StudentRegistrationForm, LoginForm, ScoreForm, EditStudentForm, \
        SubjectForm, DeleteForm, ApproveForm, ResultForm
import random, string

def generate_unique_username(first_name, last_name):
    username = f"{first_name.strip().lower()}.{last_name.strip().lower()}"
    existing_user = Student.query.filter_by(username=username).first()
    if existing_user:
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        username = f"{username}{random_suffix}"
    return username

@app.route('/')
@app.route('/index')
@app.route('/home')
def index():
    return render_template('index.html', title="Home", school_name="Aunty Anne's Int'l School")

@app.route('/about_us')
def about_us():
    return render_template('about_us.html', title="About Us", school_name="Aunty Anne's Int'l School")


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

@app.route("/register/student", methods=["GET", "POST"])
def student_registration():
    form = StudentRegistrationForm()
    if form.validate_on_submit():
        username = generate_unique_username(form.first_name.data, form.last_name.data)
        temporary_password = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        student = Student(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            gender=form.gender.data,
            date_of_birth=form.date_of_birth.data,
            parent_phone_number=form.parent_phone_number.data,
            address=form.address.data,
            parent_occupation=form.parent_occupation.data,
            entry_class=form.entry_class.data,
            previous_class=form.previous_class.data,
            state_of_origin=form.state_of_origin.data,
            local_government_area=form.local_government_area.data,
            religion=form.religion.data,
            username=username,
            password = temporary_password
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
        return redirect(url_for("student_registration"))
    return render_template(
        "student_registration.html",
        title="Register",
        form=form,
        school_name="Aunty Anne's Int'l School",
    )


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
                else redirect(url_for("student_result_portal"))
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
    return render_template("/admin/index.html")


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
        regenerate_form=regenerate_form
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
        "admin/students_by_class.html", students=students, entry_class=entry_class, form=form
    )


@app.route("/admin/manage_classes")
@login_required
def manage_classes():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("login"))
    students = Student.query.all()
    return render_template("admin/classes.html", students=students)


# @app.route("/admin/manage_results/<int:student_id>", methods=["GET", "POST"])
# @login_required
# def manage_results(student_id):
#    if not current_user.is_authenticated or not current_user.is_admin:
#        return redirect(url_for("login"))

#    student = Student.query.get_or_404(student_id)
#    form = ScoreForm()
#    subjects = Subject.query.all()

#    if request.method == "POST":
#        try:
#            for key, value in request.form.items():
#                if key.startswith("subject_id_new_"):
#                    result_id = key.split("_")[-1]
#                    subject_id = request.form.get(f"subject_id_new_{result_id}")
#                    class_assessment = request.form.get(
#                        f"class_assessment_new_{result_id}"
#                    )
#                    summative_test = request.form.get(f"summative_test_new_{result_id}")
#                    exam = request.form.get(f"exam_new_{result_id}")
#                    total = request.form.get(f"total_new_{result_id}")

#                    if (
#                        subject_id
#                        and class_assessment
#                        and summative_test
#                        and exam
#                        and total
#                    ):
#                        new_score = Score(
#                            student_id=student_id,
#                            subject_id=subject_id,
#                            class_assessment=int(class_assessment),
#                            summative_test=int(summative_test),
#                            exam=int(exam),
#                            term=form.term.data,
#                            session=form.session.data,
#                        )
#                        new_score.calculate_total()
#                        new_score.get_remark()  # Call the get_remark method
#                        db.session.add(new_score)
#                elif key.startswith("subject_id_"):
#                    result_id = key.split("_")[-1]
#                    subject_id = request.form.get(f"subject_id_{result_id}")
#                    class_assessment = request.form.get(f"class_assessment_{result_id}")
#                    summative_test = request.form.get(f"summative_test_{result_id}")
#                    exam = request.form.get(f"exam_{result_id}")
#                    total = request.form.get(f"total_{result_id}")

#                    if (
#                        subject_id
#                        and class_assessment
#                        and summative_test
#                        and exam
#                        and total
#                    ):
#                        score = Score.query.get(result_id)
#                        if score:
#                            score.subject_id = subject_id
#                            score.class_assessment = int(class_assessment)
#                            score.summative_test = int(summative_test)
#                            score.exam = int(exam)
#                            score.total = int(total)
#                            score.calculate_total()
#                            score.get_remark()  # Call the get_remark method

#            db.session.commit()
#            flash("Scores updated successfully!", "alert alert-success")
#        except Exception as e:
#            db.session.rollback()
#            flash(f"Error: {e}", "alert alert-danger")

#        return redirect(url_for("manage_results", student_id=student_id))

#    results = Score.query.filter_by(student_id=student_id).all()
#    grand_total = {
#        "class_assessment": sum(result.class_assessment for result in results),
#        "summative_test": sum(result.summative_test for result in results),
#        "exam": sum(result.exam for result in results),
#        "total": sum(result.total for result in results),
#    }
#    average_total = grand_total["total"] / len(results) if results else 0

#    return render_template(
#        "admin/manage_results.html",
#        form=form,
#        results=results,
#        student=student,
#        subjects=subjects,
#        grand_total=grand_total,
#        average_total=average_total,
#    )


def create_empty_results(student, session, term):
    subjects = Subject.query.all()
    for subject in subjects:
        empty_score = Score(
            student_id=student.id,
            subject_id=subject.id,
            class_assessment=0,
            summative_test=0,
            exam=0,
            term=term,
            session=session,
            total=0,
        )
        db.session.add(empty_score)
    db.session.commit()


@app.route("/admin/manage_results/<int:student_id>", methods=["GET", "POST"])
@login_required
def manage_results(student_id):
    student = Student.query.get_or_404(student_id)
    form = ResultForm()
    subjects = Subject.query.all()

    if request.method == "POST":
        current_session = form.session.data
        current_term = form.term.data

        # Check if session or term changed
        if (
            current_session != student.current_session
            or current_term != student.current_term
        ):
            # Create new empty result entries for the student
            create_empty_results(student, current_session, current_term)
            student.current_session = current_session
            student.current_term = current_term
            db.session.commit()

        # Handle form submission and existing results
        try:
            for key, value in request.form.items():
                if key.startswith("subject_id_new_"):
                    result_id = key.split("_")[-1]
                    subject_id = request.form.get(f"subject_id_new_{result_id}")
                    class_assessment = request.form.get(
                        f"class_assessment_new_{result_id}"
                    )
                    summative_test = request.form.get(f"summative_test_new_{result_id}")
                    exam = request.form.get(f"exam_new_{result_id}")
                    total = request.form.get(f"total_new_{result_id}")

                    if (
                        subject_id
                        and class_assessment
                        and summative_test
                        and exam
                        and total
                    ):
                        new_score = Score(
                            student_id=student_id,
                            subject_id=subject_id,
                            class_assessment=int(class_assessment),
                            summative_test=int(summative_test),
                            exam=int(exam),
                            term=form.term.data,
                            session=form.session.data,
                        )
                        new_score.calculate_total()
                        new_score.get_remark()  # Call the get_remark method
                        db.session.add(new_score)
                elif key.startswith("subject_id_"):
                    result_id = key.split("_")[-1]
                    subject_id = request.form.get(f"subject_id_{result_id}")
                    class_assessment = request.form.get(f"class_assessment_{result_id}")
                    summative_test = request.form.get(f"summative_test_{result_id}")
                    exam = request.form.get(f"exam_{result_id}")
                    total = request.form.get(f"total_{result_id}")

                    if (
                        subject_id
                        and class_assessment
                        and summative_test
                        and exam
                        and total
                    ):
                        score = Score.query.get(result_id)
                        if score:
                            score.subject_id = subject_id
                            score.class_assessment = int(class_assessment)
                            score.summative_test = int(summative_test)
                            score.exam = int(exam)
                            score.total = int(total)
                            score.calculate_total()
                            score.get_remark()  # Call the get_remark method

            db.session.commit()
            flash("Scores updated successfully!", "alert alert-success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "alert alert-danger")

        return redirect(url_for("manage_results", student_id=student_id))

    results = Score.query.filter_by(student_id=student_id).all()
    grand_total = {
        "class_assessment": sum(result.class_assessment for result in results),
        "summative_test": sum(result.summative_test for result in results),
        "exam": sum(result.exam for result in results),
        "total": sum(result.total for result in results),
    }
    average_total = grand_total["total"] / len(results) if results else 0

    return render_template(
        "admin/manage_results.html",
        form=form,
        results=results,
        student=student,
        subjects=subjects,
        grand_total=grand_total,
        average_total=average_total,
    )


@app.route("/admin/delete_result/<int:result_id>", methods=["POST"])
@login_required
def delete_result(result_id):
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("login"))

    result = Score.query.get_or_404(result_id)

    try:
        db.session.delete(result)
        db.session.commit()
        flash("Result deleted successfully!", "alert alert-success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting result: {e}", "alert alert-danger")

    return redirect(url_for("manage_results", student_id=result.student_id))


@app.route("/results")
@login_required
def student_result_portal():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash("Student not found", "alert alert-danger")
        return redirect(url_for("student_result_portal"))

    results = Score.query.filter_by(student_id=student.id).all()
    if not results:
        flash("No results found for this student", "alert alert-info")
        return redirect(url_for("index"))

    grand_total = {
        "class_assessment": sum(result.class_assessment for result in results),
        "summative_test": sum(result.summative_test for result in results),
        "exam": sum(result.exam for result in results),
        "total": sum(result.total for result in results),
    }
    total_obtained = grand_total["total"]
    total_obtainable = len(results) * 100

    average_total = grand_total["total"] / len(results) if results else 0
    average_total = round(average_total, 1)


    return render_template(
        "view_results.html",
        title=f"{student.first_name}_{student.last_name}_Results",
        student=student,
        results=results,
        grand_total=grand_total,
        average_total=average_total,
        school_name="Aunty Anne's Int'l School",
        total_obtained=total_obtained,
        total_obtainable=total_obtainable,
    )

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
        # Update other fields as needed
        db.session.commit()
        flash("Student updated successfully!", "alert alert-success")
        return redirect(url_for("students_by_class", entry_class=student.entry_class))
    elif request.method == "GET":
        form.username.data = student.username
        form.entry_class.data = student.entry_class
        form.first_name = student.first_name
        form.last_name = student.last_name
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
            results = Score.query.filter_by(student_id=student.id).all()
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
        subject = Subject(name=form.name.data)
        db.session.add(subject)
        db.session.commit()
        flash("Subject added successfully!", "alert alert-success")
        return redirect(url_for("manage_subjects"))

    subjects = Subject.query.all()
    delete_form = DeleteForm()  # Create an instance of the DeleteForm
    return render_template(
        "admin/subject_admin.html",
        form=form,
        subjects=subjects,
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
            Score.query.filter_by(subject_id=subject_id).delete()

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
