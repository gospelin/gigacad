from application import app, db
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, login_user, logout_user
from .models import Student, User, Result
from .forms import StudentRegistrationForm, RegistrationForm, LoginForm


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
            religion=form.religion.data
        )
        db.session.add(student)
        db.session.commit()
        flash("Student registration submitted. Pending admin approval.", "alert alert-success")
        return redirect(url_for("index"))  # Redirect to home or confirmation page
    return render_template(
        "student_registration.html", form=form, school_name="Aunty Anne's Int'l School"
    )


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
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


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "alert alert-danger")
    return render_template(
        "login.html", form=form, school_name="Aunty Anne's Int'l School"
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "alert alert-success")
    return redirect(url_for("index"))


@app.route("/result_portal", methods=["GET"])
@login_required
def result_portal():
    students = Student.query.all()
    return render_template("result_portal.html", students=students)


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


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! You can now log in.", "alert alert-success")
        return redirect(url_for("login"))
    return render_template(
        "register.html", form=form, school_name="Aunty Anne's Int'l School"
    )
