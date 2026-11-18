import re

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^[0-9+\s.\-]{8,20}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.]{3,64}$")


def validate_email(email):
    if email and not EMAIL_PATTERN.match(email):
        return ["Email không hợp lệ."]
    return []


def validate_phone(phone):
    if phone and not PHONE_PATTERN.match(phone):
        return ["Số điện thoại không hợp lệ."]
    return []


def validate_username(username):
    if not USERNAME_PATTERN.match(username or ""):
        return ["Tên đăng nhập 3–64 ký tự, chỉ gồm chữ không dấu, số, dấu chấm hoặc gạch dưới."]
    return []


def validate_new_password(password, confirm_password=None):
    errors = []
    if len(password or "") < 8:
        errors.append("Mật khẩu mới phải có ít nhất 8 ký tự.")
    elif not (re.search(r"[A-Za-z]", password) and re.search(r"[0-9]", password)):
        errors.append("Mật khẩu mới phải có cả chữ và số.")
    if confirm_password is not None and password != confirm_password:
        errors.append("Xác nhận mật khẩu không khớp.")
    return errors


def parse_float_field(form, field_name, label, minimum=None, maximum=None, errors=None, required=True):
    raw_value = (form.get(field_name) or "").strip().replace(",", ".")
    if raw_value == "":
        if required and errors is not None:
            errors.append(f"{label} không được để trống.")
        return None
    try:
        value = float(raw_value)
    except ValueError:
        if errors is not None:
            errors.append(f"{label} phải là số.")
        return None
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        if errors is not None:
            errors.append(f"{label} phải nằm trong khoảng {minimum} – {maximum}.")
        return None
    return value


def parse_int_field(form, field_name, label, minimum=None, maximum=None, errors=None, required=True):
    raw_value = (form.get(field_name) or "").strip()
    if raw_value == "":
        if required and errors is not None:
            errors.append(f"{label} không được để trống.")
        return None
    try:
        value = int(raw_value)
    except ValueError:
        if errors is not None:
            errors.append(f"{label} phải là số nguyên.")
        return None
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        if errors is not None:
            errors.append(f"{label} phải nằm trong khoảng {minimum} – {maximum}.")
        return None
    return value
