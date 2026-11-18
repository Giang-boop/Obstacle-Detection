import csv
import io
from datetime import datetime, time, timedelta

from flask import Blueprint, Response, abort, render_template, request
from flask_login import current_user, login_required

from ..access import can_access_blind_person, visible_alerts_query, visible_blind_persons_query
from ..extensions import db
from ..labels import level_label, position_label
from ..models import ALERT_LEVELS, Alert, Device, ObjectClass, local_now
from ..pagination import paginate_query
from ..timeutils import format_datetime, parse_form_date

alerts_bp = Blueprint("alerts", __name__, url_prefix="/alerts")


def read_alert_filters(args):
    blind_person_id = args.get("blind_person_id", type=int)
    if blind_person_id and not can_access_blind_person(current_user, blind_person_id):
        abort(403)
    level = args.get("level", "").upper()
    return {
        "blind_person_id": blind_person_id,
        "date_from": parse_form_date(args.get("date_from")),
        "date_to": parse_form_date(args.get("date_to")),
        "level": level if level in ALERT_LEVELS else "",
        "class_code": args.get("class_code", "").strip(),
    }


def filtered_alerts_query(filters):
    query = visible_alerts_query(current_user)
    if filters["blind_person_id"]:
        query = query.where(Alert.device_id.in_(
            db.select(Device.id).where(Device.blind_person_id == filters["blind_person_id"])
        ))
    if filters["date_from"]:
        query = query.where(Alert.created_at >= datetime.combine(filters["date_from"], time.min))
    if filters["date_to"]:
        query = query.where(Alert.created_at < datetime.combine(filters["date_to"] + timedelta(days=1), time.min))
    if filters["level"]:
        query = query.where(Alert.level == filters["level"])
    if filters["class_code"]:
        query = query.where(Alert.class_code == filters["class_code"])
    return query.order_by(Alert.created_at.desc(), Alert.id.desc())


def filter_query_args(filters):
    result = {}
    for key, value in filters.items():
        if value:
            result[key] = value.isoformat() if hasattr(value, "isoformat") else value
    return result


@alerts_bp.get("")
@login_required
def list_alerts():
    filters = read_alert_filters(request.args)
    pagination = paginate_query(filtered_alerts_query(filters), "ALERTS_PER_PAGE")
    return render_template(
        "alerts/list.html",
        pagination=pagination,
        filters=filters,
        filter_args=filter_query_args(filters),
        blind_persons=db.session.scalars(visible_blind_persons_query(current_user)).all(),
        object_classes=db.session.scalars(db.select(ObjectClass).order_by(ObjectClass.name_vi)).all(),
    )


@alerts_bp.get("/export.csv")
@login_required
def export_csv():
    filters = read_alert_filters(request.args)
    alerts = db.session.scalars(filtered_alerts_query(filters)).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Mã", "Thời gian", "Người khiếm thị", "Mã thiết bị", "Mã lớp", "Vật cản", "Mức cảnh báo",
        "Khoảng cách (m)", "Vị trí", "TTC (s)", "Nội dung", "Phiên",
    ])
    for alert in alerts:
        device = alert.device
        writer.writerow([
            alert.id,
            format_datetime(alert.created_at),
            device.blind_person.full_name if device.blind_person else "",
            device.device_code,
            alert.class_code,
            alert.class_name_vi or "",
            level_label(alert.level),
            "" if alert.distance_m is None else f"{alert.distance_m:.2f}",
            position_label(alert.position) if alert.position else "",
            "" if alert.ttc_s is None else f"{alert.ttc_s:.2f}",
            alert.message or "",
            alert.session_id or "",
        ])
    content = "﻿" + buffer.getvalue()
    file_name = f"lich_su_canh_bao_{local_now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content.encode("utf-8"),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={file_name}",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
