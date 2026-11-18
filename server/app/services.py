import re
from datetime import datetime, time, timedelta

from flask import current_app

from .extensions import db
from .models import Alert, Device, DeviceConfig, ObjectClass, SosEvent, SOS_NEW, local_now
from .timeutils import to_iso


def ensure_device_config(device):
    if device.config is None:
        device.config = DeviceConfig(device=device, disabled_classes=[])
        db.session.flush()
    return device.config


def object_classes_payload():
    classes = db.session.scalars(db.select(ObjectClass).order_by(ObjectClass.code)).all()
    return {
        item.code: {
            "name_vi": item.name_vi,
            "k_value": item.k_value,
            "risk_weight": item.risk_weight,
            "enabled": bool(item.enabled),
            "is_obstacle": bool(item.is_obstacle),
        }
        for item in classes
    }


def device_config_payload(device):
    config = ensure_device_config(device)
    return {
        "warning_distance": config.warning_distance,
        "danger_distance": config.danger_distance,
        "tts_rate": config.tts_rate,
        "tts_rate_danger": config.tts_rate_danger,
        "tts_volume": config.tts_volume,
        "short_messages": bool(config.short_messages),
        "disabled_classes": list(config.disabled_classes or []),
        "classes": object_classes_payload(),
        "updated_at": to_iso(config.updated_at),
    }


def touch_device(device, app_version=None, model_name=None):
    device.last_seen_at = local_now()
    device.status = "online"
    if app_version:
        device.app_version = str(app_version)[:40]
    if model_name:
        device.model_name = str(model_name)[:120]


def refresh_device_statuses():
    limit = local_now() - timedelta(seconds=current_app.config.get("DEVICE_OFFLINE_SECONDS", 30))
    stale_devices = db.session.scalars(
        db.select(Device).where(Device.status == "online").where(
            (Device.last_seen_at.is_(None)) | (Device.last_seen_at < limit)
        )
    ).all()
    for device in stale_devices:
        device.status = "offline"
    if stale_devices:
        db.session.commit()


def mark_all_configs_updated():
    now = local_now()
    for config in db.session.scalars(db.select(DeviceConfig)).all():
        config.updated_at = now


def next_device_code():
    codes = db.session.scalars(db.select(Device.device_code)).all()
    highest = 0
    for code in codes:
        match = re.fullmatch(r"DEV-(\d+)", code or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return f"DEV-{highest + 1:04d}"


def today_range():
    start = datetime.combine(local_now().date(), time.min)
    return start, start + timedelta(days=1)


def count_alerts_today(alerts_query):
    start, end = today_range()
    query = alerts_query.where(Alert.created_at >= start).where(Alert.created_at < end)
    return db.session.scalar(db.select(db.func.count()).select_from(query.subquery()))


def count_query(query):
    return db.session.scalar(db.select(db.func.count()).select_from(query.subquery()))


def new_sos_query(sos_query):
    return sos_query.where(SosEvent.status == SOS_NEW).order_by(SosEvent.created_at.desc())
