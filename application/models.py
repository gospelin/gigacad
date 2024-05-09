from flask_sqlalchemy import SQLAlchemy
from application import db

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
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

    def __repr__(self):
        return f"<Student {self.first_name} {self.last_name}>"
