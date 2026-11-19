# ======================================================================
#  FILE: detector/detection_utils.py
#  CHUC NANG: Công thức khoảng cách d = K/h, EMA làm mượt, vùng trái/giữa/phải, lọc người ngồi trên xe, sinh câu cảnh báo tiếng Việt, vẽ box theo mức.
# ======================================================================

import unicodedata

import cv2

from config import (
    CENTER_ZONE,
    POSITION_NAMES,
    EMA_ALPHA,
    APPROACH_EMA_ALPHA,
    CONFIDENCE_THRESHOLD,
    CLASS_ALIASES,
    TWO_WHEELER_CLASSES,
    TWO_WHEELER_CONFIDENCE,
    CLASS_CONFIDENCE,
    OVERLAP_IOU,
    CROSS_CLASS_NMS_PAIRS,
    PERSON_IN_VEHICLE_RATIO,
    RIDER_OVERLAP
)

from runtime_settings import settings

DETECT_CONFIDENCE = min(
    CONFIDENCE_THRESHOLD,
    TWO_WHEELER_CONFIDENCE,
    *CLASS_CONFIDENCE.values()
)

def normalize_class_name(class_name):

    return CLASS_ALIASES.get(
        class_name,
        class_name
    )

def class_confidence_threshold(class_name):

    override = settings.class_confidence(class_name)

    if override is not None:
        return override

    if class_name in TWO_WHEELER_CLASSES:
        return TWO_WHEELER_CONFIDENCE

    return CONFIDENCE_THRESHOLD

def passes_confidence(class_name, confidence):

    return confidence >= class_confidence_threshold(class_name)

def box_iou(box_a, box_b):

    overlap_w = max(0, min(box_a[2], box_b[2]) - max(box_a[0], box_b[0]))
    overlap_h = max(0, min(box_a[3], box_b[3]) - max(box_a[1], box_b[1]))
    overlap_area = overlap_w * overlap_h

    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])

    return overlap_area / max(1e-6, area_a + area_b - overlap_area)

def contained_ratio(inner_box, outer_box):

    overlap_w = max(0, min(inner_box[2], outer_box[2]) - max(inner_box[0], outer_box[0]))
    overlap_h = max(0, min(inner_box[3], outer_box[3]) - max(inner_box[1], outer_box[1]))

    inner_area = (inner_box[2] - inner_box[0]) * (inner_box[3] - inner_box[1])

    return overlap_w * overlap_h / max(1e-6, inner_area)

def overlaps_vehicle(person_box, vehicle_box):

    return (
        box_iou(person_box, vehicle_box) >= OVERLAP_IOU
        or contained_ratio(person_box, vehicle_box) >= PERSON_IN_VEHICLE_RATIO
    )

def drop_people_on_vehicles(detections):

    vehicles = [
        d["box"] for d in detections
        if d["class_name"] in TWO_WHEELER_CLASSES
    ]

    if not vehicles:
        return list(detections)

    return [
        d for d in detections
        if not (
            d["class_name"] == "Person"
            and any(overlaps_vehicle(d["box"], v) for v in vehicles)
        )
    ]

def suppress_cross_class(detections, pairs=CROSS_CLASS_NMS_PAIRS, iou_threshold=OVERLAP_IOU):

    pair_sets = [frozenset(pair) for pair in pairs]

    kept = []

    for detection in sorted(detections, key=lambda d: -d["confidence"]):

        suppressed = any(
            frozenset((detection["class_name"], other["class_name"])) in pair_sets
            and box_iou(detection["box"], other["box"]) >= iou_threshold
            for other in kept
        )

        if not suppressed:
            kept.append(detection)

    return kept

def resolve_overlaps(detections):

    return suppress_cross_class(
        drop_people_on_vehicles(detections)
    )

def is_rider(person_box, vehicle_box):

    px1, py1, px2, py2 = person_box
    vx1, vy1, vx2, vy2 = vehicle_box

    overlap_w = max(0, min(px2, vx2) - max(px1, vx1))
    overlap_h = max(0, min(py2, vy2) - max(py1, vy1))
    overlap_area = overlap_w * overlap_h

    person_area = max(1, (px2 - px1) * (py2 - py1))
    vehicle_area = max(1, (vx2 - vx1) * (vy2 - vy1))

    center_x = (px1 + px2) / 2

    vehicle_middle_y = (vy1 + vy2) / 2

    if py1 >= vehicle_middle_y:
        return False

    sits_on_vehicle = (
        overlap_area / person_area >= RIDER_OVERLAP
        and vx1 <= center_x <= vx2
    )

    covers_vehicle = (
        overlap_area / vehicle_area >= 0.8
        and (vy2 - vy1) >= 0.5 * (py2 - py1)
    )

    return sits_on_vehicle or covers_vehicle

def remove_riders(detections, tracked_vehicle_boxes=()):

    vehicles = [
        d["box"] for d in detections
        if d["class_name"] in TWO_WHEELER_CLASSES
    ] + list(tracked_vehicle_boxes)

    if not vehicles:
        return detections

    return [
        d for d in detections
        if not (
            d["class_name"] == "Person"
            and any(is_rider(d["box"], v) for v in vehicles)
        )
    ]

def calculate_distance(
    class_name,
    x1,
    y1,
    x2,
    y2
):

    box_height = max(
        1,
        y2 - y1
    )

    k = settings.k_value(
        class_name
    )

    distance = k / box_height

    distance = max(
        0.05,
        min(distance, 100.0)
    )

    return distance, box_height, k

