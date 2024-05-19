from application import app, db
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, login_user, logout_user, current_user
from .models import Student, User
from .forms import StudentRegistrationForm, LoginForm
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

        try:
            db.session.add(student)
            db.session.commit()
            flash(
                f"Student registered successfully. Username: {username}, Password: {temporary_password}",
                "alert alert-success",
            )

            # Upload student username and password to AdminUser database
            student_user = User(username=student.username)
            student_user.set_password(student.password)  # Hash the password
            db.session.add(student_user)
            db.session.commit()
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

@app.route("/admin/results", methods=["GET", "POST"])
@login_required
def manage_results():
    if not current_user.is_admin:
        return redirect(url_for("login"))
    # Add logic to handle result management (e.g., uploading results, viewing all student results)
    return render_template("admin/manage_results.html", title="Manage Results")


@app.route("/results")
@login_required
def student_result_portal():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))
    # Add logic to fetch and display the student's results
    return render_template(
        "view_results.html", title="View Results", student=current_user
    )
