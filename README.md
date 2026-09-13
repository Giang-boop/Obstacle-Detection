Obstacle Detection and Voice Warning System



1\. Giới thiệu



Obstacle Detection là hệ thống hỗ trợ người khiếm thị nhận diện vật cản bằng Computer Vision và đưa ra cảnh báo bằng giọng nói tiếng Việt.



Hệ thống sử dụng camera để thu nhận hình ảnh, mô hình YOLOv8 để phát hiện vật thể, sau đó ước lượng khoảng cách tương đối dựa trên kích thước bounding box. Khi phát hiện vật cản nằm trong vùng phía trước và ở khoảng cách nguy hiểm, hệ thống sẽ phát cảnh báo bằng giọng nói thông qua pyttsx3.





2\. Yêu cầu hệ thống



2.1. Phần cứng



Máy tính Windows



Webcam hoặc camera USB



CPU/GPU hỗ trợ chạy YOLOv8



Loa hoặc tai nghe



2.2. Phần mềm



Python 3.10+



Windows 10/11



Visual Studio Code hoặc IDE tương đương



Git



3\. Cấu trúc thư mục



Obstacle-Detection/

│

├── best.pt

├── config.py

├── detection\_utils.py

├── tts\_engine.py

├── main.py

│

├── requirements.txt

├── README.md

└── .gitignore





Chức năng các file



FileChức năng







main.py



Chương trình chính, xử lý camera và nhận diện



config.py



Cấu hình hệ thống



detection\_utils.py



Tính khoảng cách, mức độ nguy hiểm và cảnh báo



tts\_engine.py



Xử lý cảnh báo bằng giọng nói



best.pt



Mô hình YOLOv8 đã được huấn luyện



requirements.txt



Danh sách thư viện Python



.gitignore



Các file/thư mục không đưa lên GitHub



README.md



Tài liệu hướng dẫn project



4\. Cài đặt



4.1. Clone project



git clone https://github.com/<USERNAME>/Obstacle-Detection.git

cd Obstacle-Detection





Thay <USERNAME> bằng tên tài khoản GitHub của bạn.



4.2. Tạo môi trường ảo



Trên Windows:



python -m venv venv





Kích hoạt môi trường:



venv\\Scripts\\activate





Nếu sử dụng Git Bash:



source venv/Scripts/activate





4.3. Cài đặt thư viện



pip install -r requirements.txt





Kiểm tra Ultralytics:



yolo checks





5\. Model YOLO



Project sử dụng mô hình YOLOv8 đã được huấn luyện trên dataset nhận diện vật cản.



File model được sử dụng:



best.pt





Đặt model trong thư mục gốc:



Obstacle-Detection/

└── best.pt





Trong chương trình:



MODEL\_PATH = "best.pt"





Do file model có thể có kích thước lớn, không nên đưa model lên GitHub nếu vượt giới hạn dung lượng của GitHub. Có thể lưu model riêng và đặt vào thư mục project trước khi chạy.



6\. Cấu hình hệ thống



Các thông số chính được cấu hình trong:



config.py





M7. Nhận diện vật cản



Mô hình YOLOv8 được sử dụng để phát hiện nhiều loại vật thể.



Dataset sử dụng 25 lớp:



0  Bike

1  Building

2  Car

3  Person

4  Stairs

5  Traffic sign

6  Electrical Pole

7  Road

8  Motorcycle

9  Dustbin

10 Dog

11 Manhole

12 Tree

13 Guard rail

14 Pedestrian crosswalk

15 Truck

16 Bus

17 Bench

18 Traffic Cone

19 Fire hydrant

20 Teraffic Barrel

21 Plant Pot

22 Electrical Box

23 Chair

24 Bicycle Rack





Tên lớp được chuyển sang tiếng Việt để sử dụng trong cảnh báo.



8\. Ước lượng khoảng cách



Hệ thống sử dụng kích thước bounding box của vật thể để ước lượng khoảng cách tương đối.



Công thức:



d = K / h





Trong đó:



d: khoảng cách ước lượng.



K: hệ số hiệu chỉnh của từng loại vật thể.



h: chiều cao bounding box tính theo pixel.







9\. Cảnh báo vật cản



Hệ thống chia khoảng cách thành các mức cảnh báo.





Hệ thống ưu tiên cảnh báo vật cản gần nhất nằm trong vùng phía trước người sử dụng.



10\. Cảnh báo bằng giọng nói



Project sử dụng thư viện:



pyttsx3





Đây là giải pháp Text-to-Speech hoạt động offline.



Hệ thống được thiết kế để sử dụng giọng nói tiếng Việt Microsoft An trên Windows.



Ví dụ cảnh báo:



Phía trước có người, khoảng cách 1.5 mét.



Cảnh báo, có xe máy phía trước.



Nguy hiểm, vật cản ở khoảng cách rất gần.





File xử lý TTS:



tts\_engine.py





11\. Chạy chương trình



11.1. Chạy camera realtime



Đảm bảo webcam đã được kết nối.



Sau đó chạy:



python main.py





