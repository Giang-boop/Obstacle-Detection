# 🚧 Hệ thống hỗ trợ người khiếm thị nhận diện vật cản và cảnh báo bằng giọng nói

**Obstacle Detection and Voice Warning System (BlindAssist)** — hệ thống nhận diện vật cản
bằng Computer Vision (YOLOv8), theo dõi đa vật thể (ByteTrack), ước lượng khoảng cách và
cảnh báo bằng **giọng nói tiếng Việt** theo thời gian thực, hoàn toàn **local**, không cần
Internet, không gọi API AI.

Hệ thống gồm **2 thành phần**:

| Thành phần | Vai trò |
|---|---|
| **App thiết bị** (`detector/`) | Chạy trên máy có webcam: nhận diện vật cản, đọc cảnh báo tiếng Việt, gửi dữ liệu lên máy chủ, gửi SOS |
| **Máy chủ web** (`server/`) | Quản lý người khiếm thị / thiết bị / lịch sử cảnh báo / thống kê, cấu hình cảnh báo từ xa, nhận SOS, và chạy chế độ người khiếm thị ngay trên trình duyệt (`/thiet-bi`) |

---

## 1. Tính năng chính

- **Camera đọc ở thread riêng, luôn giữ frame mới nhất**: nếu YOLO xử lý chậm hơn camera thì
  frame cũ bị bỏ qua, hệ thống luôn phản ứng với hiện trường mới.
- **Theo dõi đa vật thể ByteTrack**: gán ID ổn định, chống nhảy nhãn (bỏ phiếu theo lớp),
  giữ vật khi mất dấu vài frame, dự đoán vị trí 1 giây tới (vẽ mũi tên).
- **Cảnh báo thông minh**: xếp hạng độ nguy hiểm (khoảng cách, loại vật, vị trí trái/giữa/phải),
  mỗi lần chỉ đọc 1 câu cho vật nguy hiểm nhất; vật nguy hiểm hơn xuất hiện thì câu mới
  ưu tiên, câu đang đọc bị ngắt.
- **Cảnh báo sớm bằng TTC**: vật đang lao tới (TTC < 4 s) được nâng mức cảnh báo **trước khi**
  vào vùng nguy hiểm theo khoảng cách.
- **Cấu hình từ xa**: máy chủ chỉnh ngưỡng cảnh báo, tốc độ/âm lượng đọc, tắt lớp vật —
  app áp dụng ngay không cần khởi động lại.
- **SOS một phím**: nhấn `S` (app) hoặc nút trên web → người thân thấy ngay trên dashboard
  kèm âm báo.
- **Đo hiệu năng tự động**: mỗi lần chạy ghi log frames/objects/alerts/summary để so sánh
  trước–sau (profile A/B/C).
- **Chạy nhận diện ngay trên trình duyệt** `/thiet-bi`: máy chủ nhận khung JPEG từ webcam
  trình duyệt (máy tính hoặc điện thoại qua HTTPS), chạy đúng luồng xử lý của app detector.

## 2. Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ | Python 3.10+ |
| Nhận diện vật thể | YOLOv8n 17 lớp (Ultralytics) — model `best.pt` |
| Theo dõi vật thể | ByteTrack (tích hợp Ultralytics) |
| Xử lý ảnh | OpenCV, NumPy |
| Giọng nói tiếng Việt | Windows SAPI trực tiếp qua **comtypes** (dò giọng bằng pyttsx3) |
| Máy chủ | Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF (CSRF), SQLite |
| Giao diện web | Bootstrap 5.3, Bootstrap Icons, Chart.js (đã tải sẵn vào `static/vendor/`, chạy offline) |
| HTTPS cho điện thoại | Chứng chỉ tự ký tạo bằng `cryptography` |
| Đa luồng | `threading` + `queue` |

## 3. Yêu cầu hệ thống

### Phần cứng
- Máy tính Windows 10/11
- Webcam hoặc camera USB (app cũng chạy được bằng video kiểm thử `test_video.mp4`)
- GPU NVIDIA (nếu có) hoặc CPU
- Loa hoặc tai nghe

### Phần mềm
- Python 3.10 trở lên
- Git (khi làm việc nhóm)
- Windows SAPI có giọng tiếng Việt (khuyến nghị **Microsoft An**) — cài trong
  *Settings > Time & Language > Language > thêm tiếng Việt, tick Text-to-speech*

## 4. Kiến trúc và phân lớp hệ thống

Hệ thống dùng kiến trúc **Flask server-side rendering** — frontend (Jinja2 templates +
static CSS/JS) và backend (routes + services + models) cùng nằm trong `server/` theo quy ước
chuẩn của Flask, không phải mô hình SPA tách folder. Ranh giới 2 lớp tách bạch rõ ràng:

