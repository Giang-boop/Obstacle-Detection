# === MO TA FILE ===
# server/app/routes/statistics.py
# CHUC NANG: /statistics bieu do 14 ngay / loai vat / muc / vi tri
# ===================

from datetime import datetime, time, timedelta

from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required

from ..access import can_access_blind_person, visible_alerts_query, visible_blind_persons_query, visible_sessions_query
from ..extensions import db
from ..labels import LEVEL_LABELS, POSITION_LABELS
from ..models import Alert, Device, UsageSession, local_now

statistics_bp = Blueprint("statistics", __name__, url_prefix="/statistics")

DAYS_IN_CHART = 14


def restrict_to_blind_person(query, device_column, blind_person_id):
    if not blind_person_id:
        return query
    return query.where(device_column.in_(db.select(Device.id).where(Device.blind_person_id == blind_person_id)))


def build_statistics(blind_person_id):
    alerts_query = restrict_to_blind_person(visible_alerts_query(current_user), Alert.device_id, blind_person_id)
    alerts = alerts_query.subquery()

    today = local_now().date()
    first_day = today - timedelta(days=DAYS_IN_CHART - 1)
    day_column = db.func.date(alerts.c.created_at)
    per_day_rows = db.session.execute(
        db.select(day_column, alerts.c.level, db.func.count())
        .where(alerts.c.created_at >= datetime.combine(first_day, time.min))
        .group_by(day_column, alerts.c.level)
    ).all()
    day_keys = [(first_day + timedelta(days=offset)) for offset in range(DAYS_IN_CHART)]
    per_day = {"WARNING": {key.isoformat(): 0 for key in day_keys}, "DANGER": {key.isoformat(): 0 for key in day_keys}}
    for day_value, level, count in per_day_rows:
        if level in per_day and day_value in per_day[level]:
            per_day[level][day_value] = count

    class_rows = db.session.execute(
        db.select(alerts.c.class_code, db.func.max(alerts.c.class_name_vi), db.func.count())
        .group_by(alerts.c.class_code).order_by(db.func.count().desc())
    ).all()
    level_rows = dict(db.session.execute(
        db.select(alerts.c.level, db.func.count()).group_by(alerts.c.level)
    ).all())
    position_rows = dict(db.session.execute(
        db.select(alerts.c.position, db.func.count()).group_by(alerts.c.position)
    ).all())

    sessions = restrict_to_blind_person(
        visible_sessions_query(current_user), UsageSession.device_id, blind_person_id
    ).subquery()
    session_summary = db.session.execute(
        db.select(
            db.func.count(),
            db.func.avg(sessions.c.avg_fps),
            db.func.avg(sessions.c.avg_latency_ms),
        )
    ).one()

    total_alerts = sum(level_rows.values())
    return {
        "total_alerts": total_alerts,
        "danger_alerts": level_rows.get("DANGER", 0),
        "warning_alerts": level_rows.get("WARNING", 0),
        "session_count": session_summary[0] or 0,
        "avg_fps": session_summary[1],
        "avg_latency_ms": session_summary[2],
        "chart": {
            "days": [key.strftime("%d/%m") for key in day_keys],
            "per_day_warning": list(per_day["WARNING"].values()),
            "per_day_danger": list(per_day["DANGER"].values()),
            "class_labels": [(name or code) for code, name, _ in class_rows],
            "class_counts": [count for _, _, count in class_rows],
            "level_labels": [LEVEL_LABELS[key] for key in ("WARNING", "DANGER")],
            "level_counts": [level_rows.get(key, 0) for key in ("WARNING", "DANGER")],
            "position_labels": [POSITION_LABELS[key] for key in ("LEFT", "CENTER", "RIGHT")],
            "position_counts": [position_rows.get(key, 0) for key in ("LEFT", "CENTER", "RIGHT")],
        },
        "class_rows": class_rows,
    }


@statistics_bp.get("")
@login_required
def index():
    blind_person_id = request.args.get("blind_person_id", type=int)
    if blind_person_id and not can_access_blind_person(current_user, blind_person_id):
        abort(403)
    return render_template(
        "statistics/index.html",
        stats=build_statistics(blind_person_id),
        blind_persons=db.session.scalars(visible_blind_persons_query(current_user)).all(),
        selected_blind_person_id=blind_person_id,
        days_in_chart=DAYS_IN_CHART,
    )
