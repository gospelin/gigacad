from flask_login import current_user
from flask_admin.contrib.sqla import ModelView
from flask import redirect, url_for, request, render_template
from flask_admin import AdminIndexView, expose


class MyAdminIndexView(AdminIndexView):
    @expose("/")
    def index(self):
        if not self.is_accessible():
            return self.inaccessible_callback(name="index")
        return render_template("admin/index.html")

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login", next=request.url))


class StudentAdmin(ModelView):
    column_list = [
        "first_name",
        "last_name",
        "email",
        "username",
        "gender",
        "date_of_birth",
        "parent_phone_number",
        "address",
        "parent_occupation",
        "entry_class",
        "previous_class",
        "state_of_origin",
        "local_government_area",
        "religion",
        "date_registered",
        "approved",
    ]
    form_columns = [
        "first_name",
        "last_name",
        "email",
        "username",
        "password",
        "gender",
        "date_of_birth",
        "parent_phone_number",
        "address",
        "parent_occupation",
        "entry_class",
        "previous_class",
        "state_of_origin",
        "local_government_area",
        "religion",
        "approved",
    ]
    form_excluded_columns = ["date_registered"]
    column_searchable_list = [
        "first_name",
        "last_name",
        "email",
        "username",
        "entry_class",
    ]
    column_filters = ["approved", "entry_class"]
    list_template = "admin/student_admin.html"

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login", next=request.url))


class ScoreAdmin(ModelView):
    column_list = [
        "student_id",
        "subject",
        "class_assessment",
        "summative_test",
        "exam",
        "total",
        "term",
        "session",
    ]
    form_columns = [
        "student_id",
        "subject_id",
        "class_assessment",
        "summative_test",
        "exam",
        "term",
        "session",
    ]

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login", next=request.url))


class SubjectAdmin(ModelView):
    column_list = ["name"]
    form_columns = ["name"]
    list_template = "admin/subject_admin.html"

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login", next=request.url))
