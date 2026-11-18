# === MO TA FILE ===
# server/app/routes/sessions.py
# CHUC NANG: /sessions phien su dung (FPS, do tre, so canh bao)
# ===================

from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required

from ..access import can_access_blind_person, visible_blind_persons_query, visible_sessions_query
from ..extensions import db
from ..models import Device, UsageSession
from ..pagination import paginate_query

sessions_bp = Blueprint("sessions", __name__, url_prefix="/sessions")


@sessions_bp.get("")
@login_required
def list_sessions():
    blind_person_id = request.args.get("blind_person_id", type=int)
    if blind_person_id and not can_access_blind_person(current_user, blind_person_id):
        abort(403)
    query = visible_sessions_query(current_user)
    if blind_person_id:
        query = query.where(UsageSession.device_id.in_(
            db.select(Device.id).where(Device.blind_person_id == blind_person_id)
        ))
    query = query.order_by(UsageSession.started_at.desc(), UsageSession.id.desc())
    pagination = paginate_query(query)
    return render_template(
        "sessions/list.html",
        pagination=pagination,
        blind_persons=db.session.scalars(visible_blind_persons_query(current_user)).all(),
        selected_blind_person_id=blind_person_id,
    )
