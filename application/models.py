from werkzeug.security import generate_password_hash, check_password_hash
from application import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import Enum

class RoleEnum(Enum):
    ADMIN = "admin"
    STUDENT = "student"
    TEACHER = "teacher"

# Association Tables
class_teacher = db.Table(
    "class_teacher",
    db.Column("class_id", db.Integer, db.ForeignKey("classes.id"), primary_key=True),
    db.Column("teacher_id", db.Integer, db.ForeignKey("teacher.id"), primary_key=True),
    db.Column("is_form_teacher", db.Boolean, default=False)
)

class_subject = db.Table(
    "class_subject",
    db.Column("class_id", db.Integer, db.ForeignKey("classes.id"), primary_key=True),
    db.Column("subject_id", db.Integer, db.ForeignKey("subject.id"), primary_key=True),
)

teacher_subject = db.Table(
    "teacher_subject",
    db.Column("teacher_id", db.Integer, db.ForeignKey("teacher.id"), primary_key=True),
    db.Column("subject_id", db.Integer, db.ForeignKey("subject.id"), primary_key=True),
)

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(20), unique=True, nullable=False)  # e.g., "2023/2024"
    is_current = db.Column(db.Boolean, default=False)
    current_term = db.Column(db.String(20), nullable=True)

    def __repr__(self):
        return f"<Session {self.year}>"

    @staticmethod
    def get_current_session():
        return Session.query.filter_by(is_current=True).first()

    @staticmethod
    def get_current_session_and_term(include_term=False):
        """Helper function to get the current session and optionally the current term."""
        session = Session.query.filter_by(is_current=True).first()
        if not session:
            return None, None if include_term else None
        return (session, session.current_term) if include_term else session


    @staticmethod
    def set_current_session(session_id, term):
        # First, unset the current session
        Session.query.update({Session.is_current: False})
        db.session.commit()

        # Set the new session as the current one
        new_session = Session.query.get(session_id)
        if new_session:
            new_session.is_current = True
            new_session.current_term = term
            db.session.commit()
            return new_session
        return None

class StudentClassHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True)

    # student = db.relationship("Student", backref="class_history", lazy=True)
    session = db.relationship("Session", backref="class_history", lazy=True)
    class_ref = db.relationship("Classes", backref="class_history", lazy=True)

    def __repr__(self):
        return f"<StudentClassHistory Student: {self.student_id}, Class: {self.class_ref.name}, Session: {self.session.year}>"


# Your models start here

