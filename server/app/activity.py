# === MO TA FILE ===
# server/app/activity.py
# CHUC NANG: Ghi nhat ky he thong: dang nhap, doi cau hinh, xu ly SOS
# ===================

from flask import has_request_context, request
from flask_login import current_user

from .extensions import db
from .models import ActivityLog


def client_ip_address():
    if not has_request_context():
        return None
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr


def log_activity(action, detail="", user=None, commit=True):
    actor = user
    if actor is None and has_request_context() and current_user and current_user.is_authenticated:
        actor = current_user
    entry = ActivityLog(
        user_id=actor.id if actor is not None else None,
        action=action,
        detail=detail,
        ip_address=client_ip_address(),
    )
    db.session.add(entry)
    if commit:
        db.session.commit()
    return entry
