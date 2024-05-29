from application import app, db
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, login_user, logout_user, current_user
from .models import Student, User, Subject, Score
from .forms import StudentRegistrationForm, LoginForm, ScoreForm
import random, string


def generate_unique_username(first_name, last_name):
    username = f"{first_name.lower()}.{last_name.lower()}"
    print(f"Generated username: {username}")  # Debugging statement
    existing_user = Student.query.filter_by(username=username).first()
    print(f"Existing user: {existing_user}")  # Debugging statement
    if existing_user:
        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=4)
        )
        username = f"{username}{random_suffix}"
    return username

# This is for regular navigation links

@app.route('/')
@app.route('/index')
@app.route('/home')
def index():
    return render_template('index.html', title="Home", school_name="Aunty Anne's Int'l School")

@app.route('/about_us')
def about_us():
    return render_template('about_us.html', title="About Us", school_name="Aunty Anne's Int'l School")

# Student Registration routes


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
            flash(f"Error: {str(e)}", "alert alert-danger")

        return redirect(url_for("index"))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(
                    f"Error in the {getattr(form, field).label.text} field - {error}",
                    "alert alert-danger",
                )

    return render_template(
        "student_registration.html",
        title="Register",
        form=form,
        school_name="Aunty Anne's Int'l School",
    )


# Login and User Authentication routes

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("index"))
        else:
            flash("Login Unsuccessful. Please check username and password", "danger")
    return render_template("login.html", title="Login", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# Protect admin routes
@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for("login"))
    return render_template("/admin/index.html")

### Result Management Routes ###


@app.route("/admin/manage_results", methods=["GET", "POST"])
@login_required
def manage_results():
    form = ScoreForm()
    form.student_id.choices = [
        (student.id, f"{student.first_name} {student.last_name}")
        for student in Student.query.all()
    ]
    form.subject_id.choices = [
        (subject.id, subject.name) for subject in Subject.query.all()
    ]

    if form.validate_on_submit():
        # Get form data
        student_id = form.student_id.data
        subject_id = form.subject_id.data
        class_assessment = form.class_assessment.data
        summative_test = form.summative_test.data
        exam = form.exam.data
        term = form.term.data
        session = form.session.data

        # Check if score already exists for the student and subject
        score = Score.query.filter_by(
            student_id=student_id, subject_id=subject_id
        ).first()
        if score:
            # Update existing score
            score.class_assessment = class_assessment
            score.summative_test = summative_test
            score.exam = exam
            score.term = term
            score.session = session
        else:
            # Create new score entry
            score = Score(
                student_id=student_id,
                subject_id=subject_id,
                class_assessment=class_assessment,
                summative_test=summative_test,
                exam=exam,
                term=term,
                session=session,
            )

        score.calculate_total()  # Assuming you have a method to calculate total in your Score model
        db.session.add(score)
        db.session.commit()
        flash("Score saved successfully!", "success")
        return redirect(url_for("manage_results"))

    results = Score.query.all()
    return render_template("admin/manage_results.html", form=form, results=results)


@app.route("/results")
@login_required
def student_result_portal():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))

    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash("Student not found", "alert alert-danger")
        return redirect(url_for("index"))

    results = Score.query.filter_by(student_id=student.id).all()
    if not results:
        flash("No results found for this student", "alert alert-info")
        return redirect(url_for("index"))

    return render_template(
        "view_results.html", title="View Results", student=student, results=results, 
        school_name="Aunty Anne's Int'l School"
    )
