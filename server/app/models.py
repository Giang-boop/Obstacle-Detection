# === MO TA FILE ===
# server/app/models.py
# CHUC NANG: 11 bang CSDL: User, BlindPerson, Guardianship, Device, DeviceConfig, ObjectClass, ModelVersion, UsageSession, Alert, SosEvent, ActivityLog
# ===================

import secrets
from datetime import datetime, timedelta

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

ROLE_ADMIN = "admin"
ROLE_GUARDIAN = "guardian"
LEVEL_WARNING = "WARNING"
LEVEL_DANGER = "DANGER"
ALERT_LEVELS = (LEVEL_WARNING, LEVEL_DANGER)
ALERT_POSITIONS = ("LEFT", "CENTER", "RIGHT")
SOS_NEW = "new"
SOS_HANDLED = "handled"


def local_now():
    return datetime.now().replace(microsecond=0)


def generate_api_key():
    return secrets.token_hex(16)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(16), nullable=False, default=ROLE_GUARDIAN)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)
    last_login_at = db.Column(db.DateTime)

    guardianships = db.relationship("Guardianship", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def role_label(self):
        return "Quản trị viên" if self.is_admin else "Người thân"


class BlindPerson(db.Model):
    __tablename__ = "blind_persons"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    birth_year = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)

    guardianships = db.relationship("Guardianship", back_populates="blind_person", cascade="all, delete-orphan")
    devices = db.relationship("Device", back_populates="blind_person")


class Guardianship(db.Model):
    __tablename__ = "guardianships"
    __table_args__ = (db.UniqueConstraint("user_id", "blind_person_id", name="uq_guardianship_user_blind_person"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    blind_person_id = db.Column(db.Integer, db.ForeignKey("blind_persons.id"), nullable=False)
    relation = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)

    user = db.relationship("User", back_populates="guardianships")
    blind_person = db.relationship("BlindPerson", back_populates="guardianships")


class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    device_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    api_key = db.Column(db.String(64), unique=True, nullable=False, index=True, default=generate_api_key)
    blind_person_id = db.Column(db.Integer, db.ForeignKey("blind_persons.id"), nullable=True)
    status = db.Column(db.String(10), nullable=False, default="offline")
    last_seen_at = db.Column(db.DateTime)
    app_version = db.Column(db.String(40))
    model_name = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)

    blind_person = db.relationship("BlindPerson", back_populates="devices")
    config = db.relationship("DeviceConfig", back_populates="device", uselist=False, cascade="all, delete-orphan")
    sessions = db.relationship("UsageSession", back_populates="device", cascade="all, delete-orphan")
    alerts = db.relationship("Alert", back_populates="device", cascade="all, delete-orphan")
    sos_events = db.relationship("SosEvent", back_populates="device", cascade="all, delete-orphan")

    @property
    def is_online(self):
        if self.last_seen_at is None:
            return False
        limit_seconds = current_app.config.get("DEVICE_OFFLINE_SECONDS", 30)
        return local_now() - self.last_seen_at <= timedelta(seconds=limit_seconds)

    @property
    def effective_status(self):
        return "online" if self.is_online else "offline"


class DeviceConfig(db.Model):
    __tablename__ = "device_configs"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), unique=True, nullable=False)
    warning_distance = db.Column(db.Float, nullable=False, default=5.0)
    danger_distance = db.Column(db.Float, nullable=False, default=3.0)
    tts_rate = db.Column(db.Integer, nullable=False, default=165)
    tts_rate_danger = db.Column(db.Integer, nullable=False, default=200)
    tts_volume = db.Column(db.Float, nullable=False, default=1.0)
    short_messages = db.Column(db.Boolean, nullable=False, default=True)
    disabled_classes = db.Column(db.JSON, nullable=False, default=list)
    updated_at = db.Column(db.DateTime, nullable=False, default=local_now)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    device = db.relationship("Device", back_populates="config")
    updated_by_user = db.relationship("User")


class ObjectClass(db.Model):
    __tablename__ = "object_classes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(60), unique=True, nullable=False)
    name_vi = db.Column(db.String(120), nullable=False)
    k_value = db.Column(db.Float, nullable=False, default=600.0)
    risk_weight = db.Column(db.Float, nullable=False, default=1.0)
    is_obstacle = db.Column(db.Boolean, nullable=False, default=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)


class ModelVersion(db.Model):
    __tablename__ = "model_versions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    architecture = db.Column(db.String(60))
    num_classes = db.Column(db.Integer)
    epochs = db.Column(db.Integer)
    img_size = db.Column(db.Integer)
    precision = db.Column(db.Float)
    recall = db.Column(db.Float)
    map50 = db.Column(db.Float)
    map50_95 = db.Column(db.Float)
    trained_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    note = db.Column(db.Text)


class UsageSession(db.Model):
    __tablename__ = "usage_sessions"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=False, default=local_now)
    ended_at = db.Column(db.DateTime)
    model_name = db.Column(db.String(120))
    frames = db.Column(db.Integer)
    avg_fps = db.Column(db.Float)
    avg_latency_ms = db.Column(db.Float)
    alert_count = db.Column(db.Integer)

    device = db.relationship("Device", back_populates="sessions")
    alerts = db.relationship("Alert", back_populates="session")

    @property
    def duration_seconds(self):
        if self.started_at is None or self.ended_at is None:
            return None
        return max(0, int((self.ended_at - self.started_at).total_seconds()))


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey("usage_sessions.id"), nullable=True)
    class_code = db.Column(db.String(60), nullable=False, index=True)
    class_name_vi = db.Column(db.String(120))
    level = db.Column(db.String(10), nullable=False, index=True)
    distance_m = db.Column(db.Float)
    position = db.Column(db.String(10))
    ttc_s = db.Column(db.Float, nullable=True)
    message = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=local_now, index=True)

    device = db.relationship("Device", back_populates="alerts")
    session = db.relationship("UsageSession", back_populates="alerts")


class SosEvent(db.Model):
    __tablename__ = "sos_events"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)
    status = db.Column(db.String(10), nullable=False, default=SOS_NEW, index=True)
    handled_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    handled_at = db.Column(db.DateTime)
    note = db.Column(db.Text)

    device = db.relationship("Device", back_populates="sos_events")
    handler = db.relationship("User")


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(60), nullable=False)
    detail = db.Column(db.Text)
    ip_address = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, nullable=False, default=local_now, index=True)

    user = db.relationship("User")