class Student(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    reg_no = db.Column(db.String(50), nullable=True)
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    parent_name = db.Column(db.String(70), nullable=True)
    parent_phone_number = db.Column(db.String(11), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    parent_occupation = db.Column(db.String(100), nullable=True)
    state_of_origin = db.Column(db.String(50), nullable=True)
    local_government_area = db.Column(db.String(50), nullable=True)
    religion = db.Column(db.String(50), nullable=True)
    date_registered = db.Column(db.DateTime, server_default=db.func.now())
    approved = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    results = db.relationship("Result", backref="student", lazy=True)
    class_history = db.relationship("StudentClassHistory", backref="student", lazy=True)
    fee_payments = db.relationship("FeePayment", backref="student", lazy=True)

    def get_current_class(self):
        latest_class = self.class_history[-1] if self.class_history else None
        return latest_class.class_ref.name if latest_class else None

    # def get_class_by_session(self, session_year):
    #     # If session is passed as a string (e.g., "2023/2024"), get the session object
    #     if isinstance(session_year, str):
    #         session_id = Session.query.filter_by(year=session_year).first()
    #     else:
    #         session_id = session_year

    #     # Filter class history by session_id
    #     class_history_entry = next(
    #         (entry for entry in self.class_history if entry.session_id == session_id),
    #         None
    #     )
    #     # If found, return the class name; otherwise, return None
    #     return class_history_entry.class_ref.name if class_history_entry else None

    def get_class_by_session(self, session_year):
        session_obj = Session.query.filter_by(year=session_year).first()
        session_id = session_obj.id if session_obj else None

        if not session_id:
            print(f"Session {session_year} not found!")
            return None

        print(f"Checking class history for session_id={session_id}")
        for entry in self.class_history:
            print(f"StudentClassHistory entry: session_id={entry.session_id}, class_name={entry.class_ref.name}")

        class_history_entry = next(
            (entry for entry in self.class_history if entry.session_id == session_id),
            None
        )

        return class_history_entry.class_ref.name if class_history_entry else None


class FeePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id"), nullable=False)
    term = db.Column(db.String(20), nullable=False)
    has_paid_fee = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<FeePayment Student: {self.student_id}, Session: {self.session_id}, Term: {self.term}, Paid: {self.has_paid_fee}>"

class Classes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=True)
    section = db.Column(db.String(20), nullable=True)
    hierarchy = db.Column(db.Integer, unique=True, nullable=False)

    # Relationships
    subjects = db.relationship(
        "Subject", secondary="class_subject", back_populates="classes", lazy="dynamic"
    )
    teachers = db.relationship(
        "Teacher", secondary="class_teacher", back_populates="classes", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Class {self.name} ({self.section}) - Hierarchy: {self.hierarchy}>"

    @classmethod
    def get_next_class(cls, current_hierarchy):
        """Returns the next class in the hierarchy based on the current hierarchy value."""
        return cls.query.filter(cls.hierarchy > current_hierarchy).order_by(cls.hierarchy.asc()).first()

    @classmethod
    def get_previous_class(cls, current_hierarchy):
        """Returns the previous class in the hierarchy based on the current hierarchy value."""
        return cls.query.filter(cls.hierarchy < current_hierarchy).order_by(cls.hierarchy.desc()).first()

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    section = db.Column(db.String(20), nullable=False)

    # Relationships
    classes = db.relationship(
        "Classes", secondary="class_teacher", back_populates="teachers", lazy="dynamic"
    )
    subjects = db.relationship(
        "Subject", secondary="teacher_subject", back_populates="teachers", lazy="dynamic"
    )

    def is_form_teacher_for_class(self, class_id):
        """Check if the teacher is a form teacher for a specific class."""
        return any(teacher.is_form_teacher for teacher in self.classes.filter_by(id=class_id).all())


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    section = db.Column(db.String(20), nullable=True)
    deactivated = db.Column(db.Boolean, nullable=False, default=False)

    classes = db.relationship(
        "Classes", secondary="class_subject", back_populates="subjects", lazy="dynamic"
    )
    teachers = db.relationship(
        "Teacher", secondary="teacher_subject", back_populates="subjects", lazy="dynamic"
    )

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
    subjects_offered = db.Column(db.Integer, nullable=True)

    class_assessment = db.Column(db.Integer, nullable=True)
    summative_test = db.Column(db.Integer, nullable=True)
    exam = db.Column(db.Integer, nullable=True)
    total = db.Column(db.Integer, nullable=True)
    grade = db.Column(db.String(5), nullable=True)
    remark = db.Column(db.String(100), nullable=True)
    grand_total = db.Column(db.Integer, nullable=True)


    next_term_begins = db.Column(db.String(100), nullable=True)
    last_term_average = db.Column(db.Float, nullable=True)
    term_average = db.Column(db.Float, nullable=True)
    cumulative_average = db.Column(db.Float, nullable=True)
    position = db.Column(db.String(10), nullable=True)

    principal_remark = db.Column(db.String(100), nullable=True)
    teacher_remark = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now())
    date_issued = db.Column(db.String(100), nullable=True)

    __table_args__ = (db.UniqueConstraint('student_id', 'subject_id', 'term', 'session', name='unique_result'),)

    def __repr__(self):
        return f"<Result Student ID: {self.student_id}, Subject ID: {self.subject_id}>"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(Enum(RoleEnum.ADMIN, RoleEnum.STUDENT, RoleEnum.TEACHER), nullable=False)
    active = db.Column(db.Boolean, default=True)
    student = db.relationship("Student", backref="user", uselist=False)

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


