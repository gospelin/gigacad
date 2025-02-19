from . import main_bp
from flask_wtf.csrf import CSRFError
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    Response,
    current_app as app
)
from ..models import Student, User, StudentClassHistory, Session
from ..auth.forms import StudentRegistrationForm

from ..helpers import (
    db,
    random,
    string,
)

@main_bp.route("/")
@main_bp.route("/index")
@main_bp.route("/home")
def index():
    # return render_template(
    #     "main/index.html", title="Home", school_name="Aunty Anne's International School"
    # )
    return redirect("https://auntyannesschools.com.ng", code=301)


@main_bp.route("/about_us")
def about_us():
    # return render_template(
    #     "main/about_us.html", title="About Us", school_name="Aunty Anne's International School"
    # )
    return redirect("https://auntyannesschools.com.ng/about_us", code=301)

# @main_bp.route('/sitemap.xml')
# def sitemap():
#     # Example list of static routes (add dynamic URLs as needed)
#     urls = [
#         {'loc': url_for('main.index', _external=True), 'lastmod': '2025-01-01'},
#         {'loc': url_for('main.about_us', _external=True), 'lastmod': '2025-01-01'},
#         {'loc': url_for('students.student_portal', _external=True), 'lastmod': '2025-01-01'},
#         {'loc': url_for('auth.login', _external=True), 'lastmod': '2025-01-03'},
#         {'loc': url_for('main.student_registration', _external=True), 'lastmod': '2024-12-23'},
#         {'loc': url_for('admins.admin_dashboard', _external=True), 'lastmod': '2025-01-03'}
#     ]

#     # Generate XML
#     xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
#     for url in urls:
#         xml.append(f"<url><loc>{url['loc']}</loc><lastmod>{url['lastmod']}</lastmod></url>")
#     xml.append('</urlset>')

#     return Response("\n".join(xml), content_type='application/xml')

# @app.route('/sitemap.xml')
# def sitemap():
#     pages = [
#         {
#             'loc': 'https://auntyannesschools.com.ng/',
#             'priority': '1.0',
#             'changefreq': 'daily'
#         },
#         {
#             'loc': 'https://auntyannesschools.com.ng/about',
#             'priority': '0.8',
#             'changefreq': 'monthly'
#         },
#         # Add more pages here
#     ]
#     sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
#     sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

#     for page in pages:
#         sitemap_xml += f"""
#         <url>
#             <loc>{page['loc']}</loc>
#             <priority>{page['priority']}</priority>
#             <changefreq>{page['changefreq']}</changefreq>
#         </url>
#         """

#     sitemap_xml += '</urlset>'
#     return Response(sitemap_xml, mimetype='application/xml')

@main_bp.route('/sitemap.xml')
def sitemap():
    # Static URLs
    static_urls = [
        {'loc': url_for('main.index', _external=True), 'lastmod': '2025-01-26', 'priority': '1.0', 'changefreq': 'hourly'},
        {'loc': url_for('main.about_us', _external=True), 'lastmod': '2025-01-26', 'priority': '0.9', 'changefreq': 'hourly'},
        {'loc': url_for('students.student_portal', _external=True), 'lastmod': '2025-01-26', 'priority': '0.8', 'changefreq': 'weekly'},
        {'loc': url_for('auth.login', _external=True), 'lastmod': '2025-01-26', 'priority': '0.5', 'changefreq': 'monthly'},
        {'loc': url_for('main.student_registration', _external=True), 'lastmod': '2024-12-23', 'priority': '0.7', 'changefreq': 'monthly'},
        {'loc': url_for('admins.admin_dashboard', _external=True), 'lastmod': '2025-01-03', 'priority': '0.6', 'changefreq': 'weekly'}
    ]

    # Additional dynamic URLs (if needed)
    # dynamic_urls = get_dynamic_urls()  # Implement a function to fetch dynamic URLs
    # Combine static and dynamic URLs
    urls = static_urls  # + dynamic_urls

    # Generate XML
    sitemap_xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        sitemap_xml.append(f"""
        <url>
            <loc>{url['loc']}</loc>
            <lastmod>{url['lastmod']}</lastmod>
            <priority>{url['priority']}</priority>
            <changefreq>{url['changefreq']}</changefreq>
        </url>
        """)
    sitemap_xml.append('</urlset>')

    return Response("\n".join(sitemap_xml), content_type='application/xml')


@main_bp.route("/register/student", methods=["GET", "POST"])
def student_registration():
    form = StudentRegistrationForm()
    current_session = (
        Session.get_current_session()
    )
    try:
        if form.validate_on_submit():
            temporary_password = "".join(
                random.choices(string.ascii_letters + string.digits, k=8)
            )

            # Create the Student object
            student = Student(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                middle_name=form.middle_name.data,
                gender=form.gender.data,
                date_of_birth=form.date_of_birth.data,
                parent_name=form.parent_name.data,
                parent_phone_number=form.parent_phone_number.data,
                address=form.address.data,
                parent_occupation=form.parent_occupation.data,
                state_of_origin=form.state_of_origin.data,
                local_government_area=form.local_government_area.data,
                religion=form.religion.data,
                username=username,
                password=temporary_password,
                approved=False,
            )

            # Create a User object for login credentials
            user = User(username=student.username, is_admin=False)
            user.set_password(temporary_password)  # Hash the temporary password
            student.user = user  # Link user to the student

            # Add the student and user to the session
            db.session.add(student)
            db.session.add(user)
            db.session.flush()  # Ensure student gets an ID before creating the class history

            # Add entry to StudentClassHistory to track class for the current session
            class_history = StudentClassHistory(
                student_id=student.id,
                session_id=current_session.id,  # Store session ID from current session
                class_name=form.class_name.data,  # Store the class entered during registration
            )
            db.session.add(class_history)

            # Commit all changes (student, user, class history)
            db.session.commit()

            # Log success and inform the user
            app.logger.info(f"Student registered successfully: {username}")
            flash(
                f"Student registered successfully. Username: {username}, Password: {temporary_password}",
                "alert alert-success",
            )
            return redirect(url_for("main.student_registration"))

    except Exception as e:
        db.session.rollback()  # Rollback the session on error
        app.logger.error(f"Error registering student: {str(e)}")
        flash("An error occurred. Please try again later.", "alert alert-danger")

    return render_template(
        "student/student_registration.html",
        title="Register",
        form=form,
        school_name="Aunty Anne's Int'l School",
    )


# CSRF error handler
@main_bp.errorhandler(CSRFError)
def handle_csrf_error(e):
    app.logger.warning(f"CSRF error: {e.description}")
    flash("The form submission has expired. Please try again.", "alert alert-danger")
    return redirect(url_for("main.student_registration"))
