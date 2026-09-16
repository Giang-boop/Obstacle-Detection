# ============================================================
# CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# MODEL
# ------------------------------------------------------------

MODEL_PATH = "best.pt"


# ------------------------------------------------------------
# INPUT
# ------------------------------------------------------------

# 1 = Camera real-time
# 2 = Video file

INPUT_MODE = 2


CAMERA_ID = 0

VIDEO_PATH = "test_video.mp4"


# ------------------------------------------------------------
# YOLO
# ------------------------------------------------------------

CONFIDENCE_THRESHOLD = 0.50


# ------------------------------------------------------------
# DISTANCE
# ------------------------------------------------------------

# Công thức:
#
#       K
# d = -----
#       h
#
# d: khoảng cách (m)
# K: hằng số hiệu chỉnh
# h: chiều cao bounding box (pixel)

K_VALUES = {
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


# ------------------------------------------------------------
# WARNING
# ------------------------------------------------------------

WARNING_DISTANCE = 2.0

DANGER_DISTANCE = 1.0

ALERT_COOLDOWN = 2.0


# ------------------------------------------------------------
# DETECTION ZONE
# ------------------------------------------------------------

# 60% vùng giữa màn hình

CENTER_ZONE = 0.60


# ------------------------------------------------------------
# VIETNAMESE NAMES
# ------------------------------------------------------------

VIETNAMESE_NAMES = {
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