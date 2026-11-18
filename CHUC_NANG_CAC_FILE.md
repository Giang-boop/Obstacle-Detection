# 📋 Chức năng từng file trong dự án

Tài liệu mô tả chi tiết **từng file** của hệ thống BlindAssist, kèm lý do xóa các file
của cấu trúc cũ khi tái cấu trúc repo.

> Phân lớp tổng thể: **App thiết bị** (`detector/`, 15 file) · **Backend máy chủ**
> (`server/*.py` + `app/*.py` + `routes/`, 30 file) · **Frontend máy chủ**
> (`templates/` + `static/`, 37 file) · **Huấn luyện** (`training/`, 5 file).

---

## 1. 📱 `detector/` — App thiết bị (15 file)

| File | Chức năng |
|---|---|
| `main.py` | Chương trình chính: đọc tham số dòng lệnh, vòng lặp YOLO, vẽ HUD/box/mũi tên, phím Q thoát / S gửi SOS, đồng bộ dữ liệu lên máy chủ khi thoát |
| `config.py` | Toàn bộ thông số: ngưỡng confidence (0.40 / xe hai bánh 0.20), hệ số K từng lớp, khoảng cách 5/3 m, TTC 4/2 s, tốc độ đọc 165/200, URL máy chủ, khóa thiết bị |
| `camera_reader.py` | Đọc camera/video ở thread riêng — luôn giữ frame mới nhất, bỏ frame cũ khi YOLO xử lý chậm |
| `frame_pipeline.py` | Pipeline 1 khung hình: YOLO → trích box → ByteTrack → đo khoảng cách → tracker → AlertManager |
| `detection_utils.py` | Công thức `d = K/h`, EMA làm mượt, vùng trái/giữa/phải, lọc người ngồi trên xe, sinh câu cảnh báo tiếng Việt, vẽ box theo mức |
| `box_tracker.py` | Gọi BYTETracker của Ultralytics, gán track_id ổn định cho từng vật |
| `tracker.py` | TrackedObject + ObjectTracker: lịch sử 20 điểm, hồi quy tính tốc độ, dự đoán 1 giây tới, TTC cảnh báo sớm, giữ vật mất dấu |
| `alert_manager.py` | Xếp hạng độ nguy hiểm (risk_score), quyết định đọc: tăng mức / vật mới nguy hiểm hơn / gần hơn / nhắc lại |
| `tts_engine.py` | Giọng SAPI tiếng Việt (Microsoft An) qua comtypes, hàng đợi ưu tiên 1 chỗ, ngắt giữa câu, bỏ câu lỗi thời |
| `server_client.py` | Thread đồng bộ máy chủ: hello/heartbeat, mở–đóng phiên, gửi lô cảnh báo (buffer 500), retry SOS, nhận cấu hình từ xa |
| `runtime_settings.py` | Cấu hình chạy thời gian thực: áp cấu hình máy chủ đè lên config.py (ngưỡng, TTS, tắt lớp vật, hệ số K) |
| `perf_logger.py` | Ghi log hiệu năng mỗi lần chạy: frames.csv, objects.csv, alerts.csv, summary.json + ghi video demo theo timeline |
| `check_voice.py` | Tiện ích liệt kê giọng nói trên máy, thử đọc giọng Microsoft An |
| `requirements.txt` | Danh sách thư viện detector: ultralytics, opencv-python, numpy, pyttsx3, comtypes, lapx, requests… |
| `best.pt` | Model YOLOv8n đã huấn luyện — 17 lớp vật cản (mAP50 = 0.901) |

---

## 2. 🌐 `server/` — Máy chủ web (68 file)

### ⚙️ Backend — gốc máy chủ (6 file)

| File | Chức năng |
|---|---|
| `run.py` | Điểm chạy `py -m server.run`: tùy chọn `--https` / `--port` / `--no-warmup`, in địa chỉ LAN |
| `config.py` | Cấu hình Flask: SQLite, SECRET_KEY, số trang, biến môi trường `BLINDASSIST_*` |
| `certs.py` | Sinh chứng chỉ HTTPS tự ký (thư viện cryptography) để điện thoại mở camera trong LAN |
| `seed.py` | Lệnh `py -m server.seed` — khởi tạo lại CSDL |
| `requirements.txt` | Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Werkzeug, SQLAlchemy, cryptography, ultralytics, opencv, lapx, requests |
| `__init__.py` | Đánh dấu package Python |

### ⚙️ Backend — lõi ứng dụng `server/app/` (12 file)

