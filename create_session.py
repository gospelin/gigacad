from application import app, db
from application.models import Session


def create_sessions():
    with app.app_context():
        # Define sessions to be added
        sessions = [
            {"year": "2023/2024", "is_current": True},
            {"year": "2024/2025", "is_current": False},
            {"year": "2026/2027", "is_current": False},
            {"year": "2027/2028", "is_current": False},
            {"year": "2028/2029", "is_current": False},
        ]

        # Add each session to the database
        for session_data in sessions:
            session = Session(
                year=session_data["year"], is_current=session_data["is_current"]
            )

            # Check if session already exists to avoid duplicates
            existing_session = Session.query.filter_by(year=session.year).first()
            if not existing_session:
                db.session.add(session)
                print(f"Adding session: {session.year}")
            else:
                print(f"Session {session.year} already exists.")

        # Commit changes to the database
        db.session.commit()
        print("Sessions have been added successfully.")


if __name__ == "__main__":
    create_sessions()
