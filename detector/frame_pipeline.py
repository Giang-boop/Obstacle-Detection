# ======================================================================
#  FILE: detector/frame_pipeline.py
#  CHUC NANG: Pipeline xử lý 1 khung hình: YOLO → trích box → ByteTrack → đo khoảng cách → tracker → AlertManager.
# ======================================================================

from config import (
    MAX_DET,
    IMG_SIZE,
    TRACKER_CONFIG,
    IGNORED_CLASSES,
    TWO_WHEELER_CLASSES
)

from detection_utils import (
    calculate_distance,
    is_in_front_zone,
    DETECT_CONFIDENCE,
    normalize_class_name,
    passes_confidence,
    resolve_overlaps,
    remove_riders
)

from box_tracker import BoxTracker

from tracker import ObjectTracker

from alert_manager import AlertManager

def association_mode(use_tracking, use_distance_smoothing):

    if use_tracking:
        return "track_id"

    if use_distance_smoothing:
        return "iou"

    return "none"

def run_model(model, frame, device=None):

    return model(
        frame,
        conf=DETECT_CONFIDENCE,
        imgsz=IMG_SIZE,
        max_det=MAX_DET,
        device=device,
        verbose=False
    )

def extract_detections(results, class_names):

    raw_detections = []

    for result in results:

        if result.boxes is None:
            continue

        for box in result.boxes:

            class_id = int(box.cls[0])

            raw_detections.append({
                "class_id": class_id,
                "class_name": normalize_class_name(
                    str(class_names[class_id])
                ),
                "box": tuple(box.xyxy[0].tolist()),
                "confidence": float(box.conf[0]),
                "track_id": None,
            })

    return resolve_overlaps(raw_detections)

def measure_detections(raw_detections):

    detections = []

    for raw in raw_detections:

        class_name = raw["class_name"]

        confidence = raw["confidence"]

        if not passes_confidence(class_name, confidence):
            continue

        x1, y1, x2, y2 = map(int, raw["box"])

        distance, box_height, k = calculate_distance(
            class_name, x1, y1, x2, y2
        )

        detections.append({
            "track_id": raw["track_id"],
            "class_name": class_name,
            "box": (x1, y1, x2, y2),
            "confidence": confidence,
            "distance": distance,
            "box_height": box_height,
            "k": k,
        })

    return detections

class FrameResult:

    def __init__(self, objects, lost_objects, nearest, alert, target):

        self.objects = objects
        self.lost_objects = lost_objects
        self.nearest = nearest
        self.alert = alert
        self.target = target

class FramePipeline:

    def __init__(
        self,
        use_tracking=True,
        use_distance_smoothing=True,
        tracker_config=TRACKER_CONFIG
    ):

        self.use_tracking = use_tracking
        self.association = association_mode(use_tracking, use_distance_smoothing)

        self.box_tracker = (
            BoxTracker(tracker_config) if use_tracking else None
        )

        self.tracker = ObjectTracker(
            association=self.association,
            use_smoothing=use_distance_smoothing,
            use_hold_and_motion=use_tracking
        )

        self.alert_manager = AlertManager()

    def detect(self, model, frame, device=None):

        results = run_model(model, frame, device)

        raw_detections = extract_detections(results, model.names)

        if self.box_tracker is not None:

            raw_detections = self.box_tracker.update(
                raw_detections,
                frame.shape[:2]
            )

        return raw_detections

    def find_nearest(self, objects, frame_width):

        nearest = None

        for obj in objects:

            if obj.class_name in IGNORED_CLASSES:
                continue

            if not self.tracker.is_confirmed(obj):
                continue

            if not is_in_front_zone(obj.box[0], obj.box[2], frame_width):
                continue

            if nearest is None or obj.distance < nearest.distance:
                nearest = obj

        return nearest

    def display_id(self, obj):

        if obj is None or self.association == "none":
            return None

        return obj.object_id

    def analyze(self, raw_detections, now, frame_width):

        detections = remove_riders(
            measure_detections(raw_detections),
            [
                obj.box for obj in self.tracker.objects.values()
                if obj.class_name in TWO_WHEELER_CLASSES
            ]
        )

        objects, lost_objects = self.tracker.update(
            detections,
            now,
            frame_width
        )

        nearest = self.find_nearest(objects, frame_width)

        ranked = self.alert_manager.rank(
            objects,
            self.tracker.is_confirmed
        )

        alert = self.alert_manager.decide(ranked, now)

        return FrameResult(
            objects,
            lost_objects,
            nearest,
            alert,
            self.alert_manager.current_target
        )
