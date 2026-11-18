from flask import Blueprint, jsonify, url_for
from flask_login import current_user, login_required

from ..access import visible_alerts_query, visible_devices_query, visible_sos_query
from ..extensions import db
from ..labels import STATUS_LABELS
from ..models import Device
from ..services import count_alerts_today, count_query, new_sos_query, refresh_device_statuses
from ..timeutils import format_datetime, to_iso

web_api_bp = Blueprint("web_api", __name__, url_prefix="/api/web")


@web_api_bp.get("/summary")
@login_required
def summary():
    refresh_device_statuses()
    sos_events = db.session.scalars(new_sos_query(visible_sos_query(current_user)).limit(20)).all()
    online_devices = count_query(visible_devices_query(current_user).where(Device.status == "online"))
    devices = []
    for device in db.session.scalars(visible_devices_query(current_user)).all():
        status = device.effective_status
        devices.append({
            "id": device.id,
            "status": status,
            "status_label": STATUS_LABELS[status],
            "last_seen_at": to_iso(device.last_seen_at),
            "last_seen_text": format_datetime(device.last_seen_at),
        })
    new_sos = []
    for sos_event in sos_events:
        device = sos_event.device
        new_sos.append({
            "id": sos_event.id,
            "created_at": to_iso(sos_event.created_at),
            "created_at_text": format_datetime(sos_event.created_at),
            "device_code": device.device_code,
            "device_name": device.name,
            "blind_person": device.blind_person.full_name if device.blind_person else None,
            "url": url_for("sos.list_sos"),
        })
    return jsonify({
        "new_sos": new_sos,
        "online_devices": online_devices,
        "devices": devices,
        "alerts_today": count_alerts_today(visible_alerts_query(current_user)),
    })
