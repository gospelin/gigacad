from application import db, bcrypt
from flask_login import UserMixin, current_user
from datetime import datetime
from enum import Enum as PyEnum
from cryptography.fernet import Fernet
import os
import random
import string
import pytz

key = os.getenv("ENCRYPTION_KEY") or Fernet.generate_key()
cipher = Fernet(key)

NIGERIA_TZ = pytz.timezone('Africa/Lagos')

def nigeria_now():
    return datetime.now(NIGERIA_TZ)

class TermEnum(PyEnum):
    FIRST = "First"
    SECOND = "Second"
    THIRD = "Third"

class RoleEnum(PyEnum):
    ADMIN = "admin"
    STUDENT = "student"
    TEACHER = "teacher"

class_teacher = db.Table(
    "class_teacher",
    db.Column("class_id", db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True),
    db.Column("teacher_id", db.Integer, db.ForeignKey("teacher.id", ondelete="CASCADE"), primary_key=True),
    db.Column("session_id", db.Integer, db.ForeignKey("session.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    db.Column("term", db.String(50), primary_key=True, nullable=False),
    db.Column("is_form_teacher", db.Boolean, default=False)
)

class_subject = db.Table(
    "class_subject",
    db.Column("class_id", db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True),
    db.Column("subject_id", db.Integer, db.ForeignKey("subject.id", ondelete="CASCADE"), primary_key=True),
)

teacher_subject = db.Table(
    "teacher_subject",
    db.Column("teacher_id", db.Integer, db.ForeignKey("teacher.id", ondelete="CASCADE"), primary_key=True),
    db.Column("subject_id", db.Integer, db.ForeignKey("subject.id", ondelete="CASCADE"), primary_key=True),
)

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(20), unique=True, nullable=False)
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    current_term = db.Column(db.Enum("First", "Second", "Third", name="termenum"), nullable=False, default="First")

    def __repr__(self):
        return f"<Session {self.year}>"

    @staticmethod
    def get_current_session():
        return Session.query.filter_by(is_current=True).first()

    @staticmethod
    def get_current_session_and_term(include_term=False):
        if not current_user.is_authenticated:
            return None, None if include_term else None

        preference = UserSessionPreference.query.filter_by(user_id=current_user.id).first()
        if preference:
            session = Session.query.get(preference.session_id)
            term = TermEnum(preference.current_term) if preference.current_term else None
        else:
            legacy_session = Session.query.filter_by(is_current=True).first()
            if legacy_session:
                session = legacy_session
                term = TermEnum(legacy_session.current_term) if legacy_session.current_term else TermEnum.FIRST
                preference = UserSessionPreference(
                    user_id=current_user.id,
                    session_id=session.id,
                    current_term=term.value
                )
                db.session.add(preference)
                db.session.commit()
            else:
                session = Session.query.order_by(Session.year.desc()).first()
                if not session:
                    return None, None if include_term else None
                term = TermEnum.FIRST
                preference = UserSessionPreference(
                    user_id=current_user.id,
                    session_id=session.id,
                    current_term=term.value
                )
                db.session.add(preference)
                db.session.commit()

        return (session, term) if include_term else session

class StudentClassHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id", ondelete="CASCADE"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id", ondelete="CASCADE"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), nullable=True)
    start_term = db.Column(db.Enum("First", "Second", "Third", name="termenum"), nullable=True, default="First")
    end_term = db.Column(db.Enum("First", "Second", "Third", name="termenum"), nullable=True)
    join_date = db.Column(db.DateTime, nullable=False, default=nigeria_now)
    leave_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    session = db.relationship("Session", backref="class_history", lazy=True)
    class_ref = db.relationship("Classes", backref="class_history", lazy=True)

    __table_args__ = (
        db.Index('idx_student_session', 'student_id', 'session_id', unique=False),
    )

    def __repr__(self):
        return f"<StudentClassHistory Student: {self.student_id}, Class: {self.class_ref.name if self.class_ref else 'None'}, Session: {self.session.year}>"

    def is_active_in_term(self, session_id, term):
        term_order = {TermEnum.FIRST.value: 1, TermEnum.SECOND.value: 2, TermEnum.THIRD.value: 3}
        start_order = term_order.get(self.start_term, 1)
        end_order = term_order.get(self.end_term, 4) if self.end_term else 4
        target_order = term_order.get(term, 1)

        return (self.session_id == session_id and
                self.is_active and
                self.leave_date is None and
                start_order <= target_order <= end_order)

    def mark_as_left(self, term):
        if term not in [t.value for t in TermEnum]:
            raise ValueError(f"Invalid term: {term}")

        term_order = {TermEnum.FIRST.value: 1, TermEnum.SECOND.value: 2, TermEnum.THIRD.value: 3}
        start_order = term_order.get(self.start_term, 1)
        leave_order = term_order.get(term, 1)

        if leave_order <= start_order:
            self.is_active = False
        self.end_term = term
        self.leave_date = nigeria_now()

    def reenroll(self, session_id, class_id, term):
        if self.is_active and self.leave_date is None:
            raise ValueError("Student is already active")
        self.session_id = session_id
        self.class_id = class_id
        self.start_term = term
        self.end_term = None
        self.join_date = nigeria_now()
        self.leave_date = None
        self.is_active = True

