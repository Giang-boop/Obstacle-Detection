# === MO TA FILE ===
# server/app/web_detection.py
# CHUC NANG: May chu tu chay YOLO cho /thiet-bi: DetectionEngine, WebSessionStore theo tung phien
# ===================

import os
import sys
import threading
import time

from server.config import SERVER_DIR

DETECTOR_DIR = os.path.join(os.path.dirname(SERVER_DIR), "detector")
DEFAULT_MODEL_PATH = os.path.join(DETECTOR_DIR, "best.pt")
WEB_APP_VERSION = "2.0.0-web"


def ensure_detector_path():
    if DETECTOR_DIR not in sys.path:
        sys.path.insert(0, DETECTOR_DIR)


def detector_config():
    ensure_detector_path()
    import config as detector_config_module

    return detector_config_module


class ModelUnavailableError(Exception):
    pass


class InvalidFrameError(Exception):
    pass


def cuda_available():
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def release_cuda_memory():
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def candidate_devices(preference):
    preference = (preference or "auto").strip().lower()
    if preference == "cpu":
        return ["cpu"]
    if preference == "auto":
        return ["0", "cpu"] if cuda_available() else ["cpu"]
    return [preference, "cpu"]


def is_cuda_failure(error):
    text = f"{type(error).__name__} {error}".lower()
    return "cuda" in text or "out of memory" in text or "cublas" in text or "cudnn" in text


class DetectionEngine:
    def __init__(self, model_path=DEFAULT_MODEL_PATH, device_preference="auto"):
        self.model_path = model_path
        self.device_preference = device_preference
        self.model = None
        self.device = None
        self.load_error = None
        self.load_lock = threading.Lock()
        self.inference_lock = threading.Lock()

    @property
    def device_label(self):
        if self.device is None:
            return None
        return "cpu" if self.device == "cpu" else f"cuda:{self.device}"

    def warm_up(self, device):
        import numpy as np

        self.model(np.zeros((640, 640, 3), dtype=np.uint8), imgsz=detector_config().IMG_SIZE,
                   device=device, verbose=False)

    def load(self):
        if self.model is not None:
            return self.model
        with self.load_lock:
            if self.model is not None:
                return self.model
            ensure_detector_path()
            try:
                from ultralytics import YOLO

                self.model = YOLO(self.model_path)
            except Exception as error:
                self.load_error = str(error)
                self.model = None
                raise ModelUnavailableError(f"Không nạp được mô hình: {error}") from error
            last_error = None
            for device in candidate_devices(self.device_preference):
                try:
                    self.warm_up(device)
                    self.device = device
                    self.load_error = None
                    return self.model
                except Exception as error:
                    last_error = error
                    release_cuda_memory()
            self.load_error = str(last_error)
            self.model = None
            raise ModelUnavailableError(f"Không chạy được mô hình: {last_error}")

    def fall_back_to_cpu(self):
        release_cuda_memory()
        self.device = "cpu"

    def process(self, state, frame):
        from runtime_settings import settings as shared_settings

        model = self.load()
        with self.inference_lock:
            with shared_settings.applied(state.settings):
                infer_start = time.perf_counter()
                try:
                    raw_detections = state.pipeline.detect(model, frame, self.device)
                except Exception as error:
                    if self.device == "cpu" or not is_cuda_failure(error):
                        raise
                    self.fall_back_to_cpu()
                    raw_detections = state.pipeline.detect(model, frame, self.device)
                infer_ms = (time.perf_counter() - infer_start) * 1000
                now = time.perf_counter()
                frame_result = state.pipeline.analyze(raw_detections, now, frame.shape[1])
                return frame_result, infer_ms, now


def decode_frame(data):
    import cv2
    import numpy as np

    if not data:
        raise InvalidFrameError("Không có dữ liệu ảnh")
    buffer = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if frame is None or frame.size == 0:
        raise InvalidFrameError("Ảnh không đọc được (cần JPEG hoặc PNG)")
    return frame


