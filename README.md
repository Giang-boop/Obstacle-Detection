# 🚧 Hệ thống hỗ trợ người khiếm thị nhận diện vật cản và cảnh báo bằng giọng nói

## 1. Giới thiệu

**Obstacle Detection and Voice Warning System** là hệ thống hỗ trợ người khiếm thị nhận diện vật cản bằng **Computer Vision** và đưa ra cảnh báo bằng **giọng nói tiếng Việt**.

Hệ thống sử dụng camera để thu nhận hình ảnh, mô hình **YOLOv8** để phát hiện vật thể, sau đó ước lượng khoảng cách tương đối dựa trên kích thước **Bounding Box**.

Khi phát hiện vật cản nằm trong vùng phía trước và ở khoảng cách nguy hiểm, hệ thống sẽ phát cảnh báo bằng giọng nói thông qua thư viện **pyttsx3**.

### Công nghệ sử dụng

* Python
* YOLOv8
* OpenCV
* PyTorch
* Ultralytics
* pyttsx3
* Computer Vision
* Deep Learning

---

## 2. Yêu cầu hệ thống

### 2.1. Phần cứng

* Máy tính Windows
* Webcam hoặc camera USB
* CPU/GPU hỗ trợ chạy YOLOv8
* Loa hoặc tai nghe

### 2.2. Phần mềm

* Python 3.10+
* Windows 10/11
* Visual Studio Code hoặc IDE tương đương
* Git

---

## 3. Cấu trúc thư mục

