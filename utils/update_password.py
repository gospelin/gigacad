import sys
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('update_student_details')

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

from application import create_app, db, bcrypt
from application.models import Student, User, RoleEnum, AuditLog

def update_student_details():
    """
    Update student user accounts to ensure usernames match reg_no and passwords are hashed with bcrypt.
    Logs all actions and maintains audit trails.
    """
    app = create_app('production')

    with app.app_context():
        try:
            students = Student.query.all()
            if not students:
                logger.info("No students found in the database.")
                print("No students found in the database.")
                return

            for student in students:
                if not student.reg_no:
                    logger.warning(f"Student ID {student.id} has no reg_no. Skipping.")
                    print(f"Student ID {student.id} has no reg_no. Skipping.")
                    continue

                user = db.session.get(User, student.user_id)
                if not user:
                    logger.warning(f"No linked User found for Student ID {student.id}. Creating new user.")
                    print(f"No linked User found for Student ID {student.id}. Creating new user.")
                    user = User(
                        username=student.reg_no,
                        role=RoleEnum.STUDENT.value,
                        active=True
                    )
                    user.set_password(student.reg_no)  # Hash with bcrypt
                    student.user = user
                    db.session.add(user)
                    db.session.flush()
                    db.session.add(AuditLog(user_id=user.id, action=f"Created user for student {student.reg_no}"))
                    logger.info(f"Created new user for Student ID {student.id}: {student.reg_no}")
                    print(f"Created new user for Student ID {student.id}: {student.reg_no}")
                else:
                    try:
                        user.check_password(student.reg_no)  # Test if password is already correct
                        logger.info(f"Password for Student ID {student.id} ({student.reg_no}) is already correct.")
                        print(f"Password for Student ID {student.id} ({student.reg_no}) is already correct.")
                    except ValueError as e:
                        logger.warning(f"Invalid password hash for Student ID {student.id} ({student.reg_no}): {str(e)}. Re-hashing.")
                        print(f"Invalid password hash for Student ID {student.id} ({student.reg_no}): {str(e)}. Re-hashing.")
                        user.set_password(student.reg_no)  # Re-hash with bcrypt
                        db.session.add(AuditLog(user_id=user.id, action=f"Re-hashed password for student {student.reg_no}"))
                        logger.info(f"Re-hashed password for Student ID {student.id}: {student.reg_no}")
                        print(f"Re-hashed password for Student ID {student.id}: {student.reg_no}")

                    # Update username and role
                    user.username = student.reg_no
                    user.role = RoleEnum.STUDENT.value
                    user.active = True
                    db.session.add(AuditLog(user_id=user.id, action=f"Updated username for student {student.reg_no}"))
                    logger.info(f"Username updated for Student ID {student.id}: {student.reg_no}")
                    print(f"Username updated for Student ID {student.id}: {student.reg_no}")

            db.session.commit()
            logger.info("All student details have been updated successfully.")
            print("All student details have been updated successfully.")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update student details: {str(e)}")
            print(f"Error: Failed to update student details: {str(e)}")
            raise

if __name__ == "__main__":
    update_student_details()