def scale_to_reference(frame):
    import cv2

    config_module = detector_config()
    reference_long_side = max(config_module.CAMERA_WIDTH, config_module.CAMERA_HEIGHT)
    height, width = frame.shape[:2]
    scale = reference_long_side / max(height, width)
    if abs(scale - 1.0) < 0.01:
        return frame
    new_size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
    interpolation = cv2.INTER_LINEAR if scale > 1 else cv2.INTER_AREA
    return cv2.resize(frame, new_size, interpolation=interpolation)


class WebSessionState:
    def __init__(self, session_id, device_id, config_payload, config_updated_at):
        ensure_detector_path()
        from frame_pipeline import FramePipeline
        from runtime_settings import RuntimeSettings

        config_module = detector_config()
        self.session_id = session_id
        self.device_id = device_id
        self.pipeline = FramePipeline(
            use_tracking=config_module.USE_TRACKING,
            use_distance_smoothing=config_module.USE_DISTANCE_SMOOTHING,
        )
        self.settings = RuntimeSettings()
        self.config_updated_at = None
        self.apply_config(config_payload, config_updated_at)
        self.lock = threading.Lock()
        self.created_at = time.monotonic()
        self.last_used = self.created_at
        self.frames = 0
        self.alert_count = 0
        self.process_ms_total = 0.0
        self.infer_ms_total = 0.0
        self.first_frame_at = None
        self.last_frame_at = None

    def apply_config(self, config_payload, config_updated_at):
        from runtime_settings import RuntimeSettings

        fresh_settings = RuntimeSettings()
        if config_payload:
            fresh_settings.apply_remote(config_payload)
        self.settings = fresh_settings
        self.config_updated_at = config_updated_at

    def record_frame(self, process_ms, infer_ms, alert_raised):
        now = time.monotonic()
        if self.first_frame_at is None:
            self.first_frame_at = now
        self.last_frame_at = now
        self.last_used = now
        self.frames += 1
        self.process_ms_total += process_ms
        self.infer_ms_total += infer_ms
        if alert_raised:
            self.alert_count += 1

    def stats(self):
        avg_fps = 0.0
        if self.frames > 1 and self.last_frame_at > self.first_frame_at:
            avg_fps = (self.frames - 1) / (self.last_frame_at - self.first_frame_at)
        avg_latency = self.process_ms_total / self.frames if self.frames else 0.0
        return {
            "frames": self.frames,
            "avg_fps": round(avg_fps, 2),
            "avg_latency_ms": round(avg_latency, 1),
            "alert_count": self.alert_count,
        }