Camera sẽ được mở và hệ thống bắt đầu nhận diện vật cản.



Nhấn:



Q





để thoát chương trình.



12\. Chạy với video



Có thể thay đổi chế độ đầu vào trong:



config.py





Ví dụ:



INPUT\_MODE = 2





Sau đó cấu hình đường dẫn video:



VIDEO\_PATH = "test.mp4"





Chạy:



python main.py





13\. Hiển thị kết quả



Trong quá trình chạy, hệ thống hiển thị:



Bounding box của vật thể.



Tên vật thể.



Confidence.



Khoảng cách ước lượng.



Mức độ nguy hiểm.



FPS.



Vùng nhận diện phía trước.



Vật cản gần nhất.



Ví dụ:



Person 0.86

Distance: 1.42m

WARNING





14\. Sơ đồ hoạt động



&#x20;            ┌──────────────┐

&#x20;            │    Camera    │

&#x20;            └──────┬───────┘

&#x20;                   │

&#x20;                   ▼

&#x20;            ┌──────────────┐

&#x20;            │    OpenCV    │

&#x20;            └──────┬───────┘

&#x20;                   │

&#x20;                   ▼

&#x20;            ┌──────────────┐

&#x20;            │    YOLOv8    │

&#x20;            │ Object       │

&#x20;            │ Detection    │

&#x20;            └──────┬───────┘

&#x20;                   │

&#x20;                   ▼

&#x20;         ┌────────────────────┐

               │ Bounding Box       │

&#x20;         │ Object + Confidence│

&#x20;         └─────────┬──────────┘

&#x20;                   │

&#x20;                   ▼

&#x20;         ┌────────────────────┐

&#x20;         │ Distance Estimation│

&#x20;         └─────────┬──────────┘

&#x20;                   │

&#x20;                   ▼

&#x20;         ┌────────────────────┐

&#x20;         │ Danger Level       │

&#x20;         └─────────┬──────────┘

&#x20;                   │

&#x20;                   ▼

&#x20;         ┌────────────────────┐

&#x20;         │ Vietnamese TTS     │

&#x20;         │     pyttsx3        │

&#x20;         └─────────┬──────────┘

&#x20;                   │

&#x20;                   ▼

&#x20;            ┌──────────────┐

&#x20;            │ Voice Warning │

&#x20;            └──────────────┘





15\. Một số lệnh thường dùng



Kiểm tra Python



python --version





Kiểm tra pip



pip --version





Kiểm tra OpenCV



python -c "import cv2; print(cv2.\_\_version\_\_)"





Kiểm tra Ultralytics



python -c "from ultralytics import YOLO; print('Ultralytics OK')"





Kiểm tra pyttsx3



python -c "import pyttsx3; print('pyttsx3 OK')"





Chạy chương trình



python main.py





17\. Một số lỗi thường gặp



Lỗi không tìm thấy model



FileNotFoundError: best.pt





Kiểm tra file:



Obstacle-Detection/

└── best.pt





hoặc sửa:



MODEL\_PATH = "đường\_dẫn\_tới\_best.pt"





Không mở được camera



Kiểm tra:



CAMERA\_ID = 0





Nếu máy có nhiều camera, thử:



CAMERA\_ID = 1





hoặc:



CAMERA\_ID = 2





Đồng thời kiểm tra camera có đang được sử dụng bởi ứng dụng khác hay không.



Không nhận diện được vật thể



Kiểm tra:



Model best.pt.



CONFIDENCE\_THRESHOLD.



Điều kiện ánh sáng.



Khoảng cách tới camera.



Góc đặt camera.



Chất lượng hình ảnh.



Chất lượng và phạm vi dữ liệu huấn luyện.



Có thể thử giảm:



CONFIDENCE\_THRESHOLD = 0.50





xuống:



CONFIDENCE\_THRESHOLD = 0.30





để kiểm tra khả năng phát hiện.



Giọng nói không phát



Kiểm tra Windows Speech và giọng Microsoft An.



Sau đó kiểm tra thư viện:



pip install pyttsx3





và chạy lại:



python main.py





18\. Tài liệu



Project được xây dựng dựa trên các nội dung:



Computer Vision



Object Detection



YOLOv8



OpenCV



Distance Estimation



Text-to-Speech



Python



Deep Learning



19\. Lưu ý



Dataset huấn luyện không được đưa trực tiếp vào repository GitHub để tránh repository có kích thước quá lớn.



Các file model lớn như:



best.pt





cũng có thể được lưu trữ riêng thay vì commit trực tiếp lên GitHub.

Khi clone project, cần đặt model vào thư mục gốc trước khi chạy:



Obstacle-Detection/

├── best.pt

├── config.py

├── detection\_utils.py

├── tts\_engine.py

└── main.py





20\. Tác giả



Obstacle Detection and Voice Warning System



Đề tài:



Hệ thống hỗ trợ người khiếm thị nhận diện vật cản và cảnh báo bằng giọng nói sử dụng Computer Vision



Công nghệ:



Python

YOLOv8

OpenCV

PyTorch

pyttsx3

Computer Vision

Deep Learning