def smooth_distance(
    previous_distance,
    new_distance,
    alpha=EMA_ALPHA
):

    if previous_distance is None:
        return new_distance

    if new_distance < previous_distance:

        alpha = APPROACH_EMA_ALPHA

    return (
        alpha * new_distance
        + (1 - alpha) * previous_distance
    )

def get_zone_bounds(frame_width):

    zone_width = frame_width * CENTER_ZONE

    zone_left = (
        frame_width - zone_width
    ) / 2

    zone_right = (
        frame_width + zone_width
    ) / 2

    return zone_left, zone_right

def is_in_front_zone(
    x1,
    x2,
    frame_width
):

    center_x = (x1 + x2) / 2

    zone_left, zone_right = get_zone_bounds(
        frame_width
    )

    return (
        zone_left <= center_x <= zone_right
    )

def get_horizontal_position(
    center_x,
    frame_width
):

    zone_left, zone_right = get_zone_bounds(
        frame_width
    )

    if center_x < zone_left:
        return "LEFT"

    if center_x > zone_right:
        return "RIGHT"

    return "CENTER"

LEVEL_RANK = {
    None: -1,
    "SAFE": 0,
    "WARNING": 1,
    "DANGER": 2,
}

def get_danger_level(distance):

    if distance < settings.danger_distance:

        return "DANGER"

    elif distance < settings.warning_distance:

        return "WARNING"

    else:

        return "SAFE"

def max_level(level_a, level_b):

    if LEVEL_RANK[level_a] >= LEVEL_RANK[level_b]:
        return level_a

    return level_b

def format_distance(distance):

    return f"{distance:.1f}".replace(".", ",")

def format_spoken_distance(distance):

    if distance >= 2.0:
        value = round(distance * 2) / 2
    else:
        value = max(0.1, round(distance, 1))

    if value == int(value):
        return str(int(value))

    return f"{value:.1f}".replace(".", ",")

def get_short_alert_message(
    level,
    object_name,
    distance,
    position=None,
    approaching=False
):

    position_text = POSITION_NAMES.get(
        position,
        POSITION_NAMES["CENTER"]
    )

    distance_text = format_spoken_distance(distance)

    if level == "DANGER":

        parts = [object_name]

        if position not in (None, "CENTER"):
            parts.append(position_text)

        if approaching:
            parts.append("lao tới")

        return f"Gấp! {' '.join(parts)}, {distance_text} mét!"

    elif level == "WARNING":

        approaching_text = (
            " đang tới" if approaching else ""
        )

        return (
            f"{object_name} {position_text}"
            f"{approaching_text}, "
            f"{distance_text} mét."
        )

    return None

def get_alert_message(
    level,
    object_name,
    distance,
    position=None,
    approaching=False,
    short=None
):

    if short is None:
        short = settings.short_messages

    object_name = settings.vietnamese_name(
        object_name
    )

    object_name = object_name[:1].upper() + object_name[1:]

    if short:

        return get_short_alert_message(
            level,
            object_name,
            distance,
            position=position,
            approaching=approaching
        )

    position_text = POSITION_NAMES.get(
        position,
        POSITION_NAMES["CENTER"]
    )

    approaching_text = (
        " đang tới gần" if approaching else ""
    )

    distance_text = format_distance(distance)

    if level == "DANGER":

        return (
            f"Nguy hiểm! "
            f"{object_name} {position_text}"
            f"{approaching_text}, "
            f"cách {distance_text} mét."
        )

    elif level == "WARNING":

        return (
            f"Cẩn thận! "
            f"{object_name} {position_text}"
            f"{approaching_text}, "
            f"cách {distance_text} mét."
        )

    return None

def to_ascii(text):

    text = text.replace("đ", "d").replace("Đ", "D")

    normalized = unicodedata.normalize("NFD", text)

    return "".join(
        ch for ch in normalized
        if unicodedata.category(ch) != "Mn"
    )

def get_box_color(level):

    if level == "DANGER":

        return (0, 0, 255)

    elif level == "WARNING":

        return (0, 165, 255)

    elif level == "LOST":

        return (160, 160, 160)

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
    level,
    object_id=None,
    held=False
):

    box_color = get_box_color(level)

    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        box_color,
        1 if held else 2
    )

    vietnamese_name = to_ascii(
        settings.vietnamese_name(
            class_name
        )
    )

    id_text = (
        f"#{object_id} " if object_id is not None else ""
    )

    label = (
        f"{id_text}"
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

def draw_motion(
    frame,
    center,
    predicted_center,
    color
):

    start = (int(center[0]), int(center[1]))
    end = (int(predicted_center[0]), int(predicted_center[1]))

    if abs(start[0] - end[0]) + abs(start[1] - end[1]) < 4:
        return frame

    cv2.arrowedLine(
        frame,
        start,
        end,
        color,
        2,
        tipLength=0.3
    )

    return frame

def draw_detection_zone(
    frame
):

    frame_height, frame_width = frame.shape[:2]

    zone_left, zone_right = get_zone_bounds(
        frame_width
    )

    zone_left = int(zone_left)
    zone_right = int(zone_right)

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

    label_y = frame_height - 20

    for text, x in (
        ("TRAI", 10),
        ("GIUA", zone_left + 10),
        ("PHAI", zone_right + 10),
    ):

        cv2.putText(
            frame,
            text,
            (x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 0),
            2
        )

    return frame

