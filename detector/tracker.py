# ======================================================================
#  FILE: detector/tracker.py
#  CHUC NANG: TrackedObject + ObjectTracker: lịch sử 20 điểm, hồi quy tính tốc độ, dự đoán 1 giây tới, TTC cảnh báo sớm, giữ vật khi mất dấu.
# ======================================================================

from collections import deque

from config import (
    LOST_FRAMES,
    MIN_CONFIRM_FRAMES,
    TRACK_HISTORY,
    PREDICT_SECONDS,
    MOTION_WINDOW,
    MIN_MOTION_POINTS,
    TTC_WARNING,
    TTC_DANGER,
    MIN_APPROACH_SPEED,
    EARLY_WARNING_MAX_DISTANCE
)

from detection_utils import (
    smooth_distance,
    get_horizontal_position,
    get_danger_level,
    max_level,
    LEVEL_RANK
)

def box_iou(box_a, box_b):

    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_w = max(0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h

    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))

    return inter / (area_a + area_b - inter)

def linear_slope(times, values):

    n = len(times)
    mean_t = sum(times) / n
    mean_v = sum(values) / n

    numerator = sum(
        (t - mean_t) * (v - mean_v)
        for t, v in zip(times, values)
    )

    denominator = sum(
        (t - mean_t) ** 2 for t in times
    )

    if denominator <= 1e-9:
        return 0.0

    return numerator / denominator

class TrackedObject:

    def __init__(self, object_id, detection, now, frame_width):

        self.object_id = object_id
        self.class_votes = {}
        self.class_name = detection["class_name"]
        self.box = detection["box"]
        self.confidence = detection["confidence"]
        self.raw_distance = detection["distance"]
        self.distance = detection["distance"]
        self.box_height = detection["box_height"]
        self.k = detection["k"]

        self.hits = 0
        self.missed = 0
        self.first_seen = now
        self.last_seen = now

        self.history = deque(maxlen=TRACK_HISTORY)

        self.approach_speed = 0.0
        self.lateral_speed = 0.0
        self.vertical_speed = 0.0
        self.ttc = None
        self.predicted_center = self.center
        self.predicted_distance = self.distance
        self.predicted_position = None

        self.position = get_horizontal_position(
            self.center[0], frame_width
        )

        self.distance_level = "SAFE"
        self.level = "SAFE"
        self.state = "SAFE"
        self.previous_state = None
        self.early_warning = False

    @property
    def center(self):

        x1, y1, x2, y2 = self.box

        return ((x1 + x2) / 2, (y1 + y2) / 2)

    @property
    def held(self):

        return self.missed > 0

    def update(
        self,
        detection,
        now,
        frame_width,
        use_smoothing,
        use_motion
    ):

        votes = self.class_votes
        votes[detection["class_name"]] = (
            votes.get(detection["class_name"], 0.0)
            + detection["confidence"]
        )
        self.class_name = max(votes, key=votes.get)

        self.box = detection["box"]
        self.confidence = detection["confidence"]
        self.raw_distance = detection["distance"]
        self.box_height = detection["box_height"]
        self.k = detection["k"]

        if use_smoothing and self.hits > 0:
            self.distance = smooth_distance(
                self.distance,
                detection["distance"]
            )
        else:
            self.distance = detection["distance"]

        self.hits += 1
        self.missed = 0
        self.last_seen = now

        cx, cy = self.center
        self.history.append((now, cx, cy, self.distance, self.raw_distance))

        self.position = get_horizontal_position(cx, frame_width)

        if use_motion:
            self.estimate_motion(now, frame_width)

        self.update_level()

    def estimate_motion(self, now, frame_width):

        recent = [h for h in self.history if now - h[0] <= MOTION_WINDOW]

        if len(recent) < MIN_MOTION_POINTS or recent[-1][0] - recent[0][0] < 0.3:

            self.approach_speed = 0.0
            self.lateral_speed = 0.0
            self.vertical_speed = 0.0
            self.ttc = None
            self.predicted_center = self.center
            self.predicted_distance = self.distance
            self.predicted_position = self.position
            return

        times = [h[0] for h in recent]

        self.approach_speed = -linear_slope(times, [h[4] for h in recent])
        self.lateral_speed = linear_slope(times, [h[1] for h in recent])
        self.vertical_speed = linear_slope(times, [h[2] for h in recent])

        cx, cy = self.center

        self.predicted_center = (
            cx + self.lateral_speed * PREDICT_SECONDS,
            cy + self.vertical_speed * PREDICT_SECONDS,
        )

        self.predicted_distance = max(
            0.05,
            self.distance - self.approach_speed * PREDICT_SECONDS
        )

        self.predicted_position = get_horizontal_position(
            self.predicted_center[0], frame_width
        )

        if self.approach_speed >= MIN_APPROACH_SPEED:
            self.ttc = self.distance / self.approach_speed
        else:
            self.ttc = None

    def update_level(self):

        self.distance_level = get_danger_level(self.distance)

        early_level = "SAFE"

        heading_to_center = (
            self.position == "CENTER"
            or self.predicted_position == "CENTER"
        )

        if (
            self.ttc is not None
            and heading_to_center
            and self.distance <= EARLY_WARNING_MAX_DISTANCE
        ):

            if self.ttc < TTC_DANGER:
                early_level = "DANGER"
            elif self.ttc < TTC_WARNING:
                early_level = "WARNING"

        self.level = max_level(self.distance_level, early_level)

        self.early_warning = (
            LEVEL_RANK[early_level] > LEVEL_RANK[self.distance_level]
        )

        self.previous_state = self.state
        self.state = self.level

    def mark_missed(self):

        self.missed += 1

        if self.missed >= LOST_FRAMES:
            self.previous_state = self.state
            self.state = "LOST"