```text
Obstacle-Detection/
│
├── best.pt
├── config.py
├── detection_utils.py
├── tts_engine.py
├── main.py
├── check_voice.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

### Chức năng các file

| File                 | Chức năng                                             |
| -------------------- | ----------------------------------------------------- |
| `main.py`            | Chương trình chính, xử lý camera và nhận diện         |
| `config.py`          | Cấu hình các thông số của hệ thống                    |
| `detection_utils.py` | Xử lý nhận diện, tính khoảng cách và mức độ nguy hiểm |
| `tts_engine.py`      | Xử lý cảnh báo bằng giọng nói                         |
| `check_voice.py`     | Kiểm tra giọng nói trên Windows                       |
| `best.pt`            | Mô hình YOLOv8 đã được huấn luyện                     |
| `requirements.txt`   | Danh sách thư viện Python cần cài đặt                 |
| `.gitignore`         | Các file/thư mục không đưa lên GitHub                 |
| `README.md`          | Tài liệu hướng dẫn project                            |

---

# 4. Cài đặt

## 4.1. Clone project

```bash
git clone https://github.com/Giang-boop/Obstacle-Detection.git
cd Obstacle-Detection
```


---

## 4.2. Tạo môi trường ảo

Trên Windows:

```bash
python -m venv venv
```

### Kích hoạt môi trường

**PowerShell:**

```powershell
venv\Scripts\Activate.ps1
```

**Command Prompt:**

```cmd
venv\Scripts\activate
```

**Git Bash:**

```bash
source venv/Scripts/activate
```

---

## 4.3. Cài đặt thư viện

```bash
pip install -r requirements.txt
```

Kiểm tra Ultralytics:

```bash
yolo checks
```

Hoặc:

```bash
python -c "from ultralytics import YOLO; print('Ultralytics OK')"
```

---

# 5. Model YOLOv8

Project sử dụng mô hình **YOLOv8** đã được huấn luyện trên dataset nhận diện vật cản.

File model:

```text
best.pt
```

Model được đặt trong thư mục gốc của project:

```text
Obstacle-Detection/
│
├── best.pt
├── config.py
├── detection_utils.py
├── tts_engine.py
└── main.py
```

Trong chương trình:

```python
MODEL_PATH = "best.pt"
```

---

# 6. Cấu hình hệ thống

Các thông số chính của hệ thống được cấu hình trong:

```text
config.py
```

Một số thông số quan trọng:

```python
MODEL_PATH = "best.pt"
CAMERA_ID = 0
CONFIDENCE_THRESHOLD = 0.50
```

Trong đó:

| Thông số               | Ý nghĩa                               |
| ---------------------- | ------------------------------------- |
| `MODEL_PATH`           | Đường dẫn tới model YOLO              |
| `CAMERA_ID`            | ID của camera                         |
| `CONFIDENCE_THRESHOLD` | Ngưỡng confidence để xác nhận vật thể |

---

# 7. Nhận diện vật cản

Mô hình YOLOv8 được sử dụng để phát hiện nhiều loại vật thể trong môi trường giao thông và sinh hoạt.

Dataset gồm **25 lớp**:

| ID | Class                |
| -: | -------------------- |
|  0 | Bike                 |
|  1 | Building             |
|  2 | Car                  |
|  3 | Person               |
|  4 | Stairs               |
|  5 | Traffic sign         |
|  6 | Electrical Pole      |
|  7 | Road                 |
|  8 | Motorcycle           |
|  9 | Dustbin              |
| 10 | Dog                  |
| 11 | Manhole              |
| 12 | Tree                 |
| 13 | Guard rail           |
| 14 | Pedestrian crosswalk |
| 15 | Truck                |
| 16 | Bus                  |
| 17 | Bench                |
| 18 | Traffic Cone         |
| 19 | Fire hydrant         |
| 20 | Teraffic Barrel      |
| 21 | Plant Pot            |
| 22 | Electrical Box       |
| 23 | Chair                |
| 24 | Bicycle Rack         |

> `Teraffic Barrel` được giữ nguyên theo tên class trong dataset.

Tên các lớp được chuyển sang **tiếng Việt** để sử dụng trong nội dung cảnh báo bằng giọng nói.

---

# 8. Ước lượng khoảng cách

Hệ thống sử dụng kích thước **Bounding Box** của vật thể để ước lượng khoảng cách tương đối.

Công thức:

$$
d = \frac{K}{h}
$$

Trong đó:

* `d`: khoảng cách ước lượng.
* `K`: hệ số hiệu chỉnh của từng loại vật thể.
* `h`: chiều cao Bounding Box tính theo pixel.

Phương pháp này cho phép hệ thống xác định tương đối vật thể đang ở gần hay xa camera.

> Khoảng cách thu được mang tính **ước lượng tương đối**, độ chính xác phụ thuộc vào quá trình hiệu chỉnh hệ số `K`, góc camera, kích thước thực tế của vật thể và điều kiện môi trường.

---

# 9. Cảnh báo vật cản

Hệ thống phân loại vật cản theo khoảng cách và mức độ nguy hiểm.

Hệ thống ưu tiên cảnh báo:

1. Vật cản nằm trong vùng phía trước.
2. Vật cản có khoảng cách gần.
3. Vật cản có mức độ nguy hiểm cao.
4. Vật cản gần nhất trong trường hợp có nhiều vật thể cùng xuất hiện.

Ví dụ:

```text
Person
Distance: 1.42 m
WARNING
```

---

# 10. Cảnh báo bằng giọng nói

Project sử dụng thư viện:

```text
pyttsx3
```

`pyttsx3` là thư viện **Text-to-Speech hoạt động offline**, không yêu cầu kết nối API để phát giọng nói.

Hệ thống được thiết kế để sử dụng giọng nói tiếng Việt **Microsoft An** trên Windows.

### Một số câu cảnh báo

```text
Phía trước có người, khoảng cách 1.5 mét.
```

```text
Cảnh báo, có xe máy phía trước.
```

```text
Nguy hiểm, vật cản ở khoảng cách rất gần.
```

File xử lý TTS:

```text
tts_engine.py
```

---

# 11. Chạy chương trình

## 11.1. Chạy camera realtime

Đảm bảo webcam đã được kết nối.

Sau đó chạy:

```bash
python main.py
```

Camera sẽ được mở và hệ thống bắt đầu nhận diện vật cản.

Nhấn:

```text
Q
```

để thoát chương trình.

---

# 12. Chạy với video

Có thể thay đổi chế độ đầu vào trong:

```text
config.py
```

Ví dụ:

```python
INPUT_MODE = 2
```

Sau đó cấu hình đường dẫn video:

```python
VIDEO_PATH = "test.mp4"
```

Chạy chương trình:

```bash
python main.py
```

---

# 13. Hiển thị kết quả

Trong quá trình chạy, hệ thống hiển thị các thông tin:

* Bounding Box của vật thể.
* Tên vật thể.
* Confidence.
* Khoảng cách ước lượng.
* Mức độ nguy hiểm.
* FPS.
* Vùng nhận diện phía trước.
* Vật cản gần nhất.

Ví dụ:

```text
Person 0.86

Distance: 1.42m

WARNING
```

---

# 14. Sơ đồ hoạt động

```text
┌──────────────────┐
│      CAMERA      │
│  Thu nhận hình ảnh│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│      OpenCV      │
│ Tiền xử lý ảnh   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│      YOLOv8      │
│ Object Detection │
└────────┬─────────┘
         │
         ▼