class WebSessionStore:
    def __init__(self, idle_seconds=120.0):
        self.idle_seconds = idle_seconds
        self.states = {}
        self.lock = threading.Lock()

    def __len__(self):
        with self.lock:
            return len(self.states)

    def __contains__(self, session_id):
        with self.lock:
            return session_id in self.states

    def get(self, session_id):
        with self.lock:
            return self.states.get(session_id)

    def get_or_create(self, session_id, device_id, config_loader, config_updated_at):
        with self.lock:
            state = self.states.get(session_id)
        if state is not None and state.device_id == device_id:
            if state.config_updated_at != config_updated_at:
                state.apply_config(config_loader(), config_updated_at)
            state.last_used = time.monotonic()
            return state
        state = WebSessionState(session_id, device_id, config_loader(), config_updated_at)
        with self.lock:
            existing = self.states.get(session_id)
            if existing is not None and existing.device_id == device_id:
                return existing
            self.states[session_id] = state
        return state

    def pop(self, session_id):
        with self.lock:
            return self.states.pop(session_id, None)

    def pop_expired(self, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            expired_ids = [session_id for session_id, state in self.states.items()
                           if now - state.last_used > self.idle_seconds]
            return [self.states.pop(session_id) for session_id in expired_ids]


_engine = None
_engine_lock = threading.Lock()


def get_engine(app):
    global _engine
    model_path = app.config.get("WEB_DETECT_MODEL_PATH") or DEFAULT_MODEL_PATH
    preference = app.config.get("WEB_DETECT_DEVICE", "auto")
    with _engine_lock:
        if _engine is None or _engine.model_path != model_path or _engine.device_preference != preference:
            _engine = DetectionEngine(model_path, preference)
        return _engine


def get_session_store(app):
    store = app.extensions.get("web_detection_sessions")
    if store is None:
        store = WebSessionStore(app.config.get("WEB_SESSION_IDLE_SECONDS", 120))
        app.extensions["web_detection_sessions"] = store
    return store


def start_background_warmup(app):
    engine = get_engine(app)

    def warm():
        try:
            engine.load()
            print(f"[NHẬN DIỆN WEB] Đã nạp mô hình {os.path.basename(engine.model_path)} trên {engine.device_label}.")
        except ModelUnavailableError as error:
            print(f"[NHẬN DIỆN WEB] {error}")

    thread = threading.Thread(target=warm, name="web-detect-warmup", daemon=True)
    thread.start()
    return thread


def client_policy():
    config_module = detector_config()
    return {
        "center_zone": config_module.CENTER_ZONE,
        "max_message_age_s": config_module.MAX_MESSAGE_AGE,
        "interrupt_min_speak_s": config_module.INTERRUPT_MIN_SPEAK_SECONDS,
        "interrupt_closer_step_m": config_module.INTERRUPT_CLOSER_STEP,
        "sos_debounce_s": config_module.SOS_DEBOUNCE_SECONDS,
        "sos_retry_s": config_module.SOS_RETRY_INTERVAL,
        "heartbeat_s": config_module.HEARTBEAT_INTERVAL,
        "base_rate_wpm": config_module.TTS_RATE,
    }


def rounded(value, digits=2):
    if value is None:
        return None
    return round(float(value), digits)


def serialize_object(obj, state, frame_width, frame_height, target):
    x1, y1, x2, y2 = obj.box
    return {
        "id": state.pipeline.display_id(obj),
        "class_code": obj.class_name,
        "class_name_vi": state.settings.vietnamese_name(obj.class_name),
        "confidence": rounded(obj.confidence, 3),
        "distance_m": rounded(obj.distance),
        "level": obj.level,
        "position": obj.position,
        "ttc_s": rounded(obj.ttc),
        "early_warning": bool(obj.early_warning),
        "held": bool(obj.held),
        "confirmed": bool(state.pipeline.tracker.is_confirmed(obj)),
        "target": obj is target,
        "box": [
            rounded(max(0.0, x1 / frame_width), 4),
            rounded(max(0.0, y1 / frame_height), 4),
            rounded(min(1.0, x2 / frame_width), 4),
            rounded(min(1.0, y2 / frame_height), 4),
        ],
    }


def serialize_alert(alert, state):
    target = alert["target"]
    priority = int(alert["priority"])
    settings = state.settings
    return {
        "alert_id": alert["alert_id"],
        "message": alert["message"],
        "level": target.level,
        "priority": priority,
        "interrupt": target.level == "DANGER",
        "reason": alert.get("reason"),
        "class_code": target.class_name,
        "class_name_vi": settings.vietnamese_name(target.class_name),
        "position": target.position,
        "distance_m": rounded(alert.get("distance")),
        "rate_wpm": settings.tts_rate_danger if priority >= 2 else settings.tts_rate,
        "volume": settings.effective_volume(),
    }


def build_detection_response(state, frame_result, frame, infer_ms, process_ms):
    frame_height, frame_width = frame.shape[:2]
    target = frame_result.target
    objects = [serialize_object(obj, state, frame_width, frame_height, target) for obj in frame_result.objects]
    nearest = None
    if frame_result.nearest is not None:
        nearest = serialize_object(frame_result.nearest, state, frame_width, frame_height, target)
    return {
        "session_id": state.session_id,
        "frame_index": state.frames,
        "frame": {"width": frame_width, "height": frame_height},
        "objects": objects,
        "nearest": nearest,
        "alert": serialize_alert(frame_result.alert, state) if frame_result.alert is not None else None,
        "timing": {"infer_ms": round(infer_ms, 1), "process_ms": round(process_ms, 1)},
        "config_updated_at": state.config_updated_at,
    }


def build_alert_record(alert, state):
    from server_client import build_alert_item

    return build_alert_item(alert, settings=state.settings)
