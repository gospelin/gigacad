# from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from application import db
from flask_login import UserMixin
from datetime import datetime


class Student(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    parent_name = db.Column(db.String(70), nullable=True)
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

    results = db.relationship("Result", backref="student", lazy=True)

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
    name = db.Column(db.String(100), nullable=False)
    section = db.Column(db.String(20), nullable=False)
    results = db.relationship("Result", backref="subject", lazy=True)

    __table_args__ = (db.UniqueConstraint("name", "section", name="_name_section_uc"),)

    def __repr__(self):
        return f"<Subject {self.name}>"


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    term = db.Column(db.String(20), nullable=False)
    session = db.Column(db.String(20), nullable=False)
    class_assessment = db.Column(db.Integer, nullable=True, default=0)
    summative_test = db.Column(db.Integer, nullable=True, default=0)
    exam = db.Column(db.Integer, nullable=True, default=0)
    total = db.Column(db.Integer, nullable=False, default=0)
    grade = db.Column(db.String(5))
    created_at = db.Column(db.DateTime, default=datetime.now())
    remark = db.Column(db.String(100))
    next_term_begins = db.Column(db.String(100), nullable=True)
    last_term_average = db.Column(db.Float, nullable=True, default=0.0)
    position = db.Column(db.String(10), nullable=True)

    @property
    def class_assessment_value(self):
        return self.class_assessment or 0

    @property
    def summative_test_value(self):
        return self.summative_test or 0

    @property
    def exam_value(self):
        return self.exam or 0

    @property
    def total_value(self):
        return self.class_assessment_value + self.summative_test_value + self.exam_value