class Student(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    reg_no = db.Column(db.String(50), nullable=True)
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    parent_name = db.Column(db.String(70), nullable=True)
    _parent_phone_number = db.Column(db.String(255), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    parent_occupation = db.Column(db.String(100), nullable=True)
    state_of_origin = db.Column(db.String(50), nullable=True)
    local_government_area = db.Column(db.String(50), nullable=True)
    religion = db.Column(db.String(50), nullable=True)
    date_registered = db.Column(db.DateTime, nullable=False, default=nigeria_now)
    approved = db.Column(db.Boolean, nullable=False, default=False)
    profile_pic = db.Column(db.String(255), nullable=True, default=None)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=True)

    results = db.relationship("Result", backref="student", lazy=True, cascade="save-update, merge", passive_deletes=True)
    class_history = db.relationship("StudentClassHistory", backref="student", lazy=True, cascade="save-update, merge", passive_deletes=True)
    fee_payments = db.relationship("FeePayment", backref="student", lazy=True, cascade="save-update, merge", passive_deletes=True)

    def get_full_name(self):
        names = [self.first_name]
        if self.middle_name:
            names.append(self.middle_name)
        names.append(self.last_name)
        return " ".join(names)

    @property
    def parent_phone_number(self):
        return cipher.decrypt(self._parent_phone_number.encode()).decode() if self._parent_phone_number else None

    @parent_phone_number.setter
    def parent_phone_number(self, value):
        self._parent_phone_number = cipher.encrypt(value.encode()).decode() if value else None

    def get_current_class(self):
        latest_class = self.class_history[-1] if self.class_history else None
        return latest_class.class_ref.name if latest_class else None

    def get_current_enrollment(self):
        current_session = Session.get_current_session()
        if not current_session:
            return None
        return StudentClassHistory.query.filter_by(
            student_id=self.id,
            session_id=current_session.id,
            is_active=True,
            leave_date=None
        ).order_by(StudentClassHistory.join_date.desc()).first()

    def get_class_by_session_and_term(self, session_id, term):
        enrollment = StudentClassHistory.query.filter_by(
            student_id=self.id,
            session_id=session_id,
            start_term=term.value,
            is_active=True,
            leave_date=None
        ).first()
        return enrollment.class_ref.name if enrollment else None

    def get_class_by_session(self, session_year):
        session_obj = Session.query.filter_by(year=session_year).first()
        if not session_obj:
            print(f"Session {session_year} not found!")
            return None
        class_history_entry = next(
            (entry for entry in self.class_history if entry.session_id == session_obj.id and entry.is_active),
            None
        )
        return class_history_entry.class_ref.name if class_history_entry else None

    @classmethod
    def generate_reg_no(cls, session_year=None):
        if not session_year:
            current_session = Session.get_current_session_and_term(include_term=False)
            session_year = current_session.year if current_session else datetime.now().year
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        reg_no = f"{session_year}/{random_suffix}"
        while cls.query.filter_by(reg_no=reg_no).first():
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            reg_no = f"{session_year}/{random_suffix}"
        return reg_no

class FeePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id", ondelete="CASCADE"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id", ondelete="CASCADE"), nullable=False)
    term = db.Column(db.Enum("First", "Second", "Third", name="termenum"), nullable=True)
    has_paid_fee = db.Column(db.Boolean, nullable=False, default=False)

