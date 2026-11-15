import sys
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('session_setup')

# Add project root to sys.path
PROJECT_HOME = os.getenv("PROJECT_HOME", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)
    logger.info(f"Added {PROJECT_HOME} to sys.path")

# Load environment variables
env_path = os.path.join(PROJECT_HOME, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f"No .env file found at {env_path}. Using defaults.")


from application import create_app, db
from application.models import Session, TermEnum


def create_sessions():
    """Create academic sessions from 2023/2024 to 2030/2031 if they do not already exist.
    
    Matches the Session model:
    - year: String(20), unique, e.g. "2023/2024"
    - is_current: Boolean (only the latest created/updated session is marked current)
    - current_term: Enum("First", "Second", "Third"), defaults to "First"
    """
    app = create_app('production')

    with app.app_context():
        # Academic years to create (inclusive)
        start_year = 2023
        end_year = 2030  # produces up to 2030/2031

        sessions_to_create = [
            f"{year}/{year + 1}" for year in range(start_year, end_year + 1)
        ]

        logger.info(f"Preparing to ensure sessions exist: {sessions_to_create}")

        created_count = 0
        updated_count = 0
        latest_session = None

        try:
            # First pass: create any missing sessions (all start as non-current)
            for year_str in sessions_to_create:
                existing = Session.query.filter_by(year=year_str).first()
                if not existing:
                    session = Session(
                        year=year_str,
                        is_current=False,
                        current_term=TermEnum.FIRST.value  # "First"
                    )
                    db.session.add(session)
                    created_count += 1
                    logger.info(f"Created session: {year_str}")
                    print(f"Created session: {year_str}")
                else:
                    # Ensure current_term is valid if somehow missing/null
                    if not existing.current_term:
                        existing.current_term = TermEnum.FIRST.value
                        updated_count += 1
                        logger.info(f"Updated current_term for existing session: {year_str}")
                    logger.info(f"Session already exists: {year_str}")

            db.session.flush()

            # Second pass: ensure exactly one session is marked current.
            # Prefer the latest year (2030/2031). If it already exists, keep its
            # is_current flag unless nothing is currently marked current.
            all_sessions = Session.query.order_by(Session.year.desc()).all()
            if not all_sessions:
                logger.warning("No sessions found after creation attempt.")
                print("No sessions available.")
                return

            current_ones = [s for s in all_sessions if s.is_current]
            latest_session = all_sessions[0]  # highest year string works for YYYY/YYYY+1

            if not current_ones:
                # No current session → make the latest one current
                latest_session.is_current = True
                latest_session.current_term = latest_session.current_term or TermEnum.FIRST.value
                updated_count += 1
                logger.info(f"Marked {latest_session.year} as the current session")
                print(f"Marked {latest_session.year} as the current session")
            else:
                # Ensure only the latest remains current (clean up any duplicates)
                for s in all_sessions:
                    should_be_current = (s.id == latest_session.id)
                    if s.is_current != should_be_current:
                        s.is_current = should_be_current
                        updated_count += 1
                logger.info(f"Ensured only {latest_session.year} is marked current")
                print(f"Ensured only {latest_session.year} is marked current")

            db.session.commit()
            logger.info(
                f"Session setup complete. Created: {created_count}, "
                f"Updated: {updated_count}. Current session: {latest_session.year}"
            )
            print(
                f"Session setup complete. Created: {created_count}, "
                f"Updated: {updated_count}. Current session: {latest_session.year}"
            )

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create/update sessions: {str(e)}")
            print(f"Error: Failed to create/update sessions: {str(e)}")
            raise


if __name__ == "__main__":
    create_sessions()
