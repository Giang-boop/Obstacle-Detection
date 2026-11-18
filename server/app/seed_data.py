# === MO TA FILE ===
# server/app/seed_data.py
# CHUC NANG: Du lieu khoi tao: 2 tai khoan, thiet bi DEV-0001, 17 lop, 2 model version
# ===================

from datetime import datetime

from .extensions import db
from .models import (
    ROLE_ADMIN,
    ROLE_GUARDIAN,
    BlindPerson,
    Device,
    DeviceConfig,
    Guardianship,
    ModelVersion,
    ObjectClass,
    User,
)

SEED_CLASSES = [
    ("Bike", "xe đạp", 650.0, 1.4, True),
    ("Building", "tòa nhà", 1000.0, 1.0, True),
    ("Car", "ô tô", 900.0, 1.5, True),
    ("Person", "người", 600.0, 1.2, True),
    ("Stairs", "cầu thang", 800.0, 1.3, True),
    ("Electrical Pole", "cột điện", 1000.0, 1.0, True),
    ("Road", "đường", 1000.0, 1.0, False),
    ("Motorcycle", "xe máy", 700.0, 1.5, True),
    ("Dustbin", "thùng rác", 500.0, 1.0, True),
    ("Manhole", "nắp cống", 350.0, 1.3, True),
    ("Tree", "cây", 1000.0, 1.0, True),
    ("Guard rail", "lan can", 800.0, 1.0, True),
    ("Truck", "xe tải", 1100.0, 1.6, True),
    ("Traffic Cone", "cọc tiêu giao thông", 350.0, 1.0, True),
    ("Electrical Box", "tủ điện", 500.0, 1.0, True),
    ("Chair", "ghế", 450.0, 1.0, True),
    ("Dog", "chó", 450.0, 1.3, True),
]

DEMO_DEVICE_KEY = "demo-device-key-0001"


SEED_MODEL_VERSIONS = [
    dict(name="YOLOv8n 17 lớp – lần 1", file_name="best_lan1.pt", architecture="YOLOv8n", epochs=60, img_size=640,
         precision=0.838, recall=0.878, map50=0.908, map50_95=0.765, trained_at=datetime(2026, 11, 13, 16, 27),
         is_active=False,
         note="Chỉ số trên tập test obstacle17 (1.629 ảnh, 1.882 đối tượng). Bộ dữ liệu huấn luyện "
              "VISION_V4_17CLASS_CLEAN lấy từ cùng nguồn ảnh nên chỉ số có thể cao hơn thực tế; lần chạy này không "
              "còn đủ log và biểu đồ huấn luyện để tái lập nên không chọn dùng."),
    dict(name="YOLOv8n 17 lớp – lần 2", file_name="best.pt", architecture="YOLOv8n", epochs=60, img_size=640,
         precision=0.891, recall=0.843, map50=0.901, map50_95=0.724, trained_at=datetime(2026, 11, 18, 3, 20),
         is_active=True,
         note="Đang dùng trên thiết bị (detector/best.pt, chép từ training/runs/yolov8n_17lop/weights/best.pt). "
              "Chỉ số trên tập test obstacle17 (1.629 ảnh, 1.882 đối tượng). Precision cao hơn lần 1, ít báo nhầm; "
              "trên video đôi khi nhận chó và xe máy có người lái thành người."),
]


def seed_database():
    db.session.remove()
    db.drop_all()
    db.create_all()

    admin = User(username="admin", full_name="Quản trị hệ thống", email="admin@blindassist.local",
                 phone="0900000001", role=ROLE_ADMIN, is_active=True)
    admin.set_password("Admin@123")
    guardian = User(username="nguoithan", full_name="Nguyễn Thị Hoa", email="nguoithan@blindassist.local",
                    phone="0900000002", role=ROLE_GUARDIAN, is_active=True)
    guardian.set_password("Nguoithan@123")
    db.session.add_all([admin, guardian])

    blind_person = BlindPerson(full_name="Nguyễn Văn An", birth_year=1958, gender="Nam", phone="0900000003",
                               address="Hà Nội", note="Khiếm thị hoàn toàn, đi lại bằng gậy trắng.")
    db.session.add(blind_person)
    db.session.flush()

    db.session.add(Guardianship(user_id=guardian.id, blind_person_id=blind_person.id, relation="Con"))

    device = Device(name="Thiết bị camera của ông An", device_code="DEV-0001", api_key=DEMO_DEVICE_KEY,
                    blind_person_id=blind_person.id, status="offline")
    db.session.add(device)
    db.session.flush()
    db.session.add(DeviceConfig(device_id=device.id, warning_distance=5.0, danger_distance=3.0, tts_rate=165,
                                tts_rate_danger=200, tts_volume=1.0, short_messages=True, disabled_classes=[],
                                updated_by=admin.id))

    for code, name_vi, k_value, risk_weight, is_obstacle in SEED_CLASSES:
        db.session.add(ObjectClass(code=code, name_vi=name_vi, k_value=k_value, risk_weight=risk_weight,
                                   is_obstacle=is_obstacle, enabled=True))

    for values in SEED_MODEL_VERSIONS:
        db.session.add(ModelVersion(num_classes=len(SEED_CLASSES), **values))
    db.session.commit()

    return {
        "Tài khoản": "admin / Admin@123, nguoithan / Nguoithan@123",
        "Người khiếm thị": blind_person.full_name,
        "Thiết bị": f"{device.device_code} (api_key {DEMO_DEVICE_KEY})",
        "Số lớp vật cản": len(SEED_CLASSES),
        "Phiên bản model": len(SEED_MODEL_VERSIONS),
    }
