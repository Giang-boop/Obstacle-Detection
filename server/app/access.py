# === MO TA FILE ===
# server/app/access.py
# CHUC NANG: Phan quyen admin_required + quyen giam ho nguoi than (403 neu sai)
# ===================

from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from .extensions import db
from .models import Alert, BlindPerson, Device, Guardianship, SosEvent, UsageSession


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def visible_blind_person_ids(user):
    if user.is_admin:
        return None
    rows = db.session.execute(db.select(Guardianship.blind_person_id).where(Guardianship.user_id == user.id))
    return [row[0] for row in rows]


def can_access_blind_person(user, blind_person_id):
    if user.is_admin:
        return True
    allowed_ids = visible_blind_person_ids(user)
    return blind_person_id in allowed_ids


def can_access_device(user, device):
    if user.is_admin:
        return True
    if device.blind_person_id is None:
        return False
    return can_access_blind_person(user, device.blind_person_id)


def get_blind_person_or_403(blind_person_id):
    blind_person = db.get_or_404(BlindPerson, blind_person_id)
    if not can_access_blind_person(current_user, blind_person.id):
        abort(403)
    return blind_person


def get_device_or_403(device_id):
    device = db.get_or_404(Device, device_id)
    if not can_access_device(current_user, device):
        abort(403)
    return device


def visible_blind_persons_query(user):
    query = db.select(BlindPerson).order_by(BlindPerson.full_name)
    allowed_ids = visible_blind_person_ids(user)
    if allowed_ids is not None:
        query = query.where(BlindPerson.id.in_(allowed_ids))
    return query


def scope_by_device(query, user, device_column):
    allowed_ids = visible_blind_person_ids(user)
    if allowed_ids is None:
        return query
    allowed_device_ids = db.select(Device.id).where(Device.blind_person_id.in_(allowed_ids))
    return query.where(device_column.in_(allowed_device_ids))


def visible_devices_query(user):
    query = db.select(Device).order_by(Device.device_code)
    allowed_ids = visible_blind_person_ids(user)
    if allowed_ids is not None:
        query = query.where(Device.blind_person_id.in_(allowed_ids))
    return query


def visible_alerts_query(user):
    return scope_by_device(db.select(Alert), user, Alert.device_id)


def visible_sos_query(user):
    return scope_by_device(db.select(SosEvent), user, SosEvent.device_id)


def visible_sessions_query(user):
    return scope_by_device(db.select(UsageSession), user, UsageSession.device_id)
