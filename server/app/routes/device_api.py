# === MO TA FILE ===
# server/app/routes/device_api.py
# CHUC NANG: REST API thiet bi: hello, config, heartbeat, sessions, alerts, sos, detect (JPEG->YOLO)
# ===================

import time
from datetime import timedelta
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request

from ..activity import log_activity
from ..extensions import db
from ..models import ALERT_LEVELS, ALERT_POSITIONS, Alert, Device, ObjectClass, SosEvent, UsageSession, local_now
from ..services import device_config_payload, ensure_device_config, touch_device
from ..timeutils import parse_client_datetime, to_iso
from ..web_detection import (
    InvalidFrameError,
    ModelUnavailableError,
    build_alert_record,
    build_detection_response,
    decode_frame,
    get_engine,
    get_session_store,
    scale_to_reference,
)

device_api_bp = Blueprint("device_api", __name__, url_prefix="/api/device")


def json_error(message, status_code):
    return jsonify({"error": message}), status_code


def device_key_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        api_key = (request.headers.get("X-Device-Key") or "").strip()
        device = None
        if api_key:
            device = db.session.scalar(db.select(Device).where(Device.api_key == api_key))
        if device is None:
            return json_error("Mã thiết bị không hợp lệ", 401)
        g.device = device
        return view(*args, **kwargs)

    return wrapped


def request_json():
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def optional_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def optional_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def save_alert_items(device, session_id, items):
    vietnamese_names = dict(db.session.execute(db.select(ObjectClass.code, ObjectClass.name_vi)).all())
    saved_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        class_code = str(item.get("class_code") or "").strip()[:60]
        level = str(item.get("level") or "").upper()
        if not class_code or level not in ALERT_LEVELS:
            continue
        position = str(item.get("position") or "").upper()
        db.session.add(Alert(
            device_id=device.id,
            session_id=session_id,
            class_code=class_code,
            class_name_vi=(item.get("class_name_vi") or vietnamese_names.get(class_code) or class_code)[:120],
            level=level,
            distance_m=optional_float(item.get("distance_m")),
            position=position if position in ALERT_POSITIONS else None,
            ttc_s=optional_float(item.get("ttc_s")),
            message=(str(item.get("message"))[:255] if item.get("message") else None),
            created_at=parse_client_datetime(item.get("created_at"), local_now()),
        ))
        saved_count += 1
    return saved_count


@device_api_bp.post("/hello")
@device_key_required
def hello():
    payload = request_json()
    device = g.device
    expected_code = str(payload.get("device_code") or "").strip()
    if expected_code and expected_code.upper() != (device.device_code or "").upper():
        return json_error("Mã thiết bị và khóa thiết bị không khớp", 401)
    touch_device(device, payload.get("app_version"), payload.get("model_name"))
    ensure_device_config(device)
    db.session.commit()
    blind_person = device.blind_person
    return jsonify({
        "device": {"id": device.id, "name": device.name, "device_code": device.device_code},
        "blind_person": {"id": blind_person.id, "full_name": blind_person.full_name} if blind_person else None,
        "config": device_config_payload(device),
    })


@device_api_bp.get("/config")
@device_key_required
def get_config():
    device = g.device
    touch_device(device)
    payload = device_config_payload(device)
    db.session.commit()
    return jsonify(payload)


@device_api_bp.post("/heartbeat")
@device_key_required
def heartbeat():
    device = g.device
    touch_device(device)
    config = ensure_device_config(device)
    db.session.commit()
    return jsonify({"ok": True, "config_updated_at": to_iso(config.updated_at)})


@device_api_bp.post("/sessions")
@device_key_required
def create_session():
    payload = request_json()
    device = g.device
    touch_device(device)
    usage_session = UsageSession(
        device_id=device.id,
        started_at=parse_client_datetime(payload.get("started_at"), local_now()),
        model_name=(str(payload.get("model_name"))[:120] if payload.get("model_name") else device.model_name),
    )
    db.session.add(usage_session)
    db.session.commit()
    return jsonify({"session_id": usage_session.id})


@device_api_bp.put("/sessions/<int:session_id>")
@device_key_required
def close_session(session_id):
    payload = request_json()
    device = g.device
    usage_session = db.session.get(UsageSession, session_id)
    if usage_session is None or usage_session.device_id != device.id:
        return json_error("Không tìm thấy phiên sử dụng", 404)
    touch_device(device)
    usage_session.ended_at = parse_client_datetime(payload.get("ended_at"), local_now())
    web_state = get_session_store(current_app).pop(usage_session.id)
    if web_state is not None:
        for field_name, value in web_state.stats().items():
            if field_name not in payload:
                setattr(usage_session, field_name, value)
    for field_name in ("frames", "alert_count"):
        if field_name in payload:
            setattr(usage_session, field_name, optional_int(payload.get(field_name)))
    for field_name in ("avg_fps", "avg_latency_ms"):
        if field_name in payload:
            setattr(usage_session, field_name, optional_float(payload.get(field_name)))
    db.session.commit()
    return jsonify({"ok": True})