| Lớp kiến trúc | Vị trí | Số file | Công nghệ |
|---|---|---|---|
| **App thiết bị** (client) | `detector/` | 15 | Python, YOLOv8, ByteTrack, OpenCV, SAPI |
| **Backend máy chủ** (API + nghiệp vụ + CSDL) | `server/*.py` + `server/app/*.py` + `server/app/routes/` | 30 | Flask, SQLAlchemy, SQLite |
| **Frontend máy chủ** (giao diện web) | `server/app/templates/` + `server/app/static/` | 37 | Jinja2, Bootstrap 5.3, Chart.js 4.4 |
| Kiểm thử | `tests/` | 15 | unittest, Playwright (E2E) |
| Huấn luyện model | `training/` | 70 | Ultralytics |
| Tài liệu + sơ đồ | `docs/` | 24 | Word, draw.io |

Luồng giao tiếp:

```
[App thiết bị] ──REST API /api/device/*──▶ [Backend Flask] ──render──▶ [Frontend web]
     (detector/)                               (routes + models)          (templates+static)
        ▲                                          │
        └──────── cấu hình từ xa / SOS ◀───────────┘
[Trình duyệt người khiếm thị] ──khung JPEG /api/device/detect──▶ Backend chạy YOLO
```

Frontend chỉ gọi AJAX thật ở vài điểm: `app.js` hỏi `/api/web/summary` mỗi 5 giây (cảnh báo
SOS), `blind_mode.js` đẩy khung camera lên `/api/device/detect`, còn lại trang được Flask
render trực tiếp.

## 5. Cấu trúc thư mục chi tiết

