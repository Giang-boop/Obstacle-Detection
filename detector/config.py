# ======================================================================
#  FILE: detector/config.py
#  CHUC NANG: Toàn bộ thông số hệ thống: ngưỡng confidence (0.40, xe hai bánh 0.20), hệ số K từng lớp, khoảng cách WARNING/DANGER 5/3 m, TTC 4/2 s, tốc độ đọc 165/200, URL máy chủ, khóa thiết bị.
# ======================================================================

MODEL_PATH = "best.pt"

INPUT_MODE = 2

CAMERA_ID = 0

CAMERA_WIDTH = 1280

CAMERA_HEIGHT = 720

VIDEO_PATH = "test_video.mp4"

VIDEO_REALTIME = True

VIDEO_SLOWDOWN = 1.0

SHOW_WINDOW = True

CONFIDENCE_THRESHOLD = 0.40

MAX_DET = 50

DEVICE = None

IMG_SIZE = 640

CLASS_ALIASES = {
    "Bike": "Motorcycle",
}

TWO_WHEELER_CLASSES = {
    "Motorcycle",
}

TWO_WHEELER_CONFIDENCE = 0.20

CLASS_CONFIDENCE = {
    "Manhole": 0.60,
    "Dog": 0.30,
    "Electrical Pole": 0.25,
    "Guard rail": 0.30,
    "Person": 0.40,
}

OVERLAP_IOU = 0.50

CROSS_CLASS_NMS_PAIRS = (
    ("Person", "Dog"),
)

PERSON_IN_VEHICLE_RATIO = 0.60

RIDER_OVERLAP = 0.30

USE_LATEST_FRAME_BUFFER = True

USE_DISTANCE_SMOOTHING = True

USE_TRACKING = True

TRACKER_CONFIG = "bytetrack.yaml"

K_VALUES = {
    "Bike": 650.0,
    "Building": 1000.0,
    "Car": 900.0,
    "Person": 600.0,
    "Stairs": 800.0,
    "Traffic sign": 400.0,
    "Electrical Pole": 1000.0,
    "Road": 1000.0,
    "Motorcycle": 700.0,
    "Dustbin": 500.0,
    "Dog": 450.0,
    "Manhole": 350.0,
    "Tree": 1000.0,
    "Guard rail": 800.0,
    "Pedestrian crosswalk": 500.0,
    "Truck": 1100.0,
    "Bus": 1200.0,
    "Bench": 500.0,
    "Traffic Cone": 350.0,
    "Fire hydrant": 300.0,
    "Teraffic Barrel": 500.0,
    "Plant Pot": 400.0,
    "Electrical Box": 500.0,
    "Chair": 450.0,
    "Bicycle Rack": 600.0,
}

DEFAULT_K = 600.0

WARNING_DISTANCE = 5.0

DANGER_DISTANCE = 3.0

ALERT_COOLDOWN = 1.5

WARNING_INTERVAL = ALERT_COOLDOWN

DANGER_INTERVAL = 1.0

MIN_ALERT_GAP = 0.5

CLOSER_ALERT_STEP = 0.5

INTERRUPT_CLOSER_STEP = 0.5

INTERRUPT_MIN_SPEAK_SECONDS = 1.2

SHORT_ALERT_MESSAGES = True

IGNORED_CLASSES = {
    "Road",
    "Pedestrian crosswalk",
}

CLASS_RISK_WEIGHT = {
    "Car": 1.5,
    "Motorcycle": 1.5,
    "Bike": 1.4,
    "Truck": 1.6,
    "Bus": 1.6,
    "Person": 1.2,
    "Dog": 1.3,
    "Stairs": 1.3,
    "Manhole": 1.3,
}

DEFAULT_RISK_WEIGHT = 1.0

CENTER_ZONE = 0.60

POSITION_NAMES = {
    "LEFT": "bên trái",
    "CENTER": "phía trước",
    "RIGHT": "bên phải",
}

POSITION_RISK_WEIGHT = {
    "LEFT": 0.6,
    "CENTER": 1.0,
    "RIGHT": 0.6,
}

EMA_ALPHA = 0.35

LOST_FRAMES = 15

MIN_CONFIRM_FRAMES = 2

TRACK_HISTORY = 20

PREDICT_SECONDS = 1.0

TTC_WARNING = 4.0

TTC_DANGER = 2.0

MIN_APPROACH_SPEED = 0.15

EARLY_WARNING_MAX_DISTANCE = 6.0

MOTION_WINDOW = 2.0

MIN_MOTION_POINTS = 4

APPROACH_EMA_ALPHA = 0.6

SPEAK_PREDICT_SECONDS = 1.5

STATIC_ALERT_INTERVAL = 3.0

STATIC_SPEED_THRESHOLD = 0.08

LOG_DIR = "logs"

ENABLE_LOG = True

VIETNAMESE_NAMES = {
    "Bike": "xe đạp",
    "Building": "tòa nhà",
    "Car": "ô tô",
    "Person": "người",
    "Stairs": "cầu thang",
    "Traffic sign": "biển báo giao thông",
    "Electrical Pole": "cột điện",
    "Road": "đường",
    "Motorcycle": "xe máy",
    "Dustbin": "thùng rác",
    "Dog": "chó",
    "Manhole": "nắp cống",
    "Tree": "cây",
    "Guard rail": "lan can",
    "Pedestrian crosswalk": "vạch sang đường",
    "Truck": "xe tải",
    "Bus": "xe buýt",
    "Bench": "ghế băng",
    "Traffic Cone": "cọc tiêu giao thông",
    "Fire hydrant": "trụ cứu hỏa",
    "Teraffic Barrel": "thùng chắn giao thông",
    "Plant Pot": "chậu cây",
    "Electrical Box": "tủ điện",
    "Chair": "ghế",
    "Bicycle Rack": "giá để xe đạp",
}

TTS_RATE = 165

TTS_RATE_DANGER = 200

TTS_VOLUME = 1.0

MAX_MESSAGE_AGE = 1.5


APP_VERSION = "2.0.0"

SERVER_URL = "http://127.0.0.1:5000"

DEVICE_KEY = "demo-device-key-0001"

ENABLE_SERVER = True

HEARTBEAT_INTERVAL = 10.0

ALERT_BATCH_INTERVAL = 2.0

SERVER_RETRY_INTERVAL = 5.0

SERVER_TIMEOUT = 3.0

ALERT_BUFFER_SIZE = 500

SOS_RETRY_INTERVAL = 3.0

SOS_DEBOUNCE_SECONDS = 2.0
