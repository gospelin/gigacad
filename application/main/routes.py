from . import main_bp
from flask import redirect

@main_bp.route("/")
@main_bp.route("/index")
@main_bp.route("/home")
def index():
    return redirect("https://auntyannesschools.com.ng", code=301)


@main_bp.route("/about_us")
def about_us():
    return redirect("https://auntyannesschools.com.ng/about_us", code=301)