```
03_ma-nguon/
│
├── .gitignore                          # Quy định file không đưa lên git (DB, dataset, venv…)
│
├── detector/  ────────────────────────  📱 ỨNG DỤNG THIẾT BỊ (15 file)
│   │   # Chạy trên máy có webcam của người khiếm thị.
│   │   # Giao diện = cửa sổ OpenCV (HUD, bounding box) + giọng nói.
│   ├── main.py                         # Điểm chạy chính: tham số lệnh, vòng lặp, HUD
│   ├── config.py                       # Toàn bộ thông số: ngưỡng, hệ số K, TTS, máy chủ
│   ├── camera_reader.py                # Đọc camera/video ở thread riêng (bỏ frame cũ)
│   ├── frame_pipeline.py               # Pipeline 1 khung hình: YOLO → đo → theo dõi → cảnh báo
│   ├── detection_utils.py              # d=K/h, EMA, vùng trái/giữa/phải, câu cảnh báo, vẽ box
│   ├── box_tracker.py                  # ByteTrack — gán ID ổn định cho vật
│   ├── tracker.py                      # Trạng thái vật: lịch sử, tốc độ, TTC, giữ vật mất dấu
│   ├── alert_manager.py                # Xếp hạng nguy hiểm, chu kỳ đọc, chọn vật ưu tiên
│   ├── tts_engine.py                   # Giọng SAPI tiếng Việt, hàng đợi 1 chỗ, ngắt giữa câu
│   ├── server_client.py                # Đồng bộ cảnh báo/phiên/SOS lên máy chủ (thread)
│   ├── runtime_settings.py             # Cấu hình thời gian thực (đè config.py khi máy chủ gửi)
│   ├── perf_logger.py                  # Log hiệu năng frames/objects/alerts/summary.json
│   ├── check_voice.py                  # Tiện ích kiểm tra giọng tiếng Việt trên máy
│   ├── requirements.txt                # ultralytics, opencv, numpy, comtypes, pyttsx3…
│   └── best.pt                         # Model YOLOv8n đã huấn luyện (17 lớp, ~6 MB)
│
├── server/  ───────────────────────────  🌐 MÁY CHỦ WEB (69 file) — BACKEND + FRONTEND
│   │
│   │   ⚙️ BACKEND — xử lý nghiệp vụ (30 file Python)
│   ├── run.py                          # Khởi chạy máy chủ: py -m server.run (--https, --port)
│   ├── seed.py                         # Khởi tạo CSDL: py -m server.seed
│   ├── certs.py                        # Sinh chứng chỉ HTTPS tự ký cho mạng LAN
│   ├── config.py                       # Cấu hình Flask: SQLite, số trang, biến môi trường
│   ├── requirements.txt                # Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF…
│   ├── README_SERVER.txt               # Hướng dẫn vận hành máy chủ (tài liệu nội bộ)
│   └── app/
│       ├── __init__.py                 # Tạo Flask app, đăng ký blueprint, CSRF, login
│       ├── models.py                   # CSDL: User, BlindPerson, Guardianship, Device,
│       │                               #   DeviceConfig, ObjectClass, ModelVersion,
│       │                               #   UsageSession, Alert, SosEvent, ActivityLog
│       ├── extensions.py               # Khởi tạo db / csrf / login_manager
│       ├── services.py                 # Nghiệp vụ dùng chung (cấu hình thiết bị, thống kê…)
│       ├── access.py                   # Phân quyền: admin_required, quyền giám hộ
│       ├── validation.py               # Kiểm tra email/SĐT/tên đăng nhập
│       ├── labels.py                   # Nhãn tiếng Việt cho mức/vị trí/hành động
│       ├── activity.py                 # Ghi nhật ký hệ thống
│       ├── timeutils.py                # Xử lý thời gian ISO, định dạng hiển thị
│       ├── pagination.py               # Phân trang dùng chung
│       ├── seed_data.py                # Dữ liệu khởi tạo: 2 tài khoản, thiết bị, 17 lớp
│       ├── web_detection.py            # Máy chủ chạy YOLO cho chế độ /thiet-bi
│       │                               #   (import pipeline từ detector/)
│       └── routes/                     # 12 blueprint = REST API + luồng trang
│           ├── auth.py                 # /login /logout /profile
│           ├── dashboard.py            # / bảng điều khiển
│           ├── blind_persons.py        # /blind-persons người khiếm thị
│           ├── alerts.py               # /alerts lịch sử cảnh báo + xuất CSV
│           ├── statistics.py           # /statistics biểu đồ
│           ├── sos.py                  # /sos xử lý SOS
│           ├── devices.py              # /devices cấu hình từ xa
│           ├── sessions.py             # /sessions phiên sử dụng
│           ├── admin.py                # /admin/* quản trị user/thiết bị/lớp/model/log
│           ├── device_api.py           # /api/device/* REST API cho app thiết bị
│           ├── web_api.py              # /api/web/* dữ liệu AJAX cho trang
│           └── blind_mode.py           # /thiet-bi chế độ người khiếm thị trên web
│
│   │   🎨 FRONTEND — giao diện trình duyệt (37 file)
│   └── app/
│       ├── templates/                  # HTML/Jinja2 server-side rendering (26 file)
│       │   ├── base.html               # Bố cục chung: sidebar, thanh SOS
│       │   ├── _macros.html            # Component dùng lại (phân trang, badge…)
│       │   ├── auth/                   # login, profile (2)
│       │   ├── dashboard/              # bảng điều khiển (1)
│       │   ├── blind_persons/          # danh sách, chi tiết (2)
│       │   ├── alerts/                 # lịch sử cảnh báo + lọc + CSV (1)
│       │   ├── statistics/             # biểu đồ Chart.js (1)
│       │   ├── sos/                    # xử lý SOS (1)
│       │   ├── devices/                # danh sách, cấu hình từ xa (2)
│       │   ├── sessions/               # phiên sử dụng (1)
│       │   ├── admin/                  # quản trị: users, devices, classes, models,
│       │   │                           #   logs + form tương ứng (10)
│       │   ├── blind_mode/             # /thiet-bi camera + đọc cảnh báo (1)
│       │   └── errors/                 # trang 403/404/CSRF (2)
│       └── static/
│           ├── css/app.css             # Style toàn hệ thống
│           ├── css/blind_mode.css      # Style chế độ người khiếm thị
│           ├── js/app.js               # AJAX /api/web/summary, âm báo SOS (mỗi 5s)
│           ├── js/statistics.js        # Vẽ biểu đồ Chart.js
│           ├── js/blind_mode.js        # Camera trình duyệt, gửi khung, vẽ box, TTS web
│           └── vendor/                 # Thư viện tải sẵn → chạy OFFLINE không cần Internet
│               ├── bootstrap/          # Bootstrap 5.3.3 (css + js bundle)
│               ├── bootstrap-icons/    # Icons 1.11.3 (css + font woff/woff2)
│               └── chartjs/            # Chart.js 4.4.1
│
├── tests/  ────────────────────────────  🧪 KIỂM THỬ (15 file, 160 test)
│   ├── server_testcase.py              # Lớp cơ sở: app + CSDL tạm riêng cho từng test
│   ├── test_server_auth.py             # Đăng nhập, khóa tài khoản, nhật ký (13)
│   ├── test_server_permissions.py      # Phân quyền giám hộ (8)
│   ├── test_server_alerts_admin.py     # Quản trị cảnh báo/người/thiết bị (12)
│   ├── test_server_pagination.py       # Phân trang, lọc (15)
│   ├── test_server_device_api.py       # REST API thiết bị (11)
│   ├── test_server_web_detect.py       # Nhận diện qua trình duyệt (16)
│   ├── test_server_config_sos.py       # Cấu hình từ xa + SOS (6)
│   ├── test_server_https.py            # Chứng chỉ HTTPS (3)
│   ├── test_e2e_web.py                 # E2E Playwright web (18)
│   ├── test_e2e_blind_mode.py          # E2E chế độ thiết bị (2)
│   ├── test_detection_filters.py       # Bộ lọc detector: chồng box, rider (18)
│   ├── test_logic.py                   # Logic khoảng cách, mức, câu cảnh báo (23)
│   ├── test_server_client.py           # Đồng bộ lên máy chủ (15)
│   └── test_tts.py                     # Hàng đợi/ngắt giọng — đọc thật (5)
│
├── training/  ─────────────────────────  🏋️ HUẤN LUYỆN MODEL (70 file)
│   ├── HUONG_DAN_TRAIN.txt             # Hướng dẫn huấn luyện từng bước
│   ├── chuan_bi_dataset.py             # Chuẩn bị dataset (dataset để ngoài repo)
│   ├── tao_oversample.py               # Tăng số mẫu lớp hiếm
│   ├── train.py                        # Huấn luyện YOLOv8n
│   ├── danh_gia.py                     # Đánh giá trên tập test
│   ├── ve_bieu_do.py                   # Vẽ biểu đồ so sánh
│   └── ket_qua_danh_gia/               # 64 file kết quả: biểu đồ precision/recall/mAP,
│                                       #   confusion matrix, số liệu theo lớp, khung so sánh video
│
└── docs/  ─────────────────────────────  📚 TÀI LIỆU (24 file)
    ├── CODE_NOTES.docx                 # Giải thích mã nguồn chi tiết
    ├── so_do_luu_xu_ly.png             # Sơ đồ luồng xử lý
    └── so-do/                          # 22 sơ đồ .drawio: usecase, kiến trúc, triển khai,
                                        #   tuần tự, hoạt động, lớp, ERD
```

