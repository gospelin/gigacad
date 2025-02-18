from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    DateField,
    SubmitField,
    PasswordField,
    SelectMultipleField,
    FloatField,
    IntegerField,
    HiddenField,
    FieldList,
    FormField,
    BooleanField,
    ValidationError
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email
from wtforms_sqlalchemy.fields import QuerySelectField

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
    class_id = SelectField("Current Class", coerce=int, validators=[DataRequired()]) 
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
        default="First Term",
    )
    session = SelectField(
        "Select Session",
        choices=[],  
        validators=[DataRequired()],
        default="2024/2025",
    )
    next_term_begins = StringField("Next Term Begins", validators=[Optional()])
    date_issued = StringField("Date Issued", validators=[Optional()])
    last_term_average = FloatField("Last Term Average", validators=[Optional()])
    position = StringField("Position", validators=[Optional()])
    submit = SubmitField("Load Results")


class StudentLoginForm(FlaskForm):
    identifier = StringField(
        "Student ID or Username",
        validators=[
            DataRequired(message="This field is required."),
            Length(min=3, max=50, message="Must be between 3 and 50 characters."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="This field is required.")],
    )
    submit = SubmitField("Login")

class AdminLoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="This field is required."),
            Length(min=3, max=50, message="Must be between 3 and 50 characters."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="This field is required.")],
    )
    submit = SubmitField("Login")


class EditStudentForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired()])
    middle_name = StringField("Middle Name", validators=[Length(max=50)])
    last_name = StringField("Last Name", validators=[DataRequired()])
    reg_no = StringField("Registration ID", validators=[DataRequired()])
    gender = SelectField(
        "Gender",
        choices=[("male", "Male"), ("female", "Female")],
        validators=[DataRequired()],
    )
    class_id = SelectField("Current Class", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Update")


class SubjectForm(FlaskForm):
    name = StringField("Name (comma-separated)", validators=[DataRequired()])
    section = SelectMultipleField(
        "Section",
        choices=[
            ("Nursery", "Nursery"),
            ("Basic", "Basic"),
            ("Secondary", "Secondary"),
            ("Senior Secondary", "Senior Secondary"),
        ],
        validators=[DataRequired()],
    )  # Change to SelectMultipleField
    submit = SubmitField("Add Subject")


class DeleteForm(FlaskForm):
    submit = SubmitField("Delete")


class ApproveForm(FlaskForm):
    pass

class SessionForm(FlaskForm):
    session = SelectField(
        "Select Session",
        choices=[],  # Populated dynamically in the route
        validators=[DataRequired()],
        default="2024/2025",
    )
    term = SelectField(
        "Select Term",
        choices=[],  # Populated dynamically in the route
        validators=[DataRequired()],
        default="First Term",
    )
    submit = SubmitField("Update Academic Session and Term")


class classForm(FlaskForm):
    class_name = SelectField("Current Class", validators=[DataRequired()])
    submit = SubmitField("View Classes")
    
class ClassesForm(FlaskForm):
    class_id = HiddenField("Class ID")  # For editing existing classes
    name = StringField(
        "Class Name", 
        validators=[DataRequired(), Length(max=50, message="Class name must be under 50 characters.")]
    )
    section = SelectField(
        "Section",
         choices=[
            ("Nursery", "Nursery"),
            ("Basic", "Basic"),
            ("Secondary", "Secondary"),
            ("Senior Secondary", "Senior Secondary"),
        ],
        validators=[DataRequired(), Length(max=20, message="Section must be under 20 characters.")]
    )
    hierarchy = IntegerField(
        "Hierarchy", 
        validators=[DataRequired(), NumberRange(min=1, message="Hierarchy must be a positive integer.")]
    )
    submit_create = SubmitField("Create Class")
    submit_edit = SubmitField("Edit Class")
    submit_delete = SubmitField("Delete Class")
    
class TeacherForm(FlaskForm):
    id = HiddenField("Teacher ID")
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=50)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=50)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=100)])
    phone_number = StringField("Phone Number", validators=[Optional(), Length(max=50)])
    section = SelectField(
        "Section",
        choices=[("Nursery", "Nursery"), ("Primary", "Primary"), ("Secondary", "Secondary")],
        validators=[DataRequired()],
    )
    submit = SubmitField("Save")
    submit_edit = SubmitField("Update Profile")

