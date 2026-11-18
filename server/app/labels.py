LEVEL_LABELS = {"WARNING": "Cảnh báo", "DANGER": "Nguy hiểm"}
LEVEL_BADGES = {"WARNING": "text-bg-warning", "DANGER": "text-bg-danger"}
POSITION_LABELS = {"LEFT": "Bên trái", "CENTER": "Phía trước", "RIGHT": "Bên phải"}
STATUS_LABELS = {"online": "Trực tuyến", "offline": "Ngoại tuyến"}
SOS_STATUS_LABELS = {"new": "Chưa xử lý", "handled": "Đã xử lý"}
GENDER_CHOICES = ("Nam", "Nữ", "Khác")
ACTION_LABELS = {
    "login": "Đăng nhập",
    "login_failed": "Đăng nhập thất bại",
    "logout": "Đăng xuất",
    "profile_update": "Cập nhật hồ sơ",
    "password_change": "Đổi mật khẩu",
    "config_update": "Cấu hình thiết bị",
    "sos_received": "Nhận SOS",
    "sos_handled": "Xử lý SOS",
    "user_create": "Thêm tài khoản",
    "user_update": "Sửa tài khoản",
    "user_lock": "Khóa tài khoản",
    "user_unlock": "Mở khóa tài khoản",
    "user_reset_password": "Đặt lại mật khẩu",
    "blind_person_create": "Thêm người khiếm thị",
    "blind_person_update": "Sửa người khiếm thị",
    "blind_person_delete": "Xóa người khiếm thị",
    "guardianship_create": "Phân công người thân",
    "guardianship_delete": "Bỏ phân công người thân",
    "device_create": "Thêm thiết bị",
    "device_update": "Sửa thiết bị",
    "device_delete": "Xóa thiết bị",
    "device_regenerate_key": "Cấp lại mã thiết bị",
    "class_update": "Sửa lớp vật cản",
    "model_create": "Thêm phiên bản model",
    "model_update": "Sửa phiên bản model",
    "model_activate": "Chọn model đang dùng",
    "model_delete": "Xóa phiên bản model",
}


def level_label(value):
    return LEVEL_LABELS.get(value, value or "—")


def position_label(value):
    return POSITION_LABELS.get(value, value or "—")


def action_label(value):
    return ACTION_LABELS.get(value, value)