**Không đưa lên git** (theo `.gitignore`): `server/instance/blindassist.db` (CSDL thật),
`detector/test_video.mp4` (video kiểm thử), `detector/logs/` (log mỗi lần chạy),
dataset huấn luyện, `venv/`, `__pycache__/`.

## 6. Cài đặt

```bash
# 1. Tạo môi trường ảo
python -m venv venv
# PowerShell:  venv\Scripts\Activate.ps1
# CMD:         venv\Scripts\activate
# Git Bash:    source venv/Scripts/activate

# 2. Cài thư viện cho cả 2 thành phần
pip install -r detector/requirements.txt
pip install -r server/requirements.txt
```

Kiểm tra nhanh:

```bash
python -c "from ultralytics import YOLO; print('Ultralytics OK')"
python -c "import cv2; print('OpenCV', cv2.__version__)"
python -c "import flask; print('Flask OK')"
python detector/check_voice.py      # kiểm tra giọng tiếng Việt trên máy
```

> Model `best.pt` đã nằm sẵn trong `detector/`. Tài khoản, thiết bị và dữ liệu ban đầu
> được tạo bởi lệnh seed (mục 7).

## 7. Khởi tạo cơ sở dữ liệu (máy chủ)

```bash
# chạy trong thư mục 03_ma-nguon/
python -m server.seed
```

Dữ liệu khởi tạo (chạy lại bao nhiêu lần cũng được — xóa và tạo lại):

- Tài khoản: `admin / Admin@123` (quản trị), `nguoithan / Nguoithan@123` (người thân)
- Người khiếm thị "Nguyễn Văn An" + người thân "Nguyễn Thị Hoa" (quan hệ: Con)
- Thiết bị `DEV-0001`, khóa API `demo-device-key-0001`, cấu hình mặc định:
  cảnh báo < 5 m, nguy hiểm < 3 m, tốc độ đọc 165/200, âm lượng 1.0
- 17 lớp vật cản của model (tên tiếng Việt, hệ số K)
- 2 phiên bản model YOLOv8n với chỉ số đánh giá trên tập test
- **Không** có cảnh báo/phiên giả — dữ liệu này do app detector gửi lên khi chạy thật

## 8. Chạy máy chủ

```bash
python -m server.run
```

Mở trình duyệt: <http://127.0.0.1:5000> — máy khác trong LAN: `http://<IP>:5000`
(khi khởi động, máy chủ in sẵn các địa chỉ LAN).

