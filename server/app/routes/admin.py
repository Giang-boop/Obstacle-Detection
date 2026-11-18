# === MO TA FILE ===
# server/app/routes/admin.py
# CHUC NANG: Quan tri: users, blind persons, devices, classes, models, logs
# ===================

from datetime import datetime, time, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..access import admin_required
from ..activity import log_activity
from ..extensions import db
from ..labels import ACTION_LABELS
from ..pagination import clean_args, paginate_query, search_condition
from ..models import (
    ROLE_ADMIN,
    ROLE_GUARDIAN,
    ActivityLog,
    BlindPerson,
    Device,
    DeviceConfig,
    Guardianship,
    ModelVersion,
    ObjectClass,
    User,
    generate_api_key,
    local_now,
)
from ..services import mark_all_configs_updated, next_device_code, refresh_device_statuses
from ..timeutils import parse_form_date
from ..validation import (
    parse_float_field,
    parse_int_field,
    validate_email,
    validate_new_password,
    validate_phone,
    validate_username,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def flash_errors(errors):
    for message in errors:
        flash(message, "danger")


@admin_bp.get("/users")
@admin_required
def users():
    keyword = request.args.get("q", "").strip()
    role = request.args.get("role", "")
    query = db.select(User)
    if keyword:
        query = query.where(search_condition(keyword, User.username, User.full_name, User.email, User.phone))
    if role in (ROLE_ADMIN, ROLE_GUARDIAN):
        query = query.where(User.role == role)
    else:
        role = ""
    pagination = paginate_query(query.order_by(User.role, User.username, User.id))
    return render_template("admin/users.html", pagination=pagination, keyword=keyword, role=role,
                           filter_args=clean_args({"q": keyword, "role": role}))


def read_user_form(form, user=None):
    errors = []
    values = {
        "full_name": form.get("full_name", "").strip(),
        "email": form.get("email", "").strip() or None,
        "phone": form.get("phone", "").strip() or None,
        "role": form.get("role") if form.get("role") in (ROLE_ADMIN, ROLE_GUARDIAN) else ROLE_GUARDIAN,
    }
    if not values["full_name"]:
        errors.append("Họ tên không được để trống.")
    errors += validate_email(values["email"]) + validate_phone(values["phone"])
    if user is None:
        values["username"] = form.get("username", "").strip()
        errors += validate_username(values["username"])
        if not errors and db.session.scalar(db.select(User).where(User.username == values["username"])):
            errors.append("Tên đăng nhập đã tồn tại.")
        values["password"] = form.get("password", "")
        errors += validate_new_password(values["password"])
    elif user.id == current_user.id and values["role"] != ROLE_ADMIN:
        errors.append("Không thể tự hạ quyền quản trị của chính mình.")
    return values, errors


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def create_user():
    form_values = {}
    if request.method == "POST":
        form_values, errors = read_user_form(request.form)
        if errors:
            flash_errors(errors)
        else:
            user = User(username=form_values["username"], full_name=form_values["full_name"],
                        email=form_values["email"], phone=form_values["phone"], role=form_values["role"], is_active=True)
            user.set_password(form_values["password"])
            db.session.add(user)
            db.session.flush()
            log_activity("user_create", f"Thêm tài khoản {user.username} ({user.role_label})")
            flash(f"Đã thêm tài khoản {user.username}.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", user=None, form_values=form_values)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = db.get_or_404(User, user_id)
    form_values = {}
    if request.method == "POST":
        form_values, errors = read_user_form(request.form, user)
        if errors:
            flash_errors(errors)
        else:
            for field_name in ("full_name", "email", "phone", "role"):
                setattr(user, field_name, form_values[field_name])
            log_activity("user_update", f"Sửa tài khoản {user.username}")
            flash("Đã cập nhật tài khoản.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", user=user, form_values=form_values)


@admin_bp.post("/users/<int:user_id>/toggle-active")
@admin_required
def toggle_user_active(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("Không thể tự khóa tài khoản đang đăng nhập.", "danger")
        return redirect(url_for("admin.users"))
    user.is_active = not user.is_active
    log_activity("user_unlock" if user.is_active else "user_lock", f"Tài khoản {user.username}")
    flash(f"Đã {'mở khóa' if user.is_active else 'khóa'} tài khoản {user.username}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.post("/users/<int:user_id>/reset-password")
@admin_required
def reset_user_password(user_id):
    user = db.get_or_404(User, user_id)
    new_password = request.form.get("new_password", "")
    errors = validate_new_password(new_password, request.form.get("confirm_password", ""))
    if errors:
        flash_errors(errors)
        return redirect(url_for("admin.edit_user", user_id=user.id))
    user.set_password(new_password)
    log_activity("user_reset_password", f"Đặt lại mật khẩu cho {user.username}")
    flash(f"Đã đặt lại mật khẩu cho {user.username}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.get("/blind-persons")
@admin_required
def blind_persons():
    keyword = request.args.get("q", "").strip()
    query = db.select(BlindPerson)
    if keyword:
        query = query.where(search_condition(keyword, BlindPerson.full_name, BlindPerson.phone, BlindPerson.address))
    pagination = paginate_query(query.order_by(BlindPerson.full_name, BlindPerson.id))
    return render_template("admin/blind_persons.html", pagination=pagination, keyword=keyword,
                           filter_args=clean_args({"q": keyword}))


def read_blind_person_form(form):
    errors = []
    values = {
        "full_name": form.get("full_name", "").strip(),
        "birth_year": parse_int_field(form, "birth_year", "Năm sinh", 1900, local_now().year, errors, required=False),
        "gender": form.get("gender", "").strip() or None,
        "phone": form.get("phone", "").strip() or None,
        "address": form.get("address", "").strip() or None,
        "note": form.get("note", "").strip() or None,
    }
    if not values["full_name"]:
        errors.append("Họ tên không được để trống.")
    errors += validate_phone(values["phone"])
    return values, errors


@admin_bp.route("/blind-persons/new", methods=["GET", "POST"])
@admin_required
def create_blind_person():
    form_values = {}
    if request.method == "POST":
        form_values, errors = read_blind_person_form(request.form)
        if errors:
            flash_errors(errors)
        else:
            blind_person = BlindPerson(**form_values)
            db.session.add(blind_person)
            db.session.flush()
            log_activity("blind_person_create", f"Thêm người khiếm thị {blind_person.full_name}")
            flash("Đã thêm người khiếm thị. Hãy phân công người thân và gán thiết bị.", "success")
            return redirect(url_for("admin.edit_blind_person", blind_person_id=blind_person.id))
    return render_template("admin/blind_person_form.html", blind_person=None, form_values=form_values)


@admin_bp.route("/blind-persons/<int:blind_person_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_blind_person(blind_person_id):
    blind_person = db.get_or_404(BlindPerson, blind_person_id)
    form_values = {}
    if request.method == "POST":
        form_values, errors = read_blind_person_form(request.form)
        if errors:
            flash_errors(errors)
        else:
            for field_name, value in form_values.items():
                setattr(blind_person, field_name, value)
            log_activity("blind_person_update", f"Sửa người khiếm thị {blind_person.full_name}")
            flash("Đã cập nhật thông tin.", "success")
            return redirect(url_for("admin.edit_blind_person", blind_person_id=blind_person.id))
    assigned_user_ids = {item.user_id for item in blind_person.guardianships}
    available_guardians = [
        user for user in db.session.scalars(
            db.select(User).where(User.role == ROLE_GUARDIAN).order_by(User.full_name)
        ).all() if user.id not in assigned_user_ids
    ]
    return render_template(
        "admin/blind_person_form.html",
        blind_person=blind_person,
        form_values=form_values,
        available_guardians=available_guardians,
    )


@admin_bp.post("/blind-persons/<int:blind_person_id>/delete")
@admin_required
def delete_blind_person(blind_person_id):
    blind_person = db.get_or_404(BlindPerson, blind_person_id)
    for device in blind_person.devices:
        device.blind_person_id = None
    full_name = blind_person.full_name
    db.session.delete(blind_person)
    log_activity("blind_person_delete", f"Xóa người khiếm thị {full_name}")
    flash(f"Đã xóa {full_name}. Thiết bị của người này chuyển sang trạng thái chưa gán.", "success")
    return redirect(url_for("admin.blind_persons"))


@admin_bp.post("/blind-persons/<int:blind_person_id>/guardians")
@admin_required
def add_guardian(blind_person_id):
    blind_person = db.get_or_404(BlindPerson, blind_person_id)
    user_id = request.form.get("user_id", type=int)
    user = db.session.get(User, user_id) if user_id else None
    relation = request.form.get("relation", "").strip()[:50] or None
    if user is None or user.role != ROLE_GUARDIAN:
        flash("Vui lòng chọn một tài khoản người thân.", "danger")
    elif db.session.scalar(db.select(Guardianship).where(
            Guardianship.user_id == user.id, Guardianship.blind_person_id == blind_person.id)):
        flash("Người thân này đã được phân công.", "warning")
    else:
        db.session.add(Guardianship(user_id=user.id, blind_person_id=blind_person.id, relation=relation))
        log_activity("guardianship_create", f"Phân công {user.username} giám hộ {blind_person.full_name}")
        flash(f"Đã phân công {user.full_name}.", "success")
    return redirect(url_for("admin.edit_blind_person", blind_person_id=blind_person.id))


@admin_bp.post("/guardianships/<int:guardianship_id>/delete")
@admin_required
def delete_guardianship(guardianship_id):
    guardianship = db.get_or_404(Guardianship, guardianship_id)
    blind_person_id = guardianship.blind_person_id
    detail = f"Bỏ phân công {guardianship.user.username} khỏi {guardianship.blind_person.full_name}"
    db.session.delete(guardianship)
    log_activity("guardianship_delete", detail)
    flash("Đã bỏ phân công người thân.", "success")
    return redirect(url_for("admin.edit_blind_person", blind_person_id=blind_person_id))


@admin_bp.get("/devices")
@admin_required
def devices():
    refresh_device_statuses()
    keyword = request.args.get("q", "").strip()
    query = db.select(Device)
    if keyword:
        query = query.where(search_condition(keyword, Device.device_code, Device.name))
    pagination = paginate_query(query.order_by(Device.device_code, Device.id))
    return render_template("admin/devices.html", pagination=pagination, keyword=keyword,
                           filter_args=clean_args({"q": keyword}))


def read_device_form(form):
    errors = []
    blind_person_id = form.get("blind_person_id", type=int)
    if blind_person_id and db.session.get(BlindPerson, blind_person_id) is None:
        errors.append("Người khiếm thị không tồn tại.")
    values = {"name": form.get("name", "").strip(), "blind_person_id": blind_person_id or None}
    if not values["name"]:
        errors.append("Tên thiết bị không được để trống.")
    return values, errors


@admin_bp.route("/devices/new", methods=["GET", "POST"])
@admin_required
def create_device():
    form_values = {}
    if request.method == "POST":
        form_values, errors = read_device_form(request.form)
        if errors:
            flash_errors(errors)
        else:
            device = Device(device_code=next_device_code(), api_key=generate_api_key(), status="offline", **form_values)
            db.session.add(device)
            db.session.flush()
            db.session.add(DeviceConfig(device_id=device.id, disabled_classes=[], updated_by=current_user.id))
            log_activity("device_create", f"Thêm thiết bị {device.device_code} – {device.name}")
            flash(f"Đã thêm thiết bị {device.device_code}. Nhập mã thiết bị (api_key) bên dưới vào app detector.", "success")
            return redirect(url_for("admin.edit_device", device_id=device.id))
    return render_template("admin/device_form.html", device=None, form_values=form_values,
                           blind_persons=db.session.scalars(db.select(BlindPerson).order_by(BlindPerson.full_name)).all())


@admin_bp.route("/devices/<int:device_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_device(device_id):
    device = db.get_or_404(Device, device_id)
    form_values = {}
    if request.method == "POST":
        form_values, errors = read_device_form(request.form)
        if errors:
            flash_errors(errors)
        else:
            device.name = form_values["name"]
            device.blind_person_id = form_values["blind_person_id"]
            log_activity("device_update", f"Sửa thiết bị {device.device_code}")
            flash("Đã cập nhật thiết bị.", "success")
            return redirect(url_for("admin.devices"))
    return render_template("admin/device_form.html", device=device, form_values=form_values,
                           blind_persons=db.session.scalars(db.select(BlindPerson).order_by(BlindPerson.full_name)).all())


@admin_bp.post("/devices/<int:device_id>/regenerate-key")
@admin_required
def regenerate_device_key(device_id):
    device = db.get_or_404(Device, device_id)
    device.api_key = generate_api_key()
    log_activity("device_regenerate_key", f"Cấp lại mã thiết bị {device.device_code}")
    flash(f"Đã cấp mã mới cho {device.device_code}. Mã cũ không còn dùng được.", "success")
    return redirect(url_for("admin.edit_device", device_id=device.id))


@admin_bp.post("/devices/<int:device_id>/delete")
@admin_required
def delete_device(device_id):
    device = db.get_or_404(Device, device_id)
    device_code = device.device_code
    db.session.delete(device)
    log_activity("device_delete", f"Xóa thiết bị {device_code} cùng dữ liệu cảnh báo, phiên, SOS")
    flash(f"Đã xóa thiết bị {device_code}.", "success")
    return redirect(url_for("admin.devices"))


@admin_bp.get("/classes")
@admin_required
def classes():
    pagination = paginate_query(db.select(ObjectClass).order_by(ObjectClass.code), "CLASSES_PER_PAGE")
    return render_template("admin/classes.html", pagination=pagination)


@admin_bp.post("/classes/<int:class_id>")
@admin_required
def update_class(class_id):
    object_class = db.get_or_404(ObjectClass, class_id)
    return_page = request.form.get("page", type=int)
    return_args = {"page": return_page} if return_page and return_page > 1 else {}
    errors = []
    name_vi = request.form.get("name_vi", "").strip()
    k_value = parse_float_field(request.form, "k_value", "Hệ số K", 1, 100000, errors)
    risk_weight = parse_float_field(request.form, "risk_weight", "Trọng số rủi ro", 0, 10, errors)
    if not name_vi:
        errors.append("Tên tiếng Việt không được để trống.")
    if errors:
        flash_errors(errors)
        return redirect(url_for("admin.classes", **return_args))
    object_class.name_vi = name_vi
    object_class.k_value = k_value
    object_class.risk_weight = risk_weight
    object_class.enabled = request.form.get("enabled") == "on"
    object_class.is_obstacle = request.form.get("is_obstacle") == "on"
    mark_all_configs_updated()
    log_activity("class_update", f"Lớp {object_class.code}: {name_vi}, K={k_value}, rủi ro={risk_weight}, "
                                 f"{'bật' if object_class.enabled else 'tắt'}")
    flash(f"Đã cập nhật lớp {object_class.code}.", "success")
    return redirect(url_for("admin.classes", **return_args))


@admin_bp.get("/models")
@admin_required
def models():
    pagination = paginate_query(db.select(ModelVersion).order_by(ModelVersion.is_active.desc(), ModelVersion.id.desc()))
    return render_template("admin/models.html", pagination=pagination)


def read_model_form(form):
    errors = []
    values = {
        "name": form.get("name", "").strip(),
        "file_name": form.get("file_name", "").strip(),
        "architecture": form.get("architecture", "").strip() or None,
        "num_classes": parse_int_field(form, "num_classes", "Số lớp", 1, 1000, errors, required=False),
        "epochs": parse_int_field(form, "epochs", "Số epoch", 1, 10000, errors, required=False),
        "img_size": parse_int_field(form, "img_size", "Kích thước ảnh", 32, 4096, errors, required=False),
        "precision": parse_float_field(form, "precision", "Precision", 0, 1, errors, required=False),
        "recall": parse_float_field(form, "recall", "Recall", 0, 1, errors, required=False),
        "map50": parse_float_field(form, "map50", "mAP@0.5", 0, 1, errors, required=False),
        "map50_95": parse_float_field(form, "map50_95", "mAP@0.5:0.95", 0, 1, errors, required=False),
        "trained_at": None,
        "note": form.get("note", "").strip() or None,
    }
    trained_date = parse_form_date(form.get("trained_at"))
    if trained_date:
        values["trained_at"] = datetime.combine(trained_date, time.min)
    elif form.get("trained_at"):
        errors.append("Ngày huấn luyện không hợp lệ.")
    if not values["name"]:
        errors.append("Tên phiên bản không được để trống.")
    if not values["file_name"]:
        errors.append("Tên tệp model không được để trống.")
    return values, errors


@admin_bp.route("/models/new", methods=["GET", "POST"])
@admin_required
def create_model():
    form_values = {}
    if request.method == "POST":
        form_values, errors = read_model_form(request.form)
        if errors:
            flash_errors(errors)
        else:
            model_version = ModelVersion(is_active=False, **form_values)
            db.session.add(model_version)
            log_activity("model_create", f"Thêm phiên bản model {model_version.name}")
            flash("Đã thêm phiên bản model.", "success")
            return redirect(url_for("admin.models"))
    return render_template("admin/model_form.html", model_version=None, form_values=form_values)


@admin_bp.route("/models/<int:model_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_model(model_id):
    model_version = db.get_or_404(ModelVersion, model_id)
    form_values = {}
    if request.method == "POST":
        form_values, errors = read_model_form(request.form)
        if errors:
            flash_errors(errors)
        else:
            for field_name, value in form_values.items():
                setattr(model_version, field_name, value)
            log_activity("model_update", f"Sửa phiên bản model {model_version.name}")
            flash("Đã cập nhật phiên bản model.", "success")
            return redirect(url_for("admin.models"))
    return render_template("admin/model_form.html", model_version=model_version, form_values=form_values)


@admin_bp.post("/models/<int:model_id>/activate")
@admin_required
def activate_model(model_id):
    model_version = db.get_or_404(ModelVersion, model_id)
    for item in db.session.scalars(db.select(ModelVersion)).all():
        item.is_active = item.id == model_version.id
    log_activity("model_activate", f"Chọn model đang dùng: {model_version.name} ({model_version.file_name})")
    flash(f"Model đang dùng: {model_version.name}.", "success")
    return redirect(url_for("admin.models"))


@admin_bp.post("/models/<int:model_id>/delete")
@admin_required
def delete_model(model_id):
    model_version = db.get_or_404(ModelVersion, model_id)
    if model_version.is_active:
        flash("Không thể xóa model đang dùng. Hãy chọn model khác trước.", "danger")
        return redirect(url_for("admin.models"))
    name = model_version.name
    db.session.delete(model_version)
    log_activity("model_delete", f"Xóa phiên bản model {name}")
    flash("Đã xóa phiên bản model.", "success")
    return redirect(url_for("admin.models"))


@admin_bp.get("/logs")
@admin_required
def logs():
    action = request.args.get("action", "")
    user_id = request.args.get("user_id", type=int)
    date_from = parse_form_date(request.args.get("date_from"))
    date_to = parse_form_date(request.args.get("date_to"))
    query = db.select(ActivityLog)
    if action in ACTION_LABELS:
        query = query.where(ActivityLog.action == action)
    if user_id:
        query = query.where(ActivityLog.user_id == user_id)
    if date_from:
        query = query.where(ActivityLog.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.where(ActivityLog.created_at < datetime.combine(date_to + timedelta(days=1), time.min))
    query = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
    pagination = paginate_query(query, "LOGS_PER_PAGE")
    filter_args = {key: value for key, value in {
        "action": action if action in ACTION_LABELS else "",
        "user_id": user_id or "",
        "date_from": date_from.isoformat() if date_from else "",
        "date_to": date_to.isoformat() if date_to else "",
    }.items() if value}
    return render_template(
        "admin/logs.html",
        pagination=pagination,
        filter_args=filter_args,
        users=db.session.scalars(db.select(User).order_by(User.username)).all(),
        action_labels=ACTION_LABELS,
    )