class ObjectTracker:

    def __init__(
        self,
        association="track_id",
        use_smoothing=True,
        use_hold_and_motion=True
    ):

        self.association = association
        self.use_smoothing = use_smoothing
        self.use_hold_and_motion = use_hold_and_motion

        self.objects = {}
        self.next_local_id = 1

    def is_confirmed(self, obj):

        if self.association == "none":
            return True

        return obj.hits >= MIN_CONFIRM_FRAMES

    def _new_object(self, object_id, detection, now, frame_width):

        if object_id is None:
            object_id = f"n{self.next_local_id}"
            self.next_local_id += 1

        obj = TrackedObject(object_id, detection, now, frame_width)

        obj.update(
            detection, now, frame_width,
            self.use_smoothing, self.use_hold_and_motion
        )

        self.objects[object_id] = obj

        return obj

    def _match_by_iou(self, detection, used_ids):

        best_id = None
        best_iou = 0.3

        for object_id, obj in self.objects.items():

            if object_id in used_ids:
                continue

            iou = box_iou(obj.box, detection["box"])

            if iou > best_iou:
                best_iou = iou
                best_id = object_id

        return best_id

    def update(self, detections, now, frame_width):

        if self.association == "none":

            self.objects = {}

            active = [
                self._new_object(None, d, now, frame_width)
                for d in detections
            ]

            return active, []

        seen_ids = set()

        for detection in detections:

            object_id = None

            if (
                self.association == "track_id"
                and detection.get("track_id") is not None
            ):
                object_id = detection["track_id"]
            else:
                object_id = self._match_by_iou(detection, seen_ids)

            if object_id in seen_ids:
                object_id = None

            if object_id is not None and object_id in self.objects:

                self.objects[object_id].update(
                    detection, now, frame_width,
                    self.use_smoothing, self.use_hold_and_motion
                )

            else:

                obj = self._new_object(
                    object_id, detection, now, frame_width
                )

                object_id = obj.object_id

            seen_ids.add(object_id)

        lost = []

        for object_id in list(self.objects):

            if object_id in seen_ids:
                continue

            obj = self.objects[object_id]

            if not self.use_hold_and_motion:
                del self.objects[object_id]
                continue

            obj.mark_missed()

            if obj.state == "LOST":
                lost.append(obj)
                del self.objects[object_id]

        active = list(self.objects.values())

        return active, lost