| Tùy chọn | Ý nghĩa |
|---|---|
| `--https` | Chạy HTTPS chứng chỉ tự ký → **điện thoại mở được camera** tại `https://<IP>:5000/thiet-bi` |
| `--port 5001` | Đổi cổng (hoặc biến môi trường `BLINDASSIST_PORT`) |
| `--no-warmup` | Không nạp sẵn model YOLO khi khởi động |
| `BLINDASSIST_INFER_DEVICE=auto\|cpu\|0` | Chọn nơi chạy YOLO của máy chủ (mặc định auto) |
| `BLINDASSIST_DATABASE_URI` | Đổi nơi lưu CSDL SQLite |

### Chức năng web

| Trang | Nội dung |
|---|---|
| `/login`, `/profile` | Đăng nhập, sửa hồ sơ, đổi mật khẩu |
| `/` Bảng điều khiển | Số liệu, trạng thái thiết bị, SOS chưa xử lý, 10 cảnh báo mới nhất (tự làm mới 5 giây, SOS mới → thanh đỏ + âm báo) |
| `/blind-persons` | Người khiếm thị (người thân chỉ thấy người mình giám hộ, truy cập người khác → 403) |
| `/alerts` | Lịch sử cảnh báo, lọc theo người/ngày/mức/loại vật, phân trang, xuất CSV mở bằng Excel |
| `/statistics` | Biểu đồ theo ngày (14 ngày), theo loại vật, theo mức, theo vị trí |
| `/sos` | Danh sách SOS, nút "Đã xử lý" kèm ghi chú |
| `/devices/<id>/config` | **Cấu hình cảnh báo từ xa**: ngưỡng, tốc độ đọc, âm lượng, câu ngắn, tắt lớp vật |
| `/sessions` | Phiên sử dụng (thời lượng, FPS, độ trễ, số cảnh báo) |
| `/admin/users` · `/admin/devices` · `/admin/classes` · `/admin/models` · `/admin/logs` | Quản trị (chỉ admin) |

## 9. Chạy app detector

```bash
cd detector

python main.py                        # theo config (mặc định: camera, có cửa sổ, có tiếng)
python main.py --camera               # ép chạy camera
python main.py --video test_video.mp4 # chạy video file
python main.py --headless             # không hiện cửa sổ (dùng khi đo đạc)
python main.py --mute                 # tắt tiếng
python main.py --device cpu           # ép chạy CPU
python main.py --no-realtime          # xử lý lần lượt toàn bộ frame video (không bỏ frame)
python main.py --save-video out.mp4   # ghi video demo theo timeline thời gian thật
python main.py --max-frames 300       # dừng sau N frame
python main.py --model best.pt --run-name ten_chay
python main.py --offline              # không kết nối máy chủ
```

**Phím điều khiển:** `Q` — thoát · `S` — gửi tín hiệu cầu cứu (SOS).

### Profile so sánh từng nhóm cải tiến

| Profile | Nội dung |
|---|---|
| `--profile A` | Bản gốc: đọc tuần tự, không làm mượt, không tracking |
| `--profile B` | A + latest frame buffer + làm mượt EMA (ghép vật theo IoU) |
| `--profile C` | B + ByteTrack (ID vật thể, giữ vật khi mất dấu, dự đoán chuyển động) |

Không truyền `--profile` thì dùng đúng các cờ trong `config.py` (mặc định đầy đủ = C).

## 10. Chế độ người khiếm thị trên trình duyệt — `/thiet-bi`

Không cần chạy lệnh Python trên thiết bị — mở web là dùng được:

1. Vào `http://127.0.0.1:5000/thiet-bi` (máy tính có webcam) hoặc
   `https://<IP>:5000/thiet-bi` trên điện thoại (phải chạy `python -m server.run --https`,
   chọn "Nâng cao → Tiếp tục truy cập" vì chứng chỉ tự ký).
2. Lần đầu nhập mã thiết bị (`DEV-0001`) và khóa thiết bị (`demo-device-key-0001`);
   trình duyệt ghi nhớ. Người thân/quản trị có thể mở sẵn từ trang Thiết bị.
3. Nút **BẮT ĐẦU** (phím cách): mở camera, tạo phiên, gửi khung JPEG lên máy chủ
   (tối đa 10 khung/giây), vẽ hộp nhận diện và đọc cảnh báo bằng giọng trình duyệt
   (ưu tiên giọng vi-VN, câu nguy hiểm ngắt câu cũ).
4. Nút **SOS** (phím S), **Tắt tiếng** (phím M). Trang gửi heartbeat 10 giây/lần →
   thiết bị hiện "Trực tuyến" trên dashboard.
