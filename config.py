import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or "secret_string"

    SQLALCHEMY_DATABASE_URI = (
        "mysql://gigo:Tripled@121@hostname:3306/school_database"
    )
