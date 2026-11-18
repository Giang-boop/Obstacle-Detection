# === MO TA FILE ===
# server/app/__init__.py
# CHUC NANG: create_app(): dang ky 12 blueprint, CSRF, Flask-Login, trang loi 403/404
# ===================

import os

from flask import Flask, jsonify, render_template, request
from flask_wtf.csrf import CSRFError

from server.config import INSTANCE_DIR, Config

from . import labels
from .extensions import csrf, db, login_manager
from .models import User
from .timeutils import format_datetime, format_duration


def create_app(config=None):
    app = Flask(__name__, instance_path=INSTANCE_DIR, instance_relative_config=False)
    app.config.from_object(Config)
    if isinstance(config, dict):
        app.config.update(config)
    elif config is not None:
        app.config.from_object(config)
    os.makedirs(app.instance_path, exist_ok=True)
    app.json.ensure_ascii = False

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."
    login_manager.login_message_category = "warning"

    register_blueprints(app)
    register_template_helpers(app)
    register_error_handlers(app)
    register_cli(app)

    with app.app_context():
        db.create_all()
    return app


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    if user is None or not user.is_active:
        return None
    return user


def register_blueprints(app):
    from .routes.admin import admin_bp
    from .routes.alerts import alerts_bp
    from .routes.auth import auth_bp
    from .routes.blind_mode import blind_mode_bp
    from .routes.blind_persons import blind_persons_bp
    from .routes.dashboard import dashboard_bp
    from .routes.device_api import device_api_bp
    from .routes.devices import devices_bp
    from .routes.sessions import sessions_bp
    from .routes.sos import sos_bp
    from .routes.statistics import statistics_bp
    from .routes.web_api import web_api_bp

    for blueprint in (
        auth_bp,
        dashboard_bp,
        blind_persons_bp,
        alerts_bp,
        statistics_bp,
        sos_bp,
        devices_bp,
        sessions_bp,
        admin_bp,
        device_api_bp,
        web_api_bp,
        blind_mode_bp,
    ):
        app.register_blueprint(blueprint)
    csrf.exempt(device_api_bp)


def register_template_helpers(app):
    app.jinja_env.filters["dt"] = format_datetime
    app.jinja_env.filters["duration"] = format_duration
    app.jinja_env.filters["level_label"] = labels.level_label
    app.jinja_env.filters["position_label"] = labels.position_label
    app.jinja_env.filters["action_label"] = labels.action_label

    @app.template_filter("num")
    def format_number(value, digits=1):
        if value is None:
            return "—"
        text = f"{value:,.{digits}f}"
        return text.replace(",", " ").replace(".", ",").replace(" ", ".")

    @app.context_processor
    def inject_globals():
        return {
            "LEVEL_LABELS": labels.LEVEL_LABELS,
            "LEVEL_BADGES": labels.LEVEL_BADGES,
            "POSITION_LABELS": labels.POSITION_LABELS,
            "STATUS_LABELS": labels.STATUS_LABELS,
            "SOS_STATUS_LABELS": labels.SOS_STATUS_LABELS,
            "GENDER_CHOICES": labels.GENDER_CHOICES,
            "SUMMARY_POLL_SECONDS": app.config.get("SUMMARY_POLL_SECONDS", 5),
        }


def wants_json_response():
    return request.path.startswith("/api/")


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(error):
        if wants_json_response():
            return jsonify({"error": "Không có quyền truy cập"}), 403
        return render_template(
            "errors/error.html",
            code=403,
            title="Không có quyền truy cập",
            message="Bạn không có quyền xem dữ liệu này. Người thân chỉ xem được người khiếm thị mình giám hộ.",
        ), 403

    @app.errorhandler(404)
    def not_found(error):
        if wants_json_response():
            return jsonify({"error": "Không tìm thấy"}), 404
        return render_template(
            "errors/error.html",
            code=404,
            title="Không tìm thấy trang",
            message="Đường dẫn không tồn tại hoặc dữ liệu đã bị xóa.",
        ), 404

    @app.errorhandler(CSRFError)
    def csrf_failed(error):
        return render_template(
            "errors/error.html",
            code=400,
            title="Biểu mẫu không hợp lệ",
            message="Mã bảo vệ CSRF không hợp lệ hoặc đã hết hạn. Vui lòng tải lại trang và thử lại.",
        ), 400


def register_cli(app):
    @app.cli.command("seed")
    def seed_command():
        from .seed_data import seed_database

        summary = seed_database()
        for label, value in summary.items():
            print(f"{label}: {value}")