5. Máy chủ chạy **đúng luồng** của app detector (import `frame_pipeline`, ByteTrack,
   `AlertManager`…), giữ trạng thái bám vết riêng từng phiên, áp dụng cấu hình từ xa,
   lưu cảnh báo vào lịch sử thống kê.

## 11. REST API cho thiết bị (JSON, header `X-Device-Key`)

| Endpoint | Chức năng |
|---|---|
| `POST /api/device/hello` | Đăng nhập thiết bị, nhận cấu hình hiện tại |
| `GET /api/device/config` | Lấy cấu hình cảnh báo (ngưỡng, TTS, lớp bị tắt…) |
| `POST /api/device/heartbeat` | Báo sống (quá 30 s không liên lạc = ngoại tuyến) |
| `POST /api/device/sessions` · `PUT /api/device/sessions/<id>` | Mở/đóng phiên sử dụng kèm thống kê |
| `POST /api/device/alerts` | Gửi lô cảnh báo (tối đa 500/lần) |
| `POST /api/device/sos` | Gửi tín hiệu cầu cứu |
| `POST /api/device/detect?session_id=<id>` | Gửi khung JPEG → nhận vật thể + cảnh báo (chế độ web) |

Thử nhanh:

```bash
curl -X POST -H "X-Device-Key: demo-device-key-0001" -H "Content-Type: application/json" \
     -d "{}" http://127.0.0.1:5000/api/device/heartbeat
```

Sai khóa → 401. Ảnh quá 3 MB → 413. Phiên không gửi khung quá 120 giây tự đóng.

## 12. Model YOLOv8n — 17 lớp

Model `detector/best.pt` (YOLOv8n, huấn luyện 60 epoch, imgsz 640) nhận diện 17 lớp:

| Class | Tiếng Việt | Class | Tiếng Việt |
|---|---|---|---|
| Bike | xe đạp | Truck | xe tải |
| Building | tòa nhà | Bench | ghế băng |
| Car | ô tô | Traffic Cone | cọc tiêu giao thông |
| Person | người | Electrical Box | tủ điện |
| Stairs | cầu thang | Chair | ghế |
| Electrical Pole | cột điện | Dog | chó |
| Road | đường | Manhole | nắp cống |
| Motorcycle | xe máy | Tree | cây |
| Dustbin | thùng rác | Guard rail | lan can |

- `CONFIDENCE_THRESHOLD = 0.40` cho lớp chung; xe hai bánh dùng ngưỡng thấp hơn
  `TWO_WHEELER_CONFIDENCE = 0.20`; một số lớp có ngưỡng riêng (`CLASS_CONFIDENCE`).
- `CLASS_ALIASES` gộp `Bike` → `Motorcycle` (tránh đổi ID khi model nhảy nhãn).
- Người ngồi trên xe máy bị loại (`remove_riders`) để chỉ báo "xe máy".
- `Road` vẫn vẽ box nhưng **không cảnh báo** (bề mặt nền, không phải vật cản).

Chỉ số lần huấn luyện thứ 2 trên tập test obstacle17 (1.629 ảnh, 1.882 đối tượng):
Precision 0.891 · Recall 0.843 · mAP50 0.901 · mAP50-95 0.724.

## 13. Ước lượng khoảng cách

```
      K_class
d = -----------
       h
```

- `K_class`: hằng số hiệu chỉnh riêng từng lớp (`K_VALUES` trong `config.py`), lớp không
  có K riêng dùng `DEFAULT_K = 600`.
- `h`: chiều cao bounding box (pixel).
- Kết quả làm mượt bằng EMA: `d_mượt = 0.35·d_mới + 0.65·d_cũ`; vật **đang tiến lại gần**
  dùng hệ số phản ứng nhanh hơn `APPROACH_EMA_ALPHA = 0.6`.
- Số liệu mang tính ước lượng tương đối, phụ thuộc hiệu chỉnh K, góc camera và môi trường.

## 14. Theo dõi vật thể và cảnh báo sớm

- **ByteTrack** gán ID ổn định trong `model.track(..., persist=True)`.
- **Chống nhảy nhãn**: mỗi vật bỏ phiếu lớp theo confidence, chọn lớp thắng cuộc.
- **Chống nhấp nháy**: vật phải xuất hiện liên tiếp `MIN_CONFIRM_FRAMES = 2` frame mới được
  cảnh báo; mất dưới `LOST_FRAMES = 15` frame vẫn giữ lại (box mảnh + nhãn "giu").
- **Phân tích chuyển động**: hồi quy tuyến tính trên 20 vị trí gần nhất (~1–2 s) tính tốc độ
  tiến lại / ngang / dọc, dự đoán vị trí sau 1 giây (vẽ mũi tên).
