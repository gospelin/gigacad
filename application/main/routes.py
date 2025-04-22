from flask import Blueprint, render_template, redirect, current_app, session
from flask_login import current_user
from datetime import datetime
import pytz

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
@main_bp.route("/index")
@main_bp.route("/home")
def index():
    if current_app.config.get("TESTING", False):
        nigeria_tz = pytz.timezone("Africa/Lagos")
        current_time = datetime.now(nigeria_tz).strftime("%d %B %Y")
        # Touch the session for authenticated users to include Set-Cookie header
        if current_user.is_authenticated:
            session["last_access"] = datetime.utcnow().isoformat()
            current_app.logger.info(f"Index page accessed by user {current_user.username}")
        else:
            current_app.logger.info("Index page accessed by anonymous user")
        return render_template('main/index.html', current_time=current_time)
    return redirect("https://auntyannesschools.com.ng", code=301)

@main_bp.route("/about_us")
def about_us():
    return redirect("https://auntyannesschools.com.ng/about_us", code=301)