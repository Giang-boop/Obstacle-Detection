# === MO TA FILE ===
# server/app/routes/dashboard.py
# CHUC NANG: / bang dieu khien: the so lieu, thiet bi, SOS, 10 canh bao moi
# ===================

from flask import Blueprint, current_app, render_template
from flask_login import current_user, login_required

from ..access import (
    visible_alerts_query,
    visible_blind_persons_query,
    visible_devices_query,
    visible_sos_query,
)
from ..extensions import db
from ..models import Alert, Device
from ..services import count_alerts_today, count_query, new_sos_query, refresh_device_statuses

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
@login_required
def index():
    refresh_device_statuses()
    devices = db.session.scalars(
        visible_devices_query(current_user).limit(current_app.config.get("DASHBOARD_DEVICE_LIMIT", 10))
    ).all()
    new_sos_events = db.session.scalars(new_sos_query(visible_sos_query(current_user)).limit(10)).all()
    latest_alerts = db.session.scalars(
        visible_alerts_query(current_user).order_by(Alert.created_at.desc(), Alert.id.desc()).limit(10)
    ).all()
    stats = {
        "blind_persons": count_query(visible_blind_persons_query(current_user)),
        "devices_total": count_query(visible_devices_query(current_user)),
        "devices_online": count_query(visible_devices_query(current_user).where(Device.status == "online")),
        "alerts_today": count_alerts_today(visible_alerts_query(current_user)),
        "sos_new": count_query(new_sos_query(visible_sos_query(current_user))),
    }
    return render_template(
        "dashboard/index.html",
        devices=devices,
        new_sos_events=new_sos_events,
        latest_alerts=latest_alerts,
        stats=stats,
    )
