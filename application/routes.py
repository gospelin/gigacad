from application import app, db
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, login_user, logout_user, current_user
from .models import Student, Result, StudentLogin
from .forms import StudentRegistrationForm, RegistrationForm, StudentLoginForm, AdminLoginForm
import random
import string


def generate_unique_username(first_name, last_name):
    username = f"{first_name.lower()}.{last_name.lower()}"
    existing_user = Student.query.filter_by(username=username).first()
    if existing_user:
        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=4)
        )
        username = f"{username}{random_suffix}"
    return username


@app.route('/')
@app.route('/index')
@app.route('/home')
def index():
    return render_template('index.html', school_name="Aunty Anne's Int'l School")

@app.route('/about_us')
def about_us():
    return render_template('about_us.html', school_name="Aunty Anne's Int'l School")


@app.route("/register/student", methods=["GET", "POST"])
def student_registration():
    form = StudentRegistrationForm()
    if form.validate_on_submit():
        username = generate_unique_username(form.first_name.data, form.last_name.data)
        temporary_password = "".join(
            random.choices(string.ascii_letters + string.digits, k=8)
        )
        student = Student(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
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
        )
        student.set_password(temporary_password)
        db.session.add(student)
        db.session.commit()
        flash(
            f"Student registered successfully. Username: {username}, Password: {temporary_password}",
            "alert alert-success",
        )
        return redirect(url_for("index"))
    return render_template(
        "student_registration.html", form=form, school_name="Aunty Anne's Int'l School"
    )


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access restricted to admins only.", "alert alert-danger")
        return redirect(url_for("index"))
    # Example logic to fetch and display dashboard data
    try:
        # Get total number of students
        total_students = Student.query.count()

        # Get pending registrations count
        pending_students_count = Student.query.filter_by(approved=False).count()

        # Get approved registrations count
        approved_students_count = Student.query.filter_by(approved=True).count()

        # Get recent registrations
        recent_registrations = (
            Student.query.order_by(Student.date_registered.desc()).limit(5).all()
        )

        return render_template(
            "/admin/admin_templates/admin_dashboard.html",
            total_students=total_students,
            pending_students_count=pending_students_count,
            approved_students_count=approved_students_count,
            recent_registrations=recent_registrations,
        )
    except Exception as e:
        flash(f"Error fetching dashboard data: {str(e)}", "error")
        return render_template("/admin/admin_templates/admin_dashboard.html")


@app.route("/admin/pending_registrations")
def pending_registrations():
    pending_students = Student.query.filter_by(approved=False).all()
    return render_template(
        "admin/admin_templates/pending_registration.html",
        students=pending_students,
    )


@app.route("/admin/approve_registration/<int:student_id>", methods=["POST"])
def approve_registration(student_id):
    student = Student.query.get_or_404(student_id)
    student.approved = True
    db.session.commit()
    flash("Registration approved successfully", "alert alert-success")
    return redirect(url_for("pending_registrations"))


@app.route("/admin/view_students")
def view_students():
    all_students = Student.query.all()
    return render_template("admin/admin_templates/view_students.html", students=all_students)


