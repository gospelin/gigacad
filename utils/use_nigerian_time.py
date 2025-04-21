import sys
import os
import logging
from dotenv import load_dotenv
import pytz
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('admin_setup')

PROJECT_HOME = os.getenv("PROJECT_HOME", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)
    logger.info(f"Added {PROJECT_HOME} to sys.path")

env_path = os.path.join(PROJECT_HOME, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f"No .env file found at {env_path}. Using defaults.")

from application import create_app, db
from application.models import StudentClassHistory, Student, StudentTermSummary, Result, AuditLog

NIGERIA_TZ = pytz.timezone('Africa/Lagos')

def use_nigerian_time():
    app = create_app('production')
    
    with app.app_context():
        for model in [StudentClassHistory, Student, StudentTermSummary, Result, AuditLog]:
            logger.info(f"Processing model: {model.__name__}")
            records_updated = 0
            for record in model.query.all():
                for col in ['join_date', 'leave_date', 'date_registered', 'created_at', 'timestamp']:
                    if hasattr(record, col) and getattr(record, col):
                        utc_time = getattr(record, col)
                        # Handle string timestamps
                        if isinstance(utc_time, str):
                            try:
                                utc_time = datetime.strptime(utc_time, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                logger.error(f"Skipping unparseable timestamp {utc_time} in {model.__name__}.{col}")
                                continue
                        # Ensure the time is naive or UTC before conversion
                        if utc_time.tzinfo is None:
                            utc_time = pytz.UTC.localize(utc_time)
                        wat_time = utc_time.astimezone(NIGERIA_TZ)
                        setattr(record, col, wat_time)
                        records_updated += 1
            logger.info(f"Updated {records_updated} timestamp fields in {model.__name__}")
        db.session.commit()
        logger.info("Database commit successful")

if __name__ == "__main__":
    use_nigerian_time()