| File | Chức năng |
|---|---|
| `app/__init__.py` | `create_app()`: đăng ký 12 blueprint, CSRF, Flask-Login, filter Jinja, trang lỗi 403/404/CSRF |
| `app/models.py` | 11 bảng CSDL: User, BlindPerson, Guardianship, Device, DeviceConfig, ObjectClass, ModelVersion, UsageSession, Alert, SosEvent, ActivityLog |
| `app/web_detection.py` | Máy chủ tự chạy YOLO cho chế độ `/thiet-bi`: DetectionEngine (tự fallback CPU), WebSessionStore (trạng thái bám vết riêng từng phiên), tự đóng phiên idle |
| `app/services.py` | Nghiệp vụ dùng chung: payload cấu hình thiết bị, thống kê dashboard, touch thiết bị online |
| `app/access.py` | Phân quyền: `admin_required`, kiểm tra quyền giám hộ người thân (truy cập người khác → 403) |
| `app/validation.py` | Regex kiểm tra email / số điện thoại / tên đăng nhập |
| `app/seed_data.py` | Dữ liệu khởi tạo: 2 tài khoản, người khiếm thị, thiết bị DEV-0001, 17 lớp vật cản, 2 model version |
| `app/labels.py` | Nhãn tiếng Việt cho mức cảnh báo, vị trí, trạng thái SOS, hành động |
| `app/timeutils.py` | Parse giờ ISO 8601 client gửi lên, định dạng ngày giờ / duration hiển thị |
| `app/activity.py` | Ghi nhật ký hệ thống: đăng nhập, đổi cấu hình, xử lý SOS, thêm/sửa/xóa |
| `app/pagination.py` | Phân trang dùng chung cho mọi trang danh sách |
| `app/extensions.py` | Khởi tạo db / csrf / login_manager |

### ⚙️ Backend — 12 blueprint `server/app/routes/` (13 file)

| File | Chức năng |
|---|---|
| `routes/admin.py` | Quản trị: users, blind persons, devices, classes, models, logs — CRUD + khóa/mở tài khoản |
| `routes/device_api.py` | REST API thiết bị: hello, config, heartbeat, sessions, alerts (lô 500), sos, detect (nhận JPEG → YOLO → trả objects + alert) |
| `routes/alerts.py` | `/alerts`: lịch sử cảnh báo, lọc theo người/ngày/mức/loại vật, phân trang, xuất CSV |
| `routes/auth.py` | `/login` `/logout` `/profile`, đổi mật khẩu, ghi nhật ký đăng nhập |
| `routes/statistics.py` | `/statistics`: biểu đồ 14 ngày, theo loại vật, theo mức, theo vị trí |
| `routes/devices.py` | `/devices`: danh sách thiết bị + trang cấu hình cảnh báo từ xa |
| `routes/blind_persons.py` | `/blind-persons`: danh sách + chi tiết người khiếm thị (theo quyền giám hộ) |
| `routes/web_api.py` | `/api/web/summary` — AJAX dashboard, tự làm mới mỗi 5 giây |
| `routes/sos.py` | `/sos`: danh sách tín hiệu cầu cứu, đánh dấu đã xử lý kèm ghi chú |
| `routes/dashboard.py` | `/` bảng điều khiển: thẻ số liệu, trạng thái thiết bị, SOS mới, 10 cảnh báo mới nhất |
| `routes/blind_mode.py` | `/thiet-bi` + `/thiet-bi/mo/<id>` — chế độ người khiếm thị chạy trên trình duyệt |
| `routes/sessions.py` | `/sessions`: phiên sử dụng (thời lượng, FPS, độ trễ, số cảnh báo) |
| `routes/__init__.py` | Đánh dấu package |

### 🎨 Frontend — `server/app/templates/` (26 file HTML/Jinja2)

| File | Chức năng |
|---|---|
| `base.html` | Bố cục chung: sidebar điều hướng, thanh SOS đỏ, poll 5 giây |
| `_macros.html` | Component dùng lại: phân trang, badge mức, nút xóa |
| `auth/login.html` | Trang đăng nhập (có nút "Tôi là người khiếm thị — Mở chế độ thiết bị") |
| `auth/profile.html` | Hồ sơ cá nhân, đổi mật khẩu |
| `dashboard/index.html` | Bảng điều khiển: 4 thẻ số liệu, thiết bị, SOS, 10 cảnh báo mới |
| `blind_persons/list.html` | Danh sách người khiếm thị |
| `blind_persons/detail.html` | Chi tiết người khiếm thị + thống kê riêng |
| `alerts/list.html` | Lịch sử cảnh báo + bộ lọc + xuất CSV |
| `statistics/index.html` | 4 biểu đồ Chart.js |
| `sos/list.html` | Quản lý SOS, nút "Đã xử lý" |
| `devices/list.html` | Danh sách thiết bị |
| `devices/config.html` | Form cấu hình cảnh báo từ xa (ngưỡng, TTS, tắt lớp vật) |
| `sessions/list.html` | Phiên sử dụng |
| `blind_mode/index.html` | **Màn hình thiết bị**: nút BẮT ĐẦU/DỪNG/SOS, canvas camera, đọc cảnh báo |
| `errors/error.html` · `errors/standalone.html` | Trang lỗi 403/404/CSRF |
| `admin/users.html` · `user_form.html` | Quản trị tài khoản |
| `admin/blind_persons.html` · `blind_person_form.html` | Quản trị người khiếm thị |
| `admin/devices.html` · `device_form.html` | Quản trị thiết bị |
| `admin/classes.html` | Quản trị lớp vật cản (K, trọng số nguy hiểm) |
| `admin/models.html` · `model_form.html` | Quản trị phiên bản model YOLO |
| `admin/logs.html` | Xem nhật ký hệ thống |

