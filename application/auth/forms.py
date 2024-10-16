from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    DateField,
    SubmitField,
    PasswordField,
    SelectMultipleField,
    FloatField,
)
from wtforms.validators import DataRequired, Length, Optional


class StudentRegistrationForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=50)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=50)])
    middle_name = StringField("Middle Name", validators=[Length(max=50)])
    gender = SelectField(
        "Gender",
        choices=[("male", "Male"), ("female", "Female")],
        validators=[DataRequired()],
    )   
    date_of_birth = DateField("Date of Birth", validators=[Optional()])
    parent_name = StringField("Parent Name", validators=[Length(max=70)])
    parent_phone_number = StringField(
        "Parent Phone Number", validators=[Length(max=11)]
    )
    address = StringField("Address", validators=[Length(max=255)])
    parent_occupation = StringField("Parent Occupation", validators=[Length(max=100)])
    class_name = SelectField(
        "Current class",
        choices=[
            ("Creche"),
            ("Pre-Nursery"),
            ("Nursery 1"),
            ("Nursery 2"),
            ("Nursery 3"),
            ("Basic 1"),
            ("Basic 2"),
            ("Basic 3"),
            ("Basic 4"),
            ("Basic 5"),
            ("Basic 6"),
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
            ("Basic 1"),
            ("Basic 2"),
            ("Basic 3"),
            ("Basic 4"),
            ("Basic 5"),
            ("Basic 6"),
            ("JSS 1"),
            ("JSS 2"),
            ("JSS 3"),
        ],
        validate_choice=True,
    )
    state_of_origin = StringField("State of Origin", validators=[Length(max=50)])
    local_government_area = StringField(
        "Local Government Area", validators=[Length(max=50)]
    )
    religion = StringField("Religion", validators=[Length(max=50)])
    submit = SubmitField("Register")


class ResultForm(FlaskForm):
    term = SelectField(
        "Select Term",
        choices=[
            ("First Term", "First Term"),
            ("Second Term", "Second Term"),
            ("Third Term", "Third Term"),
        ],
        validators=[DataRequired()],
        default="Third Term",
    )
    session = SelectField(
        "Select Session",  # This will be populated dynamically
        choices=[],  # Start with an empty list, to be populated in the route
        validators=[DataRequired()],
    )
    next_term_begins = StringField("Next Term Begins", validators=[Optional()])
    date_issued = StringField("Date Issued", validators=[Optional()])
    last_term_average = FloatField("Last Term Average", validators=[Optional()])
    position = StringField("Position", validators=[Optional()])
    submit = SubmitField("Load Results")


class LoginForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=2, max=50)]
    )
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class EditStudentForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired()])
    middle_name = StringField("Middle Name", validators=[Length(max=50)])
    last_name = StringField("Last Name", validators=[DataRequired()])
    username = StringField("Username", validators=[DataRequired()])
    gender = SelectField(
        "Gender",
        choices=[("male", "Male"), ("female", "Female")],
        validators=[DataRequired()],
    )
    class_name = SelectField(
        "Current Class",
        choices=[
            ("Creche", "Creche"),
            ("Pre-Nursery", "Pre-Nursery"),
            ("Nursery 1", "Nursery 1"),
            ("Nursery 2", "Nursery 2"),
            ("Nursery 3", "Nursery 3"),
            ("Basic 1", "Basic 1"),
            ("Basic 2", "Basic 2"),
            ("Basic 3", "Basic 3"),
            ("Basic 4", "Basic 4"),
            ("Basic 5", "Basic 5"),
            ("Basic 6", "Basic 6"),
            ("JSS 1", "JSS 1"),
            ("JSS 2", "JSS 2"),
            ("JSS 3", "JSS 3"),
        ],
    )
    submit = SubmitField("Update")


class SubjectForm(FlaskForm):
    name = StringField("Name (comma-separated)", validators=[DataRequired()])
    section = SelectMultipleField(
        "Section",
        choices=[
            ("Nursery", "Nursery"),
            ("Basic", "Basic"),
            ("Secondary", "Secondary"),
        ],
        validators=[DataRequired()],
    )  # Change to SelectMultipleField
    submit = SubmitField("Add Subject")


class DeleteForm(FlaskForm):
    submit = SubmitField("Delete")


class ApproveForm(FlaskForm):
    pass


class SelectTermSessionForm(FlaskForm):
    term = SelectField(
        "Term",
        choices=[
            ("First Term", "First Term"),
            ("Second Term", "Second Term"),
            ("Third Term", "Third Term"),
        ],
        validators=[DataRequired()],
    )
    session = SelectField(
        "Select Session",
        choices=[
            ("2023/2024", "2023/2024"),
            ("2024/2025", "2024/2025"),
            ("2025/2026", "2025/2026"),
        ],
        validators=[DataRequired()],
        default="2023/2024",
    )
    submit = SubmitField("Generate Broadsheet")

class SessionForm(FlaskForm):
    session = SelectField("Select Session", choices=[], coerce=int)
    submit = SubmitField("Choose an Academic Session")


class classForm(FlaskForm):
    session = SelectField("Select Session", choices=[], coerce=int)
    class_name = SelectField(
        "Class",
        choices=[
            ("Creche", "Creche"),
            ("Pre-Nursery", "Pre-Nursery"),
            ("Nursery 1", "Nursery 1"),
            ("Nursery 2", "Nursery 2"),
            ("Nursery 3", "Nursery 3"),
            ("Basic 1", "Basic 1"),
            ("Basic 2", "Basic 2"),
            ("Basic 3", "Basic 3"),
            ("Basic 4", "Basic 4"),
            ("Basic 5", "Basic 5"),
            ("Basic 6", "Basic 6"),
            ("JSS 1", "JSS 1"),
            ("JSS 2", "JSS 2"),
            ("JSS 3", "JSS 3"),
        ],
    )
    submit = SubmitField("View Classes")