@app.route("/admin/edit_student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    form = StudentRegistrationForm(obj=student)
    if form.validate_on_submit():
        form.populate_obj(student)
        db.session.commit()
        flash("Student details updated successfully", "alert alert-success")
        return redirect(url_for("view_students"))
    return render_template(
        "admin/admin_templates/edit_students.html", form=form, student=student
    )


@app.route("/admin/delete_student/<int:student_id>", methods=["GET", "POST"])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash("Student deleted successfully", "alert alert-success")
    return redirect(url_for("view_students"))


# @app.route("/login", methods=["GET", "POST"])
# def login():
#    form = LoginForm()
#    if form.validate_on_submit():
#        user = User.query.filter_by(username=form.username.data).first()
#        if user and user.check_password(form.password.data):
#            login_user(user)
#            flash("Logged in successfully!", "success")
#            return redirect(url_for("index"))
#        else:
#            flash("Invalid username or password.", "alert alert-danger")
#    return render_template(
#        "login.html", form=form, school_name="Aunty Anne's Int'l School"
#    )


@app.route("/admin/add_student_to_class", methods=["POST"])
@login_required
def add_student_to_class():
    if not current_user.is_admin():
        flash("Access restricted to admins only.", "alert alert-danger")
        return redirect(url_for("index"))

    student_id = request.form.get("student_id")
    entry_class = request.form.get("entry_class")
    student = Student.query.get_or_404(student_id)
    student.entry_class = entry_class
    db.session.commit()
    flash("Student added to class successfully", "alert alert-success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/remove_student_from_class/<int:student_id>", methods=["POST"])
@login_required
def remove_student_from_class(student_id):
    if not current_user.is_admin():
        flash("Access restricted to admins only.", "alert alert-danger")
        return redirect(url_for("index"))

    student = Student.query.get_or_404(student_id)
    student.entry_class = None
    db.session.commit()
    flash("Student removed from class successfully", "alert alert-success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/manage_results/<int:student_id>", methods=["GET", "POST"])
@login_required
def manage_results(student_id):
    if not current_user.is_admin():
        flash("Access restricted to admins only.", "alert alert-danger")
        return redirect(url_for("index"))

    student = Student.query.get_or_404(student_id)
    if request.method == "POST":
        class_assessment = request.form.get("class_assessment")
        summative_test = request.form.get("summative_test")
        exam = request.form.get("exam")
        total = float(class_assessment) + float(summative_test) + float(exam)

        if student.results:
            result = student.results[0]
            result.class_assessment = class_assessment
            result.summative_test = summative_test
            result.exam = exam
            result.total = total
        else:
            result = Result(
                student_id=student.id,
                class_assessment=class_assessment,
                summative_test=summative_test,
                exam=exam,
                total=total,
            )
            db.session.add(result)

        db.session.commit()
        flash("Result updated successfully", "alert alert-success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/manage_results.html", student=student)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "alert alert-success")
    return redirect(url_for("index"))


@app.route("/result_portal", methods=["GET"])
@login_required
def result_portal():
    if not isinstance(current_user, Student):
        flash("Access restricted to students only.", "alert alert-danger")
        return redirect(url_for("index"))
    student = Student.query.get(current_user.id)
    return render_template("result_portal.html", student=student)


@app.route("/update_result", methods=["POST"])
@login_required
def update_result():
    data = request.json
    student_id = data.get("student_id")
    math_score = data.get("math_score")
    science_score = data.get("science_score")

    student = Student.query.get(student_id)
    if student:
        if student.results:
            # Update existing result
            result = student.results
            result.math_score = math_score
            result.science_score = science_score
        else:
            # Create new result if it doesn't exist
            result = Result(
                student_id=student_id,
                math_score=math_score,
                science_score=science_score,
            )
            db.session.add(result)
        db.session.commit()
        return jsonify({"message": "Result updated successfully"}), 200
    else:
        return jsonify({"message": "Student not found"}), 404


@app.errorhandler(401)
def unauthorized(e):
    flash("Unauthorized access. Please log in.", "danger")
    return redirect(url_for("login"))


#@app.route("/register", methods=["GET", "POST"])
#def register():
#    form = RegistrationForm()
#    if form.validate_on_submit():
#        user = User(username=form.username.data)
#        user.set_password(form.password.data)
#        db.session.add(user)
#        db.session.commit()
#        flash("Registration successful! You can now log in.", "alert alert-success")
#        return redirect(url_for("login"))
#    return render_template(
#        "register.html", form=form, school_name="Aunty Anne's Int'l School"
#    )


@app.route("/login/student", methods=["GET", "POST"])
def student_login():
    form = StudentLoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Find the student by username
        student = StudentLogin.query.filter_by(username=username).first()

        # If student is found and password is correct, login the student
        if student and student.check_password(password):
            login_user(student)  # Log in the student
            flash("Logged in successfully!", "success")
            return redirect(url_for("student_result_portal"))
        else:
            flash("Invalid username or password.", "alert alert-danger")

    return render_template("student_login.html", form=form)


@app.route("/result_portal/admin", methods=["GET"])
@login_required
def admin_result_portal():
    if not current_user.is_admin:
        flash("Access restricted to admins only.", "alert alert-danger")
        return redirect(url_for("index"))
    # Retrieve and display all students' results
    all_students = Student.query.all()
    return render_template("admin_result_portal.html", students=all_students)
