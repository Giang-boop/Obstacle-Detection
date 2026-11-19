# ======================================================================
#  FILE: detector/alert_manager.py
#  CHUC NANG: Xếp hạng độ nguy hiểm (risk_score), quyết định đọc: tăng mức / vật mới nguy hiểm hơn / gần hơn / nhắc lại.
# ======================================================================

from config import (
    IGNORED_CLASSES,
    POSITION_RISK_WEIGHT,
    WARNING_INTERVAL,
    DANGER_INTERVAL,
    MIN_ALERT_GAP,
    CLOSER_ALERT_STEP,
    MIN_APPROACH_SPEED,
    SPEAK_PREDICT_SECONDS,
    STATIC_ALERT_INTERVAL,
    STATIC_SPEED_THRESHOLD
)

from detection_utils import (
    get_alert_message,
    LEVEL_RANK
)

from runtime_settings import settings

def effective_distance(obj):

    distance = min(
        obj.distance,
        obj.predicted_distance
    )

    position_weight = POSITION_RISK_WEIGHT.get(
        obj.position,
        1.0
    )

    return distance / position_weight

def risk_score(obj):

    class_weight = settings.risk_weight(
        obj.class_name
    )

    return (
        -round(effective_distance(obj), 1),
        class_weight
    )

def is_alert_candidate(obj, is_confirmed):

    if obj.class_name in IGNORED_CLASSES:
        return False

    if settings.is_disabled(obj.class_name):
        return False

    if obj.held:
        return False

    if not is_confirmed(obj):
        return False

    if LEVEL_RANK[obj.level] < LEVEL_RANK["WARNING"]:
        return False

    if obj.position != "CENTER":

        if obj.level != "DANGER" and not obj.early_warning:
            return False

    return True

class AlertManager:

    def __init__(self):

        self.last_alert_time = float("-inf")
        self.last_alert_level = None
        self.last_alert_object = None
        self.last_alert_distance = None
        self.alert_counter = 0
        self.current_target = None

    def rank(self, objects, is_confirmed):

        candidates = [
            obj for obj in objects
            if is_alert_candidate(obj, is_confirmed)
        ]

        candidates.sort(key=risk_score, reverse=True)

        return candidates

    def decide(self, ranked, now):

        if not ranked:

            self.current_target = None

            return None

        target = ranked[0]

        self.current_target = target

        elapsed = now - self.last_alert_time

        same_object = (
            target.object_id == self.last_alert_object
        )

        if (
            target.early_warning
            or target.approach_speed >= STATIC_SPEED_THRESHOLD
        ):

            interval = (
                DANGER_INTERVAL
                if target.level == "DANGER"
                else WARNING_INTERVAL
            )

        else:

            interval = STATIC_ALERT_INTERVAL

        reason = None

        if (
            same_object
            and LEVEL_RANK[target.level]
            > LEVEL_RANK[self.last_alert_level]
        ):

            reason = "tang_muc"

        elif (
            not same_object
            and LEVEL_RANK[target.level]
            > LEVEL_RANK[self.last_alert_level]
            and elapsed >= MIN_ALERT_GAP
        ):

            reason = "vat_moi_nguy_hiem_hon"

        elif (
            same_object
            and self.last_alert_distance is not None
            and target.distance
            <= self.last_alert_distance - CLOSER_ALERT_STEP
            and elapsed >= MIN_ALERT_GAP
        ):

            reason = "gan_hon"

        elif elapsed >= interval:

            reason = (
                "nhac_lai" if same_object else "chuyen_vat"
            )

        if reason is None:
            return None

        spoken_distance = target.distance

        if target.approach_speed >= MIN_APPROACH_SPEED:

            spoken_distance = max(
                0.2,
                target.distance
                - target.approach_speed * SPEAK_PREDICT_SECONDS
            )

        message = get_alert_message(
            target.level,
            target.class_name,
            spoken_distance,
            position=target.position,
            approaching=target.early_warning
        )

        if message is None:
            return None

        self.alert_counter += 1
        self.last_alert_time = now
        self.last_alert_level = target.level
        self.last_alert_object = target.object_id
        self.last_alert_distance = target.distance

        return {
            "alert_id": self.alert_counter,
            "message": message,
            "priority": LEVEL_RANK[target.level],
            "distance": spoken_distance,
            "target": target,
            "reason": reason,
        }

