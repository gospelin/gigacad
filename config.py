import os
from dotenv import load_dotenv

class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY")
    # or "your_secret_key_here"

    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = True