class Classes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    section = db.Column(db.String(20), nullable=True)
    hierarchy = db.Column(db.Integer, unique=True, nullable=False)

    subjects = db.relationship("Subject", secondary="class_subject", back_populates="classes", lazy="dynamic")
    teachers = db.relationship("Teacher", secondary="class_teacher", back_populates="classes", lazy="dynamic")

    def __repr__(self):
        return f"<Class {self.name} ({self.section}) - Hierarchy: {self.hierarchy}>"

    @classmethod
    def get_next_class(cls, current_hierarchy):
        return cls.query.filter(cls.hierarchy > current_hierarchy).order_by(cls.hierarchy.asc()).first()

    @classmethod
    def get_previous_class(cls, current_hierarchy):
        return cls.query.filter(cls.hierarchy < current_hierarchy).order_by(cls.hierarchy.desc()).first()

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(50), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    section = db.Column(db.String(20), nullable=False)

    classes = db.relationship("Classes", secondary="class_teacher", back_populates="teachers", lazy="dynamic")
    subjects = db.relationship("Subject", secondary="teacher_subject", back_populates="teachers", lazy="dynamic")

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def is_form_teacher_for_class(self, class_id):
        return any(ct.is_form_teacher for ct in db.session.query(class_teacher).filter_by(teacher_id=self.id, class_id=class_id).all())

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    section = db.Column(db.String(100), nullable=True)
    deactivated = db.Column(db.Boolean, nullable=False, default=False)

    classes = db.relationship("Classes", secondary="class_subject", back_populates="subjects", lazy="dynamic")
    teachers = db.relationship("Teacher", secondary="teacher_subject", back_populates="subjects", lazy="dynamic")
    results = db.relationship("Result", backref="subject", lazy=True)

    def __repr__(self):
        return f"<Subject {self.name}>"

class StudentTermSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id", ondelete="CASCADE"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id", ondelete="CASCADE"), nullable=False)
    term = db.Column(db.Enum("First", "Second", "Third", name="termenum"), nullable=False)

    grand_total = db.Column(db.Integer, nullable=True)
    term_average = db.Column(db.Float, nullable=True)
    cumulative_average = db.Column(db.Float, nullable=True)
    last_term_average = db.Column(db.Float, nullable=True)
    subjects_offered = db.Column(db.Integer, nullable=True)
    position = db.Column(db.String(10), nullable=True)
    principal_remark = db.Column(db.String(100), nullable=True)
    teacher_remark = db.Column(db.String(100), nullable=True)
    next_term_begins = db.Column(db.String(100), nullable=True)
    date_issued = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=nigeria_now)

    session = db.relationship("Session", backref="term_summaries", lazy=True)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'class_id', 'term', 'session_id', name='unique_term_summary'),
    )

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id", ondelete="CASCADE"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id", ondelete="CASCADE"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id", ondelete="CASCADE"), nullable=False, default=1)
    term = db.Column(db.Enum("First", "Second", "Third", name="termenum"), nullable=False, default="Third")

    class_assessment = db.Column(db.Integer, nullable=True)
    summative_test = db.Column(db.Integer, nullable=True)
    exam = db.Column(db.Integer, nullable=True)
    total = db.Column(db.Integer, nullable=True)
    grade = db.Column(db.String(5), nullable=True)
    remark = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=nigeria_now)

    session = db.relationship("Session", backref="results", lazy=True)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'class_id', 'term', 'session_id', name='unique_result'),
    )

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Enum("admin", "student", "teacher", name="roleenum"), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    mfa_secret = db.Column(db.String(32), nullable=True)

    student = db.relationship("Student", backref="user", uselist=False)
    privileges = db.relationship("AdminPrivilege", back_populates="user", uselist=False, lazy=True)
    session_preference = db.relationship("UserSessionPreference", back_populates="user", uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class AdminPrivilege(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    can_manage_users = db.Column(db.Boolean, default=False)
    can_manage_sessions = db.Column(db.Boolean, default=False)
    can_manage_classes = db.Column(db.Boolean, default=False)
    can_manage_results = db.Column(db.Boolean, default=False)
    can_manage_teachers = db.Column(db.Boolean, default=False)
    can_manage_subjects = db.Column(db.Boolean, default=False)
    can_view_reports = db.Column(db.Boolean, default=True)

    user = db.relationship("User", back_populates="privileges", lazy=True)

class UserSessionPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id", ondelete="CASCADE"), nullable=False)
    current_term = db.Column(db.Enum("First", "Second", "Third", name="termenum"), nullable=False, default="First")

    user = db.relationship("User", back_populates="session_preference", lazy=True)
    session = db.relationship("Session", backref="user_preferences", lazy=True)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=nigeria_now, nullable=False)

    user = db.relationship("User", backref=db.backref("audit_logs", lazy=True, cascade="save-update, merge", passive_deletes=True))