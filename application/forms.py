from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, SubmitField, PasswordField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange
from application.models import Subject


class StudentRegistrationForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=50)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=50)])
    email = StringField("Email", validators=[Email(), Length(max=100)])
    gender = SelectField(
        "Gender",
        choices=[("male", "Male"), ("female", "Female")],
        validators=[DataRequired()],
    )
    date_of_birth = DateField("Date of Birth")
    parent_phone_number = StringField(
        "Parent Phone Number", validators=[Length(max=11)]
    )
    address = StringField("Address", validators=[Length(max=255)])
    parent_occupation = StringField(
        "Parent Occupation", validators=[Length(max=100)]
    )
    entry_class = SelectField(
        "Entry class",
        choices=[
            ("Creche"),
            ("Pre-Nursery"),
            ("Nursery 1"),
            ("Nursery 2"),
            ("Nursery 3"),
            ("Primary 1"),
            ("Primary 2"),
            ("Primary 3"),
            ("Primary 4"),
            ("Primary 5"),
            ("Primary 6"),
            ("JSS 1"),
            ("JSS 2"),
            ("JSS 3"),
        ],
        validate_choice=True,
    )
    previous_class = SelectField(
        "Previous Class (if any)",
        choices=[
            ("Creche"),
            ("Pre-Nursery"),
            ("Nursery 1"),
            ("Nursery 2"),
            ("Nursery 3"),
            ("Primary 1"),
            ("Primary 2"),
            ("Primary 3"),
            ("Primary 4"),
            ("Primary 5"),
            ("Primary 6"),
            ("JSS 1"),
            ("JSS 2"),
            ("JSS 3"),
        ],
        validate_choice=True,
    )
    state_of_origin = StringField(
        "State of Origin", validators=[Length(max=50)]
    )
    local_government_area = StringField(
        "Local Government Area", validators=[Length(max=50)]
    )
    religion = StringField("Religion", validators=[Length(max=50)])
    submit = SubmitField("Register")


class ScoreForm(FlaskForm):
    term = StringField("Term", validators=[DataRequired()])
    session = StringField("Session", validators=[DataRequired()])
    subject_id = SelectField("Subject", choices=[], validators=[DataRequired()])
    class_assessment = IntegerField(
        "Class Assessment", validators=[DataRequired(), NumberRange(min=0, max=20)]
    )
    summative_test = IntegerField(
        "Summative Test", validators=[DataRequired(), NumberRange(min=0, max=20)]
    )
    exam = IntegerField(
        "Exam", validators=[DataRequired(), NumberRange(min=0, max=60)]
    )
    submit = SubmitField("Submit")

    def __init__(self, *args, **kwargs):
        super(ScoreForm, self).__init__(*args, **kwargs)
        self.subject_id.choices = [
            (subject.id, subject.name) for subject in Subject.query.all()
        ]


class LoginForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=2, max=20)]
    )
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class EditStudentForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    username = StringField("Username", validators=[DataRequired()])
    entry_class = SelectField(
        "Class",
        choices=[
            ("Primary 1", "Primary 1"),
            ("Primary 2", "Primary 2"),
            ("Primary 3", "Primary 3"),
            ("Primary 4", "Primary 4"),
            ("Primary 5", "Primary 5"),
            ("Primary 6", "Primary 6"),
            ("JSS 1", "JSS 1"),
            ("JSS 2", "JSS 2"),
            ("JSS 3", "JSS 3"),
        ],
    )
    submit = SubmitField("Save")


class SubjectForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Add Subject")


class DeleteForm(FlaskForm):
    submit = SubmitField("Delete")
