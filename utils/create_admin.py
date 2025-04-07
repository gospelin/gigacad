import sys
import os
import logging
from dotenv import load_dotenv
import pyotp


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('admin_setup')

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
from application.models import User, RoleEnum, AdminPrivilege, AuditLog

def create_or_update_admin_user():
    """Create or update an admin user with full privileges and MFA support."""
    app = create_app('production')

    with app.app_context():
        username = "teacher"
        password = "Password@123"  # Ensure this meets your password policy

        try:
            # Check if the admin user exists
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                # Create a new admin user
                admin = User(username=username)
                admin.set_password(password)  # Uses flask-bcrypt
                admin.role = RoleEnum.ADMIN.value
                admin.active = True
                admin.mfa_secret = pyotp.random_base32()  # Add MFA secret
                db.session.add(admin)
                db.session.flush()
                logger.info(f"Admin user created with username: {username}")
                print(f"Admin user created with username: {username}")
                print(f"MFA Secret: {admin.mfa_secret} - Save this for authenticator app setup")
            else:
                # Update existing admin user
                admin = existing_user
                try:
                    if not admin.check_password(password):
                        admin.set_password(password)
                        logger.info(f"Password updated for admin user: {username}")
                        print(f"Password updated for admin user: {username}")
                    else:
                        logger.info(f"Admin user: {username} already exists with correct password")
                        print(f"Admin user: {username} already exists with correct password")
                except ValueError as e:
                    # Handle invalid salt by resetting password
                    logger.warning(f"Invalid password hash detected for {username}: {str(e)}. Resetting password.")
                    admin.set_password(password)
                    logger.info(f"Password reset for admin user: {username} due to invalid hash")
                    print(f"Password reset for admin user: {username} due to invalid hash")
                admin.role = RoleEnum.ADMIN.value
                admin.active = True
                if not admin.mfa_secret:
                    admin.mfa_secret = pyotp.random_base32()
                    logger.info(f"MFA secret added for admin: {username}")
                    print(f"MFA Secret: {admin.mfa_secret} - Save this for authenticator app setup")

            # Check and update privileges
            privileges = AdminPrivilege.query.filter_by(user_id=admin.id).first()
            if not privileges:
                privileges = AdminPrivilege(
                    user_id=admin.id,
                    can_manage_users=True,
                    can_manage_sessions=True,
                    can_manage_classes=True,
                    can_manage_results=True,
                    can_manage_teachers=True,
                    can_manage_subjects=True,
                    can_view_reports=True,
                )
                db.session.add(privileges)
                logger.info(f"Privileges created for admin: {username} with all privileges enabled")
                print(f"Privileges created for admin: {username} with all privileges enabled")
            else:
                privileges.can_manage_users = True
                privileges.can_manage_sessions = True
                privileges.can_manage_classes = True
                privileges.can_manage_results = True
                privileges.can_manage_teachers = True
                privileges.can_manage_subjects = True
                privileges.can_view_reports = True
                logger.info(f"Privileges updated for admin: {username} to enable all privileges")
                print(f"Privileges updated for admin: {username} to enable all privileges")

            # Add audit log entry
            action = "Admin user created" if not existing_user else "Admin user updated"
            db.session.add(AuditLog(user_id=admin.id, action=action))
            logger.info(f"Audit log entry added: {action} for {username}")

            # Commit all changes
            db.session.commit()
            logger.info(f"Admin user {username} fully configured with all privileges and MFA")
            print(f"Admin user {username} fully configured with all privileges and MFA")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to configure admin user {username}: {str(e)}")
            print(f"Error: Failed to configure admin user {username}: {str(e)}")
            raise

if __name__ == "__main__":
    create_or_update_admin_user()