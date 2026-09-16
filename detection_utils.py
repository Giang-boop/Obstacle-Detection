import cv2

from config import (
    K_VALUES,
    DEFAULT_K,
    WARNING_DISTANCE,
    DANGER_DISTANCE,
    CENTER_ZONE,
    VIETNAMESE_NAMES
)


# ============================================================
# DISTANCE
# ============================================================

def calculate_distance(
    class_name,
    x1,
    y1,
    x2,
    y2
):
    """
    Tính khoảng cách:

        d = K / h

    h = chiều cao bounding box.
    """

    box_height = max(
        1,
        y2 - y1
    )

    k = K_VALUES.get(
        class_name,
        DEFAULT_K
    )

    distance = k / box_height

    # Giới hạn khoảng cách
    distance = max(
        0.05,
        min(distance, 100.0)
    )

    return distance, box_height, k


# ============================================================
# FRONT ZONE
# ============================================================

def is_in_front_zone(
    x1,
    x2,
    frame_width
):
    """
    Kiểm tra object có nằm trong
    vùng trung tâm phía trước hay không.
    """

    center_x = (x1 + x2) / 2

    zone_width = frame_width * CENTER_ZONE

    zone_left = (
        frame_width - zone_width
    ) / 2

    zone_right = (
        frame_width + zone_width
    ) / 2

    return (
        zone_left <= center_x <= zone_right
    )


# ============================================================
# DANGER LEVEL
# ============================================================

def get_danger_level(distance):

    if distance < DANGER_DISTANCE:

        return "DANGER"

    elif distance < WARNING_DISTANCE:

        return "WARNING"

    else:

        return "SAFE"


# ============================================================
# ALERT MESSAGE
# ============================================================

def get_alert_message(
    level,
    object_name,
    distance
):
    """
    Tạo câu cảnh báo tiếng Việt.
    """

    object_name = VIETNAMESE_NAMES.get(
        object_name,
        object_name
    )

    distance_text = f"{distance:.1f}"

    if level == "DANGER":

        return (
            f"Nguy hiểm! "
            f"{object_name} "
            f"ở rất gần, "
            f"khoảng {distance_text} mét."
        )

    elif level == "WARNING":

        return (
            f"Cẩn thận! "
            f"Phía trước có {object_name}, "
            f"cách khoảng "
            f"{distance_text} mét."
        )

    return None


# ============================================================
# DRAW DETECTION
# ============================================================

def get_box_color(level):

    if level == "DANGER":

        return (0, 0, 255)

    elif level == "WARNING":

        return (0, 165, 255)

    else:

        return (0, 255, 0)


def draw_detection(
    frame,
    x1,
    y1,
    x2,
    y2,
    class_name,
    confidence,
    distance,
    level
):
    """
    Vẽ bounding box và thông tin
    lên frame.
    """

    box_color = get_box_color(level)

    # Bounding box
    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        box_color,
        2
    )

    vietnamese_name = VIETNAMESE_NAMES.get(
        class_name,
        class_name
    )

    label = (
        f"{vietnamese_name} "
        f"{confidence:.2f} | "
        f"{distance:.1f} m"
    )

    cv2.putText(
        frame,
        label,
        (
            x1,
            max(y1 - 10, 25)
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        box_color,
        2
    )

    return frame


# ============================================================
# DRAW FRONT ZONE
# ============================================================

def draw_detection_zone(
    frame
):
    """
    Vẽ vùng detection ở giữa camera.
    """

    frame_height, frame_width = frame.shape[:2]

    zone_width = int(
        frame_width * CENTER_ZONE
    )

    zone_left = int(
        (frame_width - zone_width) / 2
    )

    zone_right = int(
        (frame_width + zone_width) / 2
    )

    cv2.line(
        frame,
        (zone_left, 0),
        (zone_left, frame_height),
        (255, 255, 0),
        1
    )

    cv2.line(
        frame,
        (zone_right, 0),
        (zone_right, frame_height),
        (255, 255, 0),
        1
    )

    cv2.putText(
        frame,
        "DETECTION ZONE",
        (
            zone_left + 10,
            30
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 0),
        2
    )

    return frame