from flask import Blueprint, make_response, render_template, url_for
from flask_login import login_required

from ..access import get_device_or_403
from ..web_detection import WEB_APP_VERSION, client_policy

blind_mode_bp = Blueprint("blind_mode", __name__, url_prefix="/thiet-bi")


def render_blind_mode(preset=None):
    return render_template(
        "blind_mode/index.html",
        preset=preset,
        client_options={
            "api_base": url_for("device_api.hello").rsplit("/", 1)[0],
            "app_version": WEB_APP_VERSION,
            "model_name": "best.pt",
            "page_url": url_for("blind_mode.index"),
            "policy": client_policy(),
        },
    )


@blind_mode_bp.get("")
def index():
    return render_blind_mode()


@blind_mode_bp.get("/mo/<int:device_id>")
@login_required
def open_for_device(device_id):
    device = get_device_or_403(device_id)
    response = make_response(render_blind_mode({"device_code": device.device_code, "api_key": device.api_key}))
    response.headers["Cache-Control"] = "no-store"
    return response