# Create a form for each subject's result entry
class SubjectResultForm(FlaskForm):
    subject_id = HiddenField("Subject ID")  # Hidden field to store subject ID
    class_assessment = IntegerField(
        "Class Assessment", validators=[Optional(), NumberRange(min=0, max=20)]
    )
    summative_test = IntegerField(
        "Summative Test", validators=[Optional(), NumberRange(min=0, max=20)]
    )
    exam = IntegerField("Exam", validators=[Optional(), NumberRange(min=0, max=60)])
    total = IntegerField("Total", validators=[Optional(), NumberRange(min=0, max=100)])
    grade = StringField("Grade", validators=[Optional()])
    remark = StringField("Remark", validators=[Optional()])


# Main form to handle all subjects
class ManageResultsForm(FlaskForm):
    subjects = FieldList(
        FormField(SubjectResultForm)
    )
    submit = SubmitField("Save Results")





from application.models import Classes, Subject, Teacher

# Helper functions for dynamic queries
def get_classes():
    return Classes.query.order_by(Classes.hierarchy).all()

def get_subjects():
    return Subject.query.filter_by(deactivated=False).order_by(Subject.name).all()

def get_teachers():
    return Teacher.query.order_by(Teacher.last_name).all()

class AssignSubjectToClassForm(FlaskForm):
    class_name = QuerySelectField(
        "Class",
        query_factory=get_classes,
        get_label="name",
        allow_blank=False,
        validators=[DataRequired()],
    )
    subject = QuerySelectField(
        "Subject",
        query_factory=get_subjects,
        get_label="name",
        allow_blank=False,
        validators=[DataRequired()],
    )
    submit = SubmitField("Assign Subject to Class")

class AssignSubjectToTeacherForm(FlaskForm):
    teacher = QuerySelectField(
        "Teacher",
        query_factory=get_teachers,
        get_label=lambda teacher: f"{teacher.last_name}, {teacher.first_name}",
        allow_blank=False,
        validators=[DataRequired()],
    )
    subject = QuerySelectField(
        "Subject",
        query_factory=get_subjects,
        get_label="name",
        allow_blank=False,
        validators=[DataRequired()],
    )
    submit = SubmitField("Assign Subject")

class AssignTeacherToClassForm(FlaskForm):
    teacher = QuerySelectField(
        "Teacher",
        query_factory=get_teachers,
        get_label=lambda teacher: f"{teacher.last_name}, {teacher.first_name}",
        allow_blank=False,
        validators=[DataRequired()],
    )
    class_name = QuerySelectField(
        "Class",
        query_factory=get_classes,
        get_label="name",
        allow_blank=False,
        validators=[DataRequired()],
    )
    is_form_teacher = BooleanField("Assign as Form Teacher")
    submit = SubmitField("Assign Teacher to Class")








# Form for assigning subjects to a teacher
class AssignSubjectsForm(FlaskForm):
    subject = SelectField('Subject', coerce=int, choices=[], validate_choice=False)
    submit = SubmitField('Assign Subject')

    def __init__(self, *args, **kwargs):
        super(AssignSubjectsForm, self).__init__(*args, **kwargs)
        self.subject.choices = [(subject.id, subject.name) for subject in Subject.query.all()]

# Form for assigning classes to a teacher
class AssignClassesForm(FlaskForm):
    class_name = SelectField('Class', coerce=int, choices=[], validate_choice=False)
    submit = SubmitField('Assign Class')

    def __init__(self, *args, **kwargs):
        super(AssignClassesForm, self).__init__(*args, **kwargs)
        self.class_name.choices = [(class_.id, class_.name) for class_ in Classes.query.all()]
