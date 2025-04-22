from flask import (
    render_template, redirect, url_for, flash, request, current_app as app, session, Response
)
from flask_login import login_user, current_user, login_required, logout_user
from sqlalchemy.exc import OperationalError
from . import auth_bp
from ..models import User, RoleEnum, AuditLog
from .. import db
from .forms import StudentLoginForm, AdminLoginForm
import bleach
from application import limiter
import pyotp
import qrcode
from io import BytesIO
import base64

@auth_bp.route("/portal", methods=["GET", "POST"])
@auth_bp.route("/portal/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        if not current_user.mfa_secret or session.get('mfa_verified', False):
            return redirect_based_on_role(current_user)
        return redirect(url_for("auth.mfa_verify"))

    student_form = StudentLoginForm()
    admin_form = AdminLoginForm()

    if request.method == "POST":
        form = student_form if student_form.validate_on_submit() else admin_form if admin_form.validate_on_submit() else None
        if form:
            username = bleach.clean(form.identifier.data if hasattr(form, 'identifier') else form.username.data)
            password = form.password.data
            remember = form.remember.data

            try:
                user = User.query.filter_by(username=username).first()
                if not user:
                    flash("User not found. Please check your username.", "alert-danger")
                    app.logger.warning(f"Login attempt with non-existent username: {username}")
                elif not user.check_password(password):
                    flash("Invalid password. Please try again.", "alert-danger")
                    app.logger.warning(f"Failed password attempt for user: {username}")
                elif not user.active:
                    flash("Account is inactive. Contact admin.", "alert-danger")
                    app.logger.warning(f"Inactive account login attempt: {username}")
                else:
                    login_user(user, remember=remember)
                    app.logger.info(f"User {username} logged in successfully with remember={remember}.")
                    db.session.add(AuditLog(user_id=user.id, action="Logged in"))
                    db.session.commit()
                    if user.mfa_secret:
                        return redirect(url_for("auth.mfa_verify"))
                    return redirect_based_on_role(user)
            except OperationalError as e:
                db.session.rollback()
                app.logger.error(f"Database connection lost during login for {username}: {str(e)}")
                flash("Database unavailable. Please try again later.", "alert-danger")
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Unexpected error during login for {username}: {str(e)}")
                flash("An unexpected error occurred. Please try again or contact support.", "alert-danger")

    return render_template("auth/login.html", title="Login", student_form=student_form, admin_form=admin_form)

@auth_bp.route("/mfa_verify", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute")
def mfa_verify():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.logout"))

    if not current_user.mfa_secret or session.get('mfa_verified', False):
        return redirect_based_on_role(current_user)

    totp = pyotp.TOTP(current_user.mfa_secret)
    qr_code_url = None

    if not session.get('mfa_setup_complete', False):
        provisioning_uri = totp.provisioning_uri(
            name=current_user.username,
            issuer_name=app.config.get("SCHOOL_NAME", "Aunty Anne's International School")
        )
        qr = qrcode.make(provisioning_uri)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        qr_code_url = f"data:image/png;base64,{qr_code_base64}"

    if request.method == "POST":
        mfa_code = bleach.clean(request.form.get("mfa_code", ""))
        try:
            if totp.verify(mfa_code):
                session['mfa_verified'] = True
                session['mfa_setup_complete'] = True
                db.session.add(AuditLog(user_id=current_user.id, action="MFA verified"))
                db.session.commit()
                app.logger.info(f"MFA verified for user {current_user.username}")
                flash("MFA verification successful.", "alert-success")
                return redirect_based_on_role(current_user)
            else:
                app.logger.warning(f"Invalid MFA code attempt for user {current_user.username}")
                flash("Invalid MFA code. Ensure your device time is synced and try again.", "alert-danger")
        except Exception as e:
            app.logger.error(f"Error verifying MFA for {current_user.username}: {str(e)}")
            flash("An error occurred during MFA verification.", "alert-danger")

    form = AdminLoginForm()
    return render_template("admin/mfa_verify.html", title="MFA Verification", qr_code_url=qr_code_url, mfa_secret=current_user.mfa_secret if not qr_code_url else None, form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    username = current_user.username
    db.session.add(AuditLog(user_id=current_user.id, action="Logged out"))
    db.session.commit()
    app.logger.info(f"User {username} logged out.")
    logout_user()
    session.pop('mfa_verified', None)
    session.pop('mfa_setup_complete', None)
    session.clear()
    response = redirect(url_for("auth.login"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.set_cookie(app.config['SESSION_COOKIE_NAME'], '', expires=0, path=app.config['SESSION_COOKIE_PATH'], httponly=app.config['SESSION_COOKIE_HTTPONLY'], secure=app.config['SESSION_COOKIE_SECURE'], samesite=app.config['SESSION_COOKIE_SAMESITE'])
    flash("You have been logged out.", "alert-success")
    return response

def redirect_based_on_role(user):
    if not user.is_authenticated:
        return redirect(url_for("auth.logout"))

    role_map = {
        RoleEnum.ADMIN.value: "admins.admin_dashboard",
        RoleEnum.STUDENT.value: "students.student_portal",
        RoleEnum.TEACHER.value: "teachers.teacher_dashboard"
    }
    endpoint = role_map.get(user.role)
    if endpoint:
        return redirect(url_for(endpoint))

    logout_user()
    session.clear()
    db.session.add(AuditLog(user_id=user.id, action="Logout due to invalid role"))
    db.session.commit()
    app.logger.warning(f"Invalid role detected for user {user.username}: {user.role}")
    flash("Invalid user role detected. Contact admin.", "alert-danger")
    return redirect(url_for("auth.login"))