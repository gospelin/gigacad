# from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from application import db
from flask_login import UserMixin
from datetime import datetime


class Student(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    parent_phone_number = db.Column(db.String(11), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    parent_occupation = db.Column(db.String(100), nullable=True)
    entry_class = db.Column(db.String(50), nullable=False)
    previous_class = db.Column(db.String(50))
    state_of_origin = db.Column(db.String(50), nullable=True)
    local_government_area = db.Column(db.String(50), nullable=True)
    religion = db.Column(db.String(50), nullable=True)
    date_registered = db.Column(db.DateTime, server_default=db.func.now())
    approved = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    current_session = db.Column(db.String(50))
    current_term = db.Column(db.String(10))

    scores = db.relationship("Score", backref="student", lazy=True)

    def __repr__(self):
        return f"<Student {self.first_name} {self.last_name}>"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    student = db.relationship("Student", backref="user", uselist=False)

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    scores = db.relationship("Score", backref="subject", lazy=True)

    def __repr__(self):
        return f"<Subject {self.name}>"


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_assessment = db.Column(db.Integer, nullable=False)
    summative_test = db.Column(db.Integer, nullable=False)
    exam = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    term = db.Column(db.String(50), nullable=False)
    session = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    grade = db.Column(db.String(2))
    remark = db.Column(db.String(100))

    def calculate_total(self):
        self.total = self.class_assessment + self.summative_test + self.exam

    def get_remark(self):
        if self.total >= 95:
            self.grade = "A+"
            self.remark = "Outstanding"
        elif self.total >= 80:
            self.grade = "A"
            self.remark = "Excellent"
        elif self.total >= 70:
            self.grade = "B+"
            self.remark = "Very Good"
        elif self.total >= 65:
            self.grade = "B"
            self.remark = "Good"
        elif self.total >= 60:
            self.grade = "C+"
            self.remark = "Credit"
        elif self.total >= 50:
            self.grade = "C"
            self.remark = "Credit"
        elif self.total >= 40:
            self.grade = "D"
            self.remark = "Poor"
        elif self.total >= 30:
            self.grade = "E"
            self.remark = "Very Poor"
        else:
            self.grade = "F"
            self.remark = "Fail"

    def __repr__(self):
        return f"<Score {self.student_id} {self.subject_id}>"