- **TTC** (time-to-collision = khoảng cách / tốc độ tiến lại), chỉ tính khi tốc độ tiến
  ≥ 0.15 m/s và vật ở giữa hoặc sắp vào giữa, cách ≤ 6 m:
  - TTC < 4 s → nâng **WARNING** · TTC < 2 s → nâng **DANGER**

## 15. Cảnh báo 3 mức

| Mức | Điều kiện |
|---|---|
| **SAFE** | khoảng cách ≥ 5 m và không có cảnh báo sớm |
| **WARNING** | khoảng cách < 5 m, hoặc TTC < 4 s |
| **DANGER** | khoảng cách < 3 m, hoặc TTC < 2 s |

- Vùng quan sát: **TRÁI (20%) – GIỮA (60%) – PHẢI (20%)**; vật hai bên chỉ cảnh báo khi
  DANGER hoặc đang lao vào giữa.
- **Xếp hạng ưu tiên** (`risk_score`): khoảng cách hiệu dụng nhỏ nhất đứng đầu (vật hai bên
  bị "phạt" nhân 0.6); cách nhau ≤ 0,1 m thì ưu tiên loại nguy hiểm hơn
  (xe tải/buýt 1.6 > ô tô/xe máy 1.5 > chó/cầu thang/nắp cống 1.3 > người 1.2).
- **Nhịp cảnh báo**: nhắc lại mỗi 1,5 s (WARNING) / 1 s (DANGER) / 3 s (vật đứng yên);
  hai câu cách nhau tối thiểu 0,5 s. Báo ngay khi tăng mức, có vật mới nguy hiểm hơn,
  hoặc cùng vật đến gần thêm ≥ 0,5 m.
- **Câu ngắn** (mặc định bật), vật càng gần câu càng ngắn:

| Mức | Ví dụ |
|---|---|
| WARNING | "Xe máy phía trước, 2 mét." / "Ô tô bên trái đang tới, 3,5 mét." |
| DANGER | "Gấp! Xe máy, 1 mét!" / "Gấp! Xe máy bên trái, 0,8 mét!" |

## 16. Giọng nói tiếng Việt

- Đọc bằng **SAPI.SpVoice** gọi trực tiếp qua comtypes (pyttsx3 chỉ dùng để dò danh sách
  giọng) — dùng lại 1 đối tượng, ngắt ngay bằng cờ `SVSFPurgeBeforeSpeak`.
- Ưu tiên giọng **Microsoft An** → kho giọng OneCore → giọng tiếng Việt khác.
- **Hàng đợi 1 chỗ**: luôn giữ câu mới nhất/nguy hiểm nhất; câu chờ mức thấp hơn bị thay,
  câu mới mức cao hơn ngắt câu đang đọc (chỉ ngắt sau khi câu cũ đọc ≥ 1,2 s).
- **Câu lỗi thời bị bỏ**: chờ quá 1,5 s không còn đúng hiện trường → không đọc.
- Tốc độ đọc: 165 từ/phút (WARNING), 200 (DANGER — nghe gấp hơn).

## 17. Hiển thị

- Box màu theo mức: xanh (SAFE) → cam (WARNING) → đỏ (DANGER) → xám (LOST); vật đang được
  ưu tiên cảnh báo có viền trắng.
- Nhãn: `#ID tên-đối-tượng confidence | khoảng cách m` (không dấu vì `cv2.putText` không
  vẽ được dấu tiếng Việt).
- Mũi tên dự đoán chuyển động, nhãn vùng TRAI | GIUA | PHAI, vị trí + TTC + "giu".
- HUD: FPS, thời gian YOLO (ms), độ trễ frame, số frame bị bỏ, profile, vật gần nhất,
  câu cảnh báo vừa đọc (giữ 2 giây), thông báo SOS.

## 18. Đo hiệu năng và log

Mỗi lần chạy tạo thư mục `detector/logs/<tên>_<thời gian>/`:

| File | Nội dung |
|---|---|
| `frames.csv` | Từng frame: thời gian inference, xử lý, độ trễ, FPS, vật gần nhất |
| `objects.csv` | Từng vật từng frame: ID, lớp, confidence, khoảng cách thô/mượt, vị trí, mức, tốc độ, TTC |
| `alerts.csv` | Từng câu cảnh báo: lúc phát hiện, lúc đọc, độ trễ, trạng thái (đọc/ngắt/thay/bỏ) |
| `summary.json` | Tổng kết: số frame, FPS trung bình, p95 độ trễ, số cảnh báo, độ rung, nhấp nháy… |