@device_api_bp.post("/alerts")
@device_key_required
def create_alerts():
    payload = request_json()
    device = g.device
    items = payload.get("items")
    if not isinstance(items, list):
        return json_error("Trường items phải là danh sách", 400)
    max_items = current_app.config.get("MAX_ALERT_ITEMS_PER_REQUEST", 500)
    if len(items) > max_items:
        return json_error(f"Tối đa {max_items} cảnh báo mỗi lần gửi", 400)

    session_id = optional_int(payload.get("session_id"))
    if session_id is not None:
        usage_session = db.session.get(UsageSession, session_id)
        if usage_session is None or usage_session.device_id != device.id:
            session_id = None

    saved_count = save_alert_items(device, session_id, items)
    touch_device(device)
    db.session.commit()
    return jsonify({"saved": saved_count})


@device_api_bp.post("/sos")
@device_key_required
def create_sos():
    payload = request_json()
    device = g.device
    touch_device(device)
    sos_event = SosEvent(device_id=device.id, created_at=parse_client_datetime(payload.get("created_at"), local_now()))
    db.session.add(sos_event)
    db.session.flush()
    owner_name = device.blind_person.full_name if device.blind_person else "chưa gán"
    log_activity("sos_received", f"Thiết bị {device.device_code} ({owner_name}) gửi SOS #{sos_event.id}",
                 user=None, commit=False)
    db.session.commit()
    return jsonify({"sos_id": sos_event.id})


def read_frame_upload():
    uploaded = request.files.get("frame") or request.files.get("image")
    if uploaded is not None:
        return uploaded.read(), request.form.get("session_id") or request.args.get("session_id")
    return request.get_data(cache=False), request.args.get("session_id") or request.headers.get("X-Session-Id")


def close_expired_web_sessions(store):
    expired_states = store.pop_expired()
    for state in expired_states:
        usage_session = db.session.get(UsageSession, state.session_id)
        if usage_session is None or usage_session.ended_at is not None:
            continue
        idle_seconds = max(0, int(time.monotonic() - state.last_used))
        usage_session.ended_at = local_now() - timedelta(seconds=idle_seconds)
        for field_name, value in state.stats().items():
            setattr(usage_session, field_name, value)
    return len(expired_states)


def device_needs_touch(device):
    if device.status != "online" or device.last_seen_at is None:
        return True
    return (local_now() - device.last_seen_at).total_seconds() >= current_app.config.get("WEB_DETECT_TOUCH_SECONDS", 5)


@device_api_bp.post("/detect")
@device_key_required
def detect_frame():
    device = g.device
    max_bytes = current_app.config.get("WEB_DETECT_MAX_BYTES", 3 * 1024 * 1024)
    if request.content_length is not None and request.content_length > max_bytes:
        return json_error("Ảnh quá lớn", 413)
    data, raw_session_id = read_frame_upload()
    if len(data) > max_bytes:
        return json_error("Ảnh quá lớn", 413)
    session_id = optional_int(raw_session_id)
    if session_id is None:
        return json_error("Thiếu session_id của phiên sử dụng", 400)
    usage_session = db.session.get(UsageSession, session_id)
    if usage_session is None or usage_session.device_id != device.id:
        return json_error("Không tìm thấy phiên sử dụng", 404)
    if usage_session.ended_at is not None:
        return json_error("Phiên sử dụng đã kết thúc", 409)

    store = get_session_store(current_app)
    expired_count = close_expired_web_sessions(store)
    request_start = time.perf_counter()
    try:
        frame = scale_to_reference(decode_frame(data))
    except InvalidFrameError as error:
        return json_error(str(error), 400)

    config = ensure_device_config(device)
    config_updated_at = to_iso(config.updated_at)
    state = store.get_or_create(session_id, device.id, lambda: device_config_payload(device), config_updated_at)
    engine = get_engine(current_app)
    with state.lock:
        try:
            frame_result, infer_ms, _ = engine.process(state, frame)
        except ModelUnavailableError as error:
            return json_error(str(error), 503)
        process_ms = (time.perf_counter() - request_start) * 1000
        state.record_frame(process_ms, infer_ms, frame_result.alert is not None)
        response = build_detection_response(state, frame_result, frame, infer_ms, process_ms)

    saved = 0
    if frame_result.alert is not None:
        saved = save_alert_items(device, usage_session.id, [build_alert_record(frame_result.alert, state)])
    if saved or expired_count or device_needs_touch(device):
        touch_device(device)
        db.session.commit()
    response["alert_saved"] = bool(saved)
    response["inference_device"] = engine.device_label
    return jsonify(response)
