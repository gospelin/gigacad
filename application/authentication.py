from flask_login import LoginManager
from flask import current_app as app
from sqlalchemy.exc import OperationalError

login_manager = LoginManager()
login_manager.login_message_category = "alert-info"

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    try:
        user_id_int = int(user_id)
        user = User.query.get(user_id_int)
        if user and user.active:
            app.logger.debug(f"User {user.username} (ID: {user_id}) loaded successfully")
            return user
        app.logger.debug(f"No active user found for ID: {user_id}")
        return None
    except ValueError as e:
        app.logger.warning(f"Invalid user_id format '{user_id}': {str(e)}")
        return None
    except OperationalError as e:
        app.logger.error(f"Database error loading user {user_id}: {str(e)}")
        return None
    except Exception as e:
        app.logger.error(f"Unexpected error loading user {user_id}: {str(e)}")
        return None