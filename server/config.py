import os

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(SERVER_DIR, "instance")
DATABASE_FILE = os.path.join(INSTANCE_DIR, "blindassist.db")


class Config:
    SECRET_KEY = os.environ.get("BLINDASSIST_SECRET_KEY", "blindassist-nhom11-khoa-bi-mat-doi-khi-trien-khai")
    SQLALCHEMY_DATABASE_URI = os.environ.get("BLINDASSIST_DATABASE_URI", "sqlite:///" + DATABASE_FILE.replace("\\", "/"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = None
    JSON_AS_ASCII = False
    DEVICE_OFFLINE_SECONDS = 30
    ALERTS_PER_PAGE = 20
    LIST_PER_PAGE = 15
    LOGS_PER_PAGE = 20
    CLASSES_PER_PAGE = 20
    DASHBOARD_DEVICE_LIMIT = 10
    SUMMARY_POLL_SECONDS = 5
    MAX_ALERT_ITEMS_PER_REQUEST = 500
    WEB_DETECT_DEVICE = os.environ.get("BLINDASSIST_INFER_DEVICE", "auto")
    WEB_DETECT_MODEL_PATH = os.environ.get("BLINDASSIST_MODEL_PATH") or None
    WEB_DETECT_MAX_BYTES = 3 * 1024 * 1024
    WEB_DETECT_TOUCH_SECONDS = 5
    WEB_SESSION_IDLE_SECONDS = 120
