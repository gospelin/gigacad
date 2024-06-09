from application import app, db
from application.models import User


def create_admin_user():
    with app.app_context():
        username = "admin"
        password = "Tripled@121"  # Change this to a secure password

        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            admin = User(username=username, is_admin=True)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(
                f"Admin user created with username: {username} and password: {password}"
            )
        else:
            print(f"Admin user with username {username} already exists.")



if __name__ == "__main__":
    create_admin_user()