┌────────────────────────┐
│     Bounding Box       │
│ Object + Confidence    │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  Distance Estimation   │
│     d = K / h          │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│      Danger Level      │
│  Đánh giá mức nguy hiểm│
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│    Vietnamese TTS      │
│        pyttsx3         │
└──────────┬─────────────┘
           │
           ▼
┌──────────────────┐
│  Voice Warning   │
│ Cảnh báo bằng    │
│     giọng nói    │
└──────────────────┘
```

---


# 15. Một số lệnh thường dùng
>>>>>>> b018dca (docs: update README)

### Kiểm tra Python

```bash
python --version
```

### Kiểm tra pip

```bash
pip --version
```

### Kiểm tra OpenCV

```bash
python -c "import cv2; print(cv2.__version__)"
```

### Kiểm tra Ultralytics

```bash
python -c "from ultralytics import YOLO; print('Ultralytics OK')"
```

### Kiểm tra pyttsx3

```bash
python -c "import pyttsx3; print('pyttsx3 OK')"
```

### Chạy chương trình

```bash
python main.py
```

---

# 16. Một số lỗi thường gặp

## 16.1. Không tìm thấy model

Lỗi:

```text
FileNotFoundError: best.pt
```

Kiểm tra file:

```text
Obstacle-Detection/
└── best.pt
```

Hoặc sửa đường dẫn trong `config.py`:

```python
MODEL_PATH = "đường_dẫn_tới_best.pt"
```

---

## 16.2. Không mở được camera

Kiểm tra:

```python
CAMERA_ID = 0
```

Nếu máy có nhiều camera, thử:

```python
CAMERA_ID = 1
```

hoặc:

```python
CAMERA_ID = 2
```

Đồng thời kiểm tra camera có đang được sử dụng bởi ứng dụng khác hay không.

---

## 16.3. Không nhận diện được vật thể

Kiểm tra các yếu tố:

* Model `best.pt`.
* `CONFIDENCE_THRESHOLD`.
* Điều kiện ánh sáng.
* Khoảng cách tới camera.
* Góc đặt camera.
* Chất lượng hình ảnh.
* Chất lượng dataset huấn luyện.
* Phạm vi dữ liệu huấn luyện.

Có thể thử giảm:

```python
CONFIDENCE_THRESHOLD = 0.50
```

xuống:

```python
CONFIDENCE_THRESHOLD = 0.30
```

để kiểm tra khả năng phát hiện.

> Không nên giảm ngưỡng quá thấp khi đánh giá chính thức vì có thể làm tăng nhận diện sai.

---

## 16.4. Giọng nói không phát

Kiểm tra Windows Speech và giọng **Microsoft An**.

Kiểm tra thư viện:

```bash
pip install pyttsx3
```

Sau đó chạy lại:

```bash
python main.py
```

Có thể sử dụng file:

```text
check_voice.py
```

để kiểm tra danh sách giọng nói trên máy tính.

---

# 17. Dataset

Dataset được sử dụng để huấn luyện mô hình nhận diện vật cản.

Dataset gồm:

* 25 classes.
* Training set.
* Validation set.
* Test set.

Dataset huấn luyện **không được đưa trực tiếp vào repository GitHub** để tránh làm repository có kích thước quá lớn.

---

# 18. Tài liệu và kiến thức sử dụng

Project được xây dựng dựa trên các kiến thức:

* Computer Vision
* Object Detection
* YOLOv8
* OpenCV
* Distance Estimation
* Text-to-Speech
* Python
* Deep Learning

---

# 19. Lưu ý

Các file có kích thước lớn như:

```text
best.pt
```

có thể được lưu trữ riêng thay vì commit trực tiếp lên GitHub.

Khi clone project, cần đặt model vào thư mục gốc:

```text
Obstacle-Detection/
│
├── best.pt
├── config.py
├── detection_utils.py
├── tts_engine.py
└── main.py
```

Dataset cũng không cần đưa trực tiếp vào repository nếu kích thước quá lớn.

---

# 20. Tác giả

## Obstacle Detection and Voice Warning System

**Đề tài:**

> Hệ thống hỗ trợ người khiếm thị nhận diện vật cản và cảnh báo bằng giọng nói sử dụng Computer Vision

### Công nghệ

* Python
* YOLOv8
* OpenCV
* PyTorch
* Ultralytics
* pyttsx3
* Computer Vision
* Deep Learning
