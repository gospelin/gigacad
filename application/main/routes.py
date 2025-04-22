from flask import Blueprint, render_template, redirect, current_app
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
        return render_template('layout.html', current_time=current_time)
    return redirect("https://auntyannesschools.com.ng", code=301)

@main_bp.route("/about_us")
def about_us():
    return redirect("https://auntyannesschools.com.ng/about_us", code=301)