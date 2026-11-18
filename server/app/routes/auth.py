# === MO TA FILE ===
# server/app/routes/auth.py
# CHUC NANG: /login /logout /profile, doi mat khau, nhat ky dang nhap
# ===================

from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..activity import log_activity
from ..extensions import db
from ..models import User, local_now
from ..validation import validate_email, validate_new_password, validate_phone

auth_bp = Blueprint("auth", __name__)


def safe_next_url(target):
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/"):
        return None
    return target


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    username = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.session.scalar(db.select(User).where(User.username == username))
        if user is None or not user.check_password(password):
            log_activity("login_failed", f"Sai tên đăng nhập hoặc mật khẩu: {username}", user=None)
            flash("Tên đăng nhập hoặc mật khẩu không đúng.", "danger")
        elif not user.is_active:
            log_activity("login_failed", f"Tài khoản bị khóa: {username}", user=user)
            flash("Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.", "danger")
        else:
            login_user(user, remember=bool(request.form.get("remember")))
            user.last_login_at = local_now()
            log_activity("login", f"{user.full_name} đăng nhập", user=user)
            return redirect(safe_next_url(request.args.get("next")) or url_for("dashboard.index"))
    return render_template("auth/login.html", username=username)


@auth_bp.post("/logout")
@login_required
def logout():
    log_activity("logout", f"{current_user.full_name} đăng xuất")
    logout_user()
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        form_name = request.form.get("form_name")
        if form_name == "profile":
            update_profile()
        elif form_name == "password":
            change_password()
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html")


def update_profile():
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    errors = []
    if not full_name:
        errors.append("Họ tên không được để trống.")
    errors += validate_email(email) + validate_phone(phone)
    if errors:
        for message in errors:
            flash(message, "danger")
        return
    current_user.full_name = full_name
    current_user.email = email or None
    current_user.phone = phone or None
    log_activity("profile_update", f"{current_user.username} cập nhật hồ sơ")
    flash("Đã cập nhật hồ sơ.", "success")


def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    if not current_user.check_password(current_password):
        flash("Mật khẩu hiện tại không đúng.", "danger")
        return
    errors = validate_new_password(new_password, confirm_password)
    if errors:
        for message in errors:
            flash(message, "danger")
        return
    current_user.set_password(new_password)
    log_activity("password_change", f"{current_user.username} đổi mật khẩu")
    flash("Đã đổi mật khẩu.", "success")
