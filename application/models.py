from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from application import db
from flask_login import UserMixin
class Student(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    parent_phone_number = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    parent_occupation = db.Column(db.String(100), nullable=False)
    entry_class = db.Column(db.String(50), nullable=False)
    previous_class = db.Column(db.String(50))
    state_of_origin = db.Column(db.String(50), nullable=False)
    local_government_area = db.Column(db.String(50), nullable=False)
    religion = db.Column(db.String(50), nullable=False)
    date_registered = db.Column(db.DateTime, server_default=db.func.now())
    approved = db.Column(db.Boolean, default=False)
    results = db.relationship("Result", backref="student", lazy=True)

    def __repr__(self):
        return f"<Student {self.first_name} {self.last_name}>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    class_assessment = db.Column(db.Float)
    summative_test = db.Column(db.Float)
    exam = db.Column(db.Float)
    total = db.Column(db.Float)

    def __repr__(self):
        return f"<Result for Student ID: {self.student_id}>"


class StudentLogin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# class User(UserMixin, db.Model):
#    id = db.Column(db.Integer, primary_key=True)
#    username = db.Column(db.String(50), unique=True, nullable=False)
#    password_hash = db.Column(db.String(200), nullable=False)
#    is_active = db.Column(db.Boolean, default=True)

#    def is_admin(self):
#        # Logic to determine if the user is an admin
#        return (
#            self.username == "admin"
#        )  # This is a placeholder. Update with actual admin check logic.

#    def __repr__(self):
#        return f"<User {self.username}>"

#    def set_password(self, password):
#        self.password_hash = generate_password_hash(password)

#    def check_password(self, password):
#        return check_password_hash(self.password_hash, password)