`--save-video out.mp4` ghi video demo theo **timeline thời gian thật** (giây thứ t của video
= đúng hình màn hình ở giây thứ t) — thuận tiện ghép tiếng làm minh chứng.

## 19. Kiểm thử

```bash
# chạy trong thư mục 03_ma-nguon/
python -m unittest discover -s tests -p "test_server*.py"   # 99 test máy chủ
python -m unittest discover -s tests -p "test_logic.py"     # 23 test logic
python -m unittest discover -s tests -p "test_detection_filters.py"  # 18 test bộ lọc
python -m unittest discover -s tests -p "test_server_client.py"      # 15 test đồng bộ
python -m unittest discover -s tests -p "test_tts.py"       # 5 test giọng nói (có đọc thật)

# Toàn bộ (kể cả E2E Playwright — cần cài playwright + ffmpeg để tạo camera giả .y4m):
python -m unittest discover -s tests -p "test_*.py"
```

Test dùng CSDL tạm riêng (tempfile) — không ảnh hưởng dữ liệu thật.
Ảnh chụp E2E lưu ở `tests/e2e_artifacts/` (đổi bằng `BLINDASSIST_SCREENSHOT_DIR`).

## 20. Huấn luyện model (training/)

Xem `training/HUONG_DAN_TRAIN.txt`. Các bước chính:

```bash
python training/chuan_bi_dataset.py   # chuẩn bị dataset từ nguồn ảnh gốc
python training/tao_oversample.py     # tạo bản oversample cho lớp hiếm
python training/train.py              # huấn luyện YOLOv8n (kết quả ở training/runs/)
python training/danh_gia.py           # đánh giá trên tập test → training/ket_qua_danh_gia/
python training/ve_bieu_do.py         # vẽ biểu đồ so sánh
```

Model mới nhất (lần 2, đang dùng) chép về `detector/best.pt` và cập nhật trong
máy chủ: **Quản trị → Model** (`/admin/models`).
Dataset **không** đưa vào repository (kích thước lớn, để riêng).

## 21. Lỗi thường gặp

| Lỗi | Nguyên nhân / cách xử lý |
|---|---|
| `FileNotFoundError: best.pt` | Model phải nằm trong `detector/`, hoặc sửa `MODEL_PATH` trong `config.py` |
| Camera không mở | Đổi `CAMERA_ID` (0→1→2); đóng ứng dụng đang chiếm camera (Zoom, Teams…) |
| Không nhận diện được vật | Kiểm tra ánh sáng; giảm `CONFIDENCE_THRESHOLD` xuống 0.30 để thử (không giảm quá thấp khi đánh giá chính thức) |
| Giọng nói không phát | Chạy `python detector/check_voice.py`; cài giọng tiếng Việt trong Windows Settings |
| Giọng đọc tiếng Anh | Chưa có giọng tiếng Việt — cài theo mục 3 |
| Khoảng cách sai | Hiệu chỉnh lại `K_VALUES` cho webcam/camera của bạn (mục 13) |
| Cài `ultralytics` xong báo lỗi `yaml_load` | Dự án tương thích **ultralytics 8.3.x** (khuyến nghị 8.3.120); bản 8.4+ đã bỏ API này |
| Trình duyệt không mở được camera từ điện thoại | Phải chạy `python -m server.run --https`; điện thoại và máy chủ cùng mạng Wi-Fi; mở cổng 5000 trên Windows Firewall cho mạng Private |
| Đăng nhập web báo lỗi CSRF | Tải lại trang rồi đăng nhập lại |

## 22. Bảo mật và lưu ý an toàn

- Mật khẩu băm bằng werkzeug.security; mọi biểu mẫu web có mã CSRF; phân quyền kiểm tra ở
  máy chủ; nhật ký hệ thống ghi đăng nhập, đổi cấu hình, xử lý SOS, thêm/sửa/xóa.
- Khi triển khai thật nên đặt biến môi trường `BLINDASSIST_SECRET_KEY` bằng chuỗi ngẫu nhiên.
- Hệ thống là **công cụ hỗ trợ**, không thay thế hoàn toàn các giác quan hoặc người dẫn
  đường — số khoảng cách là ước lượng tương đối. Chỉ kiểm thử trong môi trường kiểm soát,
  có người giám sát; không di chuyển chỉ dựa vào cảnh báo của phần mềm.

## 23. Tác giả

**Obstacle Detection and Voice Warning System — Nhóm 11**
Đề tài: *Hệ thống hỗ trợ người khiếm thị nhận diện vật cản và cảnh báo bằng giọng nói
sử dụng Computer Vision*

Công nghệ: Python · YOLOv8 · OpenCV · ByteTrack · comtypes/SAPI · Flask · SQLite
