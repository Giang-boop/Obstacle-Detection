# === MO TA FILE ===
# server/app/routes/blind_persons.py
# CHUC NANG: /blind-persons theo quyen giam ho
# ===================

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..access import get_blind_person_or_403, visible_blind_persons_query
from ..extensions import db
from ..models import Alert, BlindPerson, Device, SosEvent, UsageSession
from ..pagination import paginate_query
from ..services import refresh_device_statuses

blind_persons_bp = Blueprint("blind_persons", __name__, url_prefix="/blind-persons")


@blind_persons_bp.get("")
@login_required
def list_blind_persons():
    refresh_device_statuses()
    pagination = paginate_query(visible_blind_persons_query(current_user).order_by(BlindPerson.id))
    page_ids = [person.id for person in pagination.items]
    alert_counts = {}
    if page_ids:
        alert_counts = dict(db.session.execute(
            db.select(Device.blind_person_id, db.func.count(Alert.id)).join(Alert, Alert.device_id == Device.id)
            .where(Device.blind_person_id.in_(page_ids)).group_by(Device.blind_person_id)
        ).all())
    return render_template("blind_persons/list.html", pagination=pagination, alert_counts=alert_counts)


@blind_persons_bp.get("/<int:blind_person_id>")
@login_required
def detail(blind_person_id):
    refresh_device_statuses()
    blind_person = get_blind_person_or_403(blind_person_id)
    device_ids = [device.id for device in blind_person.devices]
    recent_alerts = []
    recent_sessions = []
    recent_sos = []
    if device_ids:
        recent_alerts = db.session.scalars(
            db.select(Alert).where(Alert.device_id.in_(device_ids))
            .order_by(Alert.created_at.desc(), Alert.id.desc()).limit(10)
        ).all()
        recent_sessions = db.session.scalars(
            db.select(UsageSession).where(UsageSession.device_id.in_(device_ids))
            .order_by(UsageSession.started_at.desc()).limit(10)
        ).all()
        recent_sos = db.session.scalars(
            db.select(SosEvent).where(SosEvent.device_id.in_(device_ids))
            .order_by(SosEvent.created_at.desc()).limit(5)
        ).all()
    return render_template(
        "blind_persons/detail.html",
        blind_person=blind_person,
        recent_alerts=recent_alerts,
        recent_sessions=recent_sessions,
        recent_sos=recent_sos,
    )
