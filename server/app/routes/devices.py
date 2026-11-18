from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..access import get_device_or_403, visible_devices_query
from ..activity import log_activity
from ..extensions import db
from ..models import ObjectClass, local_now
from ..pagination import paginate_query
from ..services import ensure_device_config, refresh_device_statuses
from ..validation import parse_float_field, parse_int_field

devices_bp = Blueprint("devices", __name__, url_prefix="/devices")


@devices_bp.get("")
@login_required
def list_devices():
    refresh_device_statuses()
    pagination = paginate_query(visible_devices_query(current_user))
    return render_template("devices/list.html", pagination=pagination)


def read_config_form(form, known_class_codes):
    errors = []
    values = {
        "warning_distance": parse_float_field(form, "warning_distance", "Ngưỡng cảnh báo (WARNING)", 0.3, 20, errors),
        "danger_distance": parse_float_field(form, "danger_distance", "Ngưỡng nguy hiểm (DANGER)", 0.2, 10, errors),
        "tts_rate": parse_int_field(form, "tts_rate", "Tốc độ đọc thường", 80, 350, errors),
        "tts_rate_danger": parse_int_field(form, "tts_rate_danger", "Tốc độ đọc khẩn", 80, 400, errors),
        "tts_volume": parse_float_field(form, "tts_volume", "Âm lượng", 0, 1, errors),
        "short_messages": form.get("short_messages") == "on",
        "disabled_classes": sorted(code for code in form.getlist("disabled_classes") if code in known_class_codes),
    }
    if values["warning_distance"] is not None and values["danger_distance"] is not None:
        if values["danger_distance"] >= values["warning_distance"]:
            errors.append("Ngưỡng nguy hiểm phải nhỏ hơn ngưỡng cảnh báo.")
    return values, errors


def describe_config_changes(config, values):
    changes = []
    for field_name, new_value in values.items():
        old_value = getattr(config, field_name)
        if field_name == "disabled_classes":
            old_value = sorted(old_value or [])
        if old_value != new_value:
            changes.append(f"{field_name}: {old_value} → {new_value}")
    return changes


@devices_bp.route("/<int:device_id>/config", methods=["GET", "POST"])
@login_required
def edit_config(device_id):
    device = get_device_or_403(device_id)
    config = ensure_device_config(device)
    object_classes = db.session.scalars(db.select(ObjectClass).order_by(ObjectClass.name_vi)).all()
    known_class_codes = {item.code for item in object_classes}
    form_values = None
    if request.method == "POST":
        values, errors = read_config_form(request.form, known_class_codes)
        if errors:
            for message in errors:
                flash(message, "danger")
            form_values = values
        else:
            changes = describe_config_changes(config, values)
            for field_name, new_value in values.items():
                setattr(config, field_name, new_value)
            config.updated_at = local_now()
            config.updated_by = current_user.id
            log_activity("config_update", f"Cấu hình {device.device_code}: " + ("; ".join(changes) or "không thay đổi"))
            flash("Đã lưu cấu hình. Thiết bị sẽ áp dụng ở lần đồng bộ kế tiếp.", "success")
            return redirect(url_for("devices.edit_config", device_id=device.id))
    else:
        db.session.commit()
    return render_template(
        "devices/config.html",
        device=device,
        config=config,
        form_values=form_values,
        object_classes=object_classes,
    )
