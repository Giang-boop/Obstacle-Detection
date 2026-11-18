# === MO TA FILE ===
# server/app/routes/sos.py
# CHUC NANG: /sos xu ly tin hieu cuu cuu
# ===================

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..access import can_access_device, visible_sos_query
from ..activity import log_activity
from ..extensions import db
from ..models import SOS_HANDLED, SOS_NEW, SosEvent, local_now
from ..pagination import paginate_query
from .auth import safe_next_url

sos_bp = Blueprint("sos", __name__, url_prefix="/sos")


@sos_bp.get("")
@login_required
def list_sos():
    status = request.args.get("status", "")
    query = visible_sos_query(current_user)
    if status in (SOS_NEW, SOS_HANDLED):
        query = query.where(SosEvent.status == status)
    query = query.order_by(db.case((SosEvent.status == SOS_NEW, 0), else_=1), SosEvent.created_at.desc())
    pagination = paginate_query(query.order_by(SosEvent.id.desc()))
    return render_template("sos/list.html", pagination=pagination, status=status)


@sos_bp.post("/<int:sos_id>/handle")
@login_required
def handle(sos_id):
    sos_event = db.get_or_404(SosEvent, sos_id)
    if not can_access_device(current_user, sos_event.device):
        abort(403)
    if sos_event.status == SOS_HANDLED:
        flash("Tín hiệu SOS này đã được xử lý trước đó.", "info")
        return redirect(url_for("sos.list_sos"))
    sos_event.status = SOS_HANDLED
    sos_event.handled_by = current_user.id
    sos_event.handled_at = local_now()
    sos_event.note = request.form.get("note", "").strip()[:1000] or None
    log_activity("sos_handled", f"Xử lý SOS #{sos_event.id} của thiết bị {sos_event.device.device_code}"
                 + (f": {sos_event.note}" if sos_event.note else ""))
    flash(f"Đã đánh dấu SOS #{sos_event.id} là đã xử lý.", "success")
    return redirect(safe_next_url(request.form.get("return_to")) or url_for("sos.list_sos"))