### 🎨 Frontend — `server/app/static/` (11 file)

| File | Chức năng |
|---|---|
| `css/app.css` | Style toàn hệ thống |
| `css/blind_mode.css` | Style màn hình thiết bị |
| `js/app.js` | AJAX `/api/web/summary` 5 giây, thanh SOS + âm báo |
| `js/statistics.js` | Vẽ biểu đồ Chart.js |
| `js/blind_mode.js` | Mở camera trình duyệt, nén + gửi khung JPEG, vẽ box, Web Speech API tiếng Việt, phím cách/S/M |
| `vendor/bootstrap/` (2 file) | Bootstrap 5.3.3 (css + js bundle) — tải sẵn, chạy offline |
| `vendor/bootstrap-icons/` (3 file) | Bootstrap Icons 1.11.3 (css + font woff/woff2) |
| `vendor/chartjs/chart.umd.min.js` | Chart.js 4.4.1 |

---

## 3. 🏋️ `training/` — Huấn luyện model (5 file)

| File | Chức năng |
|---|---|
| `chuan_bi_dataset.py` | Chuẩn bị dataset từ nguồn ảnh gốc (tách train/val/test) |
| `tao_oversample.py` | Tạo bản oversample cho lớp vật hiếm |
| `train.py` | Huấn luyện YOLOv8n 60 epoch, imgsz 640 |
| `danh_gia.py` | Đánh giá model trên tập test (precision/recall/mAP theo lớp) |
| `ve_bieu_do.py` | Vẽ biểu đồ so sánh giữa các lần huấn luyện |

---

## 4. 🔒 File chung (2 file)

| File | Chức năng |
|---|---|
| `.gitignore` | Chặn: CSDL `instance/`, logs, test_video.mp4, dataset, venv, `__pycache__`, tests/, docs/, sơ đồ, hình ảnh, số liệu, file txt |
| `README.md` | Hướng dẫn cài đặt – chạy – kiến trúc – API – lỗi thường gặp (23 mục) |

---

## 5. 🗑️ Phụ lục — Lý do xóa các file cấu trúc cũ (commit tái cấu trúc)

| File/thư mục cũ đã xóa | Lý do | Thay thế bằng |
|---|---|---|
| `main.py` | Bản detector cũ: 25 lớp, không tracking, không máy chủ | `detector/main.py` (bản 2.0) |
| `config.py` | Thiếu cấu hình tracking, TTC, máy chủ | `detector/config.py` |
| `detection_utils.py` | Chưa có EMA, bộ lọc rider, câu cảnh báo ngắn | `detector/detection_utils.py` |
| `tts_engine.py` | pyttsx3 thuần — không ngắt giữa câu | `detector/tts_engine.py` (SAPI comtypes) |
| `check_voice.py` | Di chuyển vị trí cho đúng cấu trúc mới | `detector/check_voice.py` |
| `best.pt` | Model cũ 25 lớp lần huấn luyện 1 | `detector/best.pt` (17 lớp, lần 2) |
| `requirements.txt` | Thiếu comtypes, lapx | `detector/requirements.txt` |
| `notebooks/` (3 file .ipynb) | Notebook thí nghiệm giai đoạn đầu; kết quả đã tổng hợp vào training/ và báo cáo | — (xem lại qua History) |
| `.gitattributes` | Không dùng Git LFS (best.pt 6 MB < 100 MB) | — |
| `README.md` | Mô tả cấu trúc cũ, lệch với code thật | `README.md` mới |
| `.gitignore` | Thiếu quy tắc chặn DB, logs, dataset, tests, docs, hình ảnh, txt | `.gitignore` mới |

---

*Lưu ý: các file test (`tests/`, 160 test), tài liệu chi tiết (`docs/`), sơ đồ và kết quả
đánh giá được giữ trên máy nhóm, không đưa lên repo theo quy ước chung của nhóm.*
