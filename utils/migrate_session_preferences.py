import sys
import os

# Get the absolute path of the project root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from application import db, create_app
from application.models import User, Session, UserSessionPreference, RoleEnum

app = create_app()
with app.app_context():
    # Find the current global session
    current_session = Session.query.filter_by(is_current=True).first()
    if not current_session:
        print("No current session found. Aborting migration.")
        exit(1)

    # Get all admin users
    admins = User.query.filter_by(role=RoleEnum.ADMIN.value).all()
    if not admins:
        print("No admin users found. Aborting migration.")
        exit(1)

    # Transfer current session and term to each admin
    for admin in admins:
        existing_pref = UserSessionPreference.query.filter_by(user_id=admin.id).first()
        if not existing_pref:
            pref = UserSessionPreference(
                user_id=admin.id,
                session_id=current_session.id,
                current_term=current_session.current_term or "First"  # Default to "First" if null
            )
            db.session.add(pref)
            print(f"Set preference for {admin.username}: {current_session.year}, {pref.current_term}")
        else:
            print(f"Preference already exists for {admin.username}, skipping.")

    db.session.commit()
    print("Migration completed successfully!")