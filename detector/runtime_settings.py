# ======================================================================
#  FILE: detector/runtime_settings.py
#  CHUC NANG: Cấu hình chạy thời gian thực: áp cấu hình máy chủ đè lên config.py (ngưỡng, TTS, tắt lớp vật, hệ số K).
# ======================================================================

from contextlib import contextmanager

import config

def to_positive_float(value):

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if number <= 0:
        return None

    return number

class RuntimeSettings:

    def __init__(self):

        self.reset()

    def reset(self):

        self.warning_distance = float(config.WARNING_DISTANCE)
        self.danger_distance = float(config.DANGER_DISTANCE)
        self.tts_rate = float(config.TTS_RATE)
        self.tts_rate_danger = float(config.TTS_RATE_DANGER)
        self.tts_volume = float(config.TTS_VOLUME)
        self.muted = False
        self.short_messages = bool(config.SHORT_ALERT_MESSAGES)
        self.disabled_classes = frozenset()
        self.names_vi = dict(config.VIETNAMESE_NAMES)
        self.k_values = dict(config.K_VALUES)
        self.risk_weights = dict(config.CLASS_RISK_WEIGHT)
        self.confidences = dict(config.CLASS_CONFIDENCE)
        self.updated_at = None
        self.source = "config.py"

    def effective_volume(self):

        return 0.0 if self.muted else self.tts_volume

    def vietnamese_name(self, class_name):

        return self.names_vi.get(class_name, class_name)

    def k_value(self, class_name):

        return self.k_values.get(class_name, config.DEFAULT_K)

    def risk_weight(self, class_name):

        return self.risk_weights.get(class_name, config.DEFAULT_RISK_WEIGHT)

    def class_confidence(self, class_name):

        return self.confidences.get(class_name)

    def is_disabled(self, class_name):

        return class_name in self.disabled_classes

    def apply_remote(self, data):

        if not isinstance(data, dict):
            return False

        warning = to_positive_float(data.get("warning_distance"))
        danger = to_positive_float(data.get("danger_distance"))

        if warning is None:
            warning = self.warning_distance

        if danger is None:
            danger = self.danger_distance

        if danger < warning:
            self.warning_distance = warning
            self.danger_distance = danger

        rate = to_positive_float(data.get("tts_rate"))

        if rate is not None:
            self.tts_rate = rate

        rate_danger = to_positive_float(data.get("tts_rate_danger"))

        if rate_danger is not None:
            self.tts_rate_danger = rate_danger

        volume = data.get("tts_volume")

        if isinstance(volume, (int, float)) and not isinstance(volume, bool):
            self.tts_volume = max(0.0, min(1.0, float(volume)))

        if isinstance(data.get("short_messages"), bool):
            self.short_messages = data["short_messages"]

        disabled = set()

        if isinstance(data.get("disabled_classes"), list):
            disabled.update(str(code) for code in data["disabled_classes"])

        classes = data.get("classes")

        if isinstance(classes, dict):

            names_vi = dict(self.names_vi)
            k_values = dict(self.k_values)
            risk_weights = dict(self.risk_weights)
            confidences = dict(self.confidences)

            for code, info in classes.items():

                if not isinstance(info, dict):
                    continue

                name_vi = info.get("name_vi")

                if isinstance(name_vi, str) and name_vi.strip():
                    names_vi[code] = name_vi.strip()

                k_value = to_positive_float(info.get("k_value"))

                if k_value is not None:
                    k_values[code] = k_value

                risk_weight = to_positive_float(info.get("risk_weight"))

                if risk_weight is not None:
                    risk_weights[code] = risk_weight

                confidence = to_positive_float(info.get("confidence"))

                if confidence is not None and confidence < 1:
                    confidences[code] = confidence

                if info.get("enabled") is False:
                    disabled.add(code)

            self.names_vi = names_vi
            self.k_values = k_values
            self.risk_weights = risk_weights
            self.confidences = confidences

        if "disabled_classes" in data or isinstance(classes, dict):
            self.disabled_classes = frozenset(disabled)

        self.updated_at = data.get("updated_at", self.updated_at)
        self.source = "server"

        return True

    @contextmanager
    def applied(self, other):

        saved = dict(vars(self))

        self.__dict__.update(vars(other))

        try:
            yield self
        finally:
            self.__dict__.clear()
            self.__dict__.update(saved)

    def describe(self):

        disabled = ", ".join(sorted(self.disabled_classes)) or "không"

        return (
            f"cảnh báo < {self.warning_distance:g} m, "
            f"nguy hiểm < {self.danger_distance:g} m, "
            f"tốc độ đọc {self.tts_rate:g}/{self.tts_rate_danger:g}, "
            f"âm lượng {self.tts_volume:g}, "
            f"câu ngắn: {'có' if self.short_messages else 'không'}, "
            f"lớp bị tắt: {disabled}"
        )

settings = RuntimeSettings()
