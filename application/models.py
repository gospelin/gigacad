from werkzeug.security import generate_password_hash, check_password_hash
from application import db
from flask_login import UserMixin
from datetime import datetime


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(20), unique=True, nullable=False)  # e.g., "2023/2024"
    is_current = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Session {self.year}>"

    @staticmethod
    def get_current_session():
        return Session.query.filter_by(is_current=True).first()

    @staticmethod
    def set_current_session(session_id):
        # First, unset the current session
        Session.query.update({Session.is_current: False})
        
        # Set the new session as the current one
        new_session = Session.query.get(session_id)
        if new_session:
            new_session.is_current = True
            db.session.commit()
            return new_session
        return None


class StudentClassHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id"), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)

    student = db.relationship("Student", backref="class_history", lazy=True)
    session = db.relationship("Session", backref="class_history", lazy=True)

    @classmethod
    def get_class_by_session(cls, student_id, session_year_str):
        """
        Get the student's class for a given academic session.
        If the session is a string, retrieve the session object first.
        """
        # If session is passed as a string (e.g., "2023/2024"), get the session object
        if isinstance(session_year_str, str):
            session_year = Session.query.filter_by(year=session_year_str).first()
        else:
            session_year = session_year_str  # Assume session is an object

        if not session_year:
            # Log or handle the case where the session doesn't exist
            return None

        # Query the class history for the student in the specified session
        class_history = cls.query.filter_by(
            student_id=student_id, session_id=session_year.id
        ).first()

        return class_history.class_name if class_history else None


    def __repr__(self):
        return f"<StudentClassHistory Student: {self.student_id}, Class: {self.class_name}, Session: {self.session.year}>"


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
    previous_class = db.Column(db.String(50), nullable=True)
    parent_phone_number = db.Column(db.String(11), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    parent_occupation = db.Column(db.String(100), nullable=True)
    state_of_origin = db.Column(db.String(50), nullable=True)
    local_government_area = db.Column(db.String(50), nullable=True)
    religion = db.Column(db.String(50), nullable=True)
    date_registered = db.Column(db.DateTime, server_default=db.func.now())
    approved = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    results = db.relationship("Result", backref="student", lazy=True)

    def get_class_by_session(self, session):
        """
        Delegate to StudentClassHistory to fetch the student's class
        in the specified session.
        """
        return StudentClassHistory.get_class_by_session(self.id, session)

    def get_latest_class(self):
        """Get the student's latest class by finding the latest session."""
        latest_session = self.get_latest_session()
        return self.get_class_by_session(latest_session)

    def get_latest_session(self):
        """Get the most recent session from the class history."""
        latest_class_history = (
            StudentClassHistory.query.filter_by(student_id=self.id)
            .order_by(StudentClassHistory.id.desc())
            .first()
        )
        return latest_class_history.session if latest_class_history else None

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
    session_year = db.Column(db.String(20), nullable=False)
    class_assessment = db.Column(db.Integer, nullable=True)
    summative_test = db.Column(db.Integer, nullable=True)
    exam = db.Column(db.Integer, nullable=True)
    total = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.String(5))
    created_at = db.Column(db.DateTime, default=datetime.now())
    remark = db.Column(db.String(100))
    next_term_begins = db.Column(db.String(100), nullable=True)
    last_term_average = db.Column(db.Float, nullable=True)
    position = db.Column(db.String(10), nullable=True)
    date_issued = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<Result Student ID: {self.student_id}, Subject ID: {self.subject_id}>"
