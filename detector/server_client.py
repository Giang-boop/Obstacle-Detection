# ======================================================================
#  FILE: detector/server_client.py
#  CHUC NANG: Thread đồng bộ máy chủ: hello/heartbeat, mở–đóng phiên, gửi lô cảnh báo (buffer 500), retry SOS, nhận cấu hình từ xa.
# ======================================================================

import collections
import datetime
import threading
import time

import requests

import config

from runtime_settings import settings as shared_settings

MAX_ALERTS_PER_REQUEST = 100

def now_iso():

    return datetime.datetime.now().isoformat(timespec="seconds")

def build_alert_item(alert, settings=shared_settings, created_at=None):

    target = alert["target"]

    ttc = getattr(target, "ttc", None)

    distance = alert.get("distance")

    if distance is None:
        distance = target.distance

    return {
        "class_code": target.class_name,
        "class_name_vi": settings.vietnamese_name(target.class_name),
        "level": target.level,
        "distance_m": round(float(distance), 2),
        "position": target.position,
        "ttc_s": None if ttc is None else round(float(ttc), 2),
        "message": alert["message"],
        "created_at": created_at or now_iso(),
    }

def session_stats_from_summary(summary, fallback_alert_count=0):

    summary = summary or {}

    alert_count = summary.get("so_canh_bao_tao_ra")

    if alert_count is None:
        alert_count = fallback_alert_count

    return {
        "frames": int(summary.get("so_frame_xu_ly") or 0),
        "avg_fps": float(summary.get("fps_tb") or 0.0),
        "avg_latency_ms": float(summary.get("do_tre_frame_ms_tb") or 0.0),
        "alert_count": int(alert_count),
    }

class ServerError(Exception):

    def __init__(self, message, retryable=True, unauthorized=False):

        super().__init__(message)

        self.retryable = retryable
        self.unauthorized = unauthorized

class ServerClient:

    def __init__(
        self,
        server_url=config.SERVER_URL,
        device_key=config.DEVICE_KEY,
        model_name="",
        app_version=config.APP_VERSION,
        settings=shared_settings,
        heartbeat_interval=config.HEARTBEAT_INTERVAL,
        batch_interval=config.ALERT_BATCH_INTERVAL,
        retry_interval=config.SERVER_RETRY_INTERVAL,
        sos_retry_interval=config.SOS_RETRY_INTERVAL,
        timeout=config.SERVER_TIMEOUT,
        buffer_size=config.ALERT_BUFFER_SIZE,
        on_sos_result=None,
        log=print
    ):

        self.base_url = server_url.rstrip("/")
        self.model_name = model_name
        self.app_version = app_version
        self.settings = settings
        self.heartbeat_interval = heartbeat_interval
        self.batch_interval = batch_interval
        self.retry_interval = retry_interval
        self.sos_retry_interval = sos_retry_interval
        self.timeout = timeout
        self.buffer_size = buffer_size
        self.on_sos_result = on_sos_result
        self.log = log

        self.http = requests.Session()
        self.http.headers.update({"X-Device-Key": device_key})

        self.lock = threading.Lock()
        self.alert_buffer = collections.deque()
        self.sos_queue = collections.deque()
        self.wake_event = threading.Event()
        self.stop_event = threading.Event()
        self.thread = None

        self.connected = False
        self.connection_reported = False
        self.buffer_full_reported = False
        self.device = None
        self.blind_person = None
        self.session_id = None
        self.session_closed = False
        self.session_unavailable = False
        self.reported_rejections = set()
        self.started_at = now_iso()
        self.config_updated_at = None

        self.reported_alert_count = 0
        self.sent_alert_count = 0
        self.dropped_alert_count = 0
        self.sent_sos_count = 0
        self.final_stats = None

        self.next_connect = 0.0
        self.next_heartbeat = 0.0
        self.next_flush = 0.0
        self.next_sos = 0.0

    def start(self):

        if self.thread is not None:
            return

        self.thread = threading.Thread(
            target=self.run,
            name="server-client",
            daemon=True
        )

        self.thread.start()

    def stop(self, stats=None, timeout=15.0):

        self.final_stats = stats

        self.stop_event.set()
        self.wake_event.set()

        if self.thread is not None:
            self.thread.join(timeout)

    def report_alert(self, item):

        with self.lock:

            if len(self.alert_buffer) >= self.buffer_size:

                self.alert_buffer.popleft()
                self.dropped_alert_count += 1

                if not self.buffer_full_reported:

                    self.buffer_full_reported = True

                    self.log(
                        f"[MÁY CHỦ] Bộ đệm đầy {self.buffer_size} cảnh báo, "
                        "bỏ bớt cảnh báo cũ nhất."
                    )

            self.alert_buffer.append(item)
            self.reported_alert_count += 1

    def send_sos(self):

        with self.lock:

            self.sos_queue.append({
                "created_at": now_iso(),
                "failed_once": False,
            })

        self.next_sos = 0.0
        self.wake_event.set()

    def pending_alert_count(self):

        with self.lock:
            return len(self.alert_buffer)

    def request(self, method, path, payload=None):

        try:

            response = self.http.request(
                method,
                self.base_url + path,
                json=payload,
                timeout=self.timeout
            )

        except requests.RequestException as error:

            raise ServerError(type(error).__name__)

        if response.status_code == 401:

            raise ServerError("HTTP 401", unauthorized=True)

        if response.status_code >= 500:

            raise ServerError(f"HTTP {response.status_code}")

        if response.status_code >= 400:

            raise ServerError(
                f"HTTP {response.status_code}",
                retryable=False
            )

        try:
            data = response.json()
        except ValueError:
            data = {}

        return data if isinstance(data, dict) else {}

    def mark_disconnected(self, error):

        was_connected = self.connected

        self.connected = False
        self.next_connect = time.monotonic() + self.retry_interval

        if was_connected or not self.connection_reported:

            self.connection_reported = True

            if error.unauthorized:

                self.log(
                    "[MÁY CHỦ] Máy chủ từ chối mã thiết bị (401). "
                    "Kiểm tra DEVICE_KEY / --device-key. Ứng dụng vẫn chạy offline."
                )

            elif was_connected:

                self.log(
                    f"[MÁY CHỦ] Mất kết nối máy chủ ({error}). "
                    "Ứng dụng vẫn chạy, cảnh báo được đệm và gửi lại sau."
                )

            else:

                self.log(
                    f"[MÁY CHỦ] Chưa kết nối được {self.base_url} ({error}). "
                    "Ứng dụng vẫn chạy, sẽ tự thử lại."
                )

    def apply_config(self, data):

        if not self.settings.apply_remote(data):
            return

        updated_at = data.get("updated_at")

        if updated_at is not None and updated_at == self.config_updated_at:
            return

        self.config_updated_at = updated_at

        self.log(
            "[MÁY CHỦ] Áp dụng cấu hình từ máy chủ: "
            + self.settings.describe()
        )

    def fetch_config(self):

        data = self.request("GET", "/api/device/config")

        self.apply_config(data)

    def connect(self):

        data = self.request(
            "POST",
            "/api/device/hello",
            {
                "app_version": self.app_version,
                "model_name": self.model_name,
            }
        )

        self.device = data.get("device") or {}
        self.blind_person = data.get("blind_person")

        remote_config = data.get("config")

        if isinstance(remote_config, dict) and "classes" in remote_config:
            self.apply_config(remote_config)
        else:
            self.fetch_config()

        self.connected = True
        self.connection_reported = True
        self.buffer_full_reported = False

        now = time.monotonic()

        self.next_heartbeat = now + self.heartbeat_interval
        self.next_flush = now

        person = (self.blind_person or {}).get("full_name") or "chưa gán"

        self.log(
            f"[MÁY CHỦ] Đã kết nối {self.base_url} | thiết bị "
            f"{self.device.get('device_code', '?')} ({self.device.get('name', '')}) "
            f"| người dùng: {person}"
        )

    def open_session(self):

        try:

            data = self.request(
                "POST",
                "/api/device/sessions",
                {
                    "started_at": self.started_at,
                    "model_name": self.model_name,
                }
            )

        except ServerError as error:

            if not error.retryable and not error.unauthorized:
                self.session_unavailable = True

            raise

        self.session_id = data.get("session_id")

    def close_session(self, stats):

        if self.session_id is None or self.session_closed:
            return

        payload = {"ended_at": now_iso()}
        payload.update(stats)

        self.request(
            "PUT",
            f"/api/device/sessions/{self.session_id}",
            payload
        )

        self.session_closed = True

    def heartbeat(self):

        data = self.request("POST", "/api/device/heartbeat", {})

        remote_updated_at = data.get("config_updated_at")

        if (
            remote_updated_at is not None
            and remote_updated_at != self.config_updated_at
        ):
            self.fetch_config()

    def take_alert_batch(self):

        with self.lock:

            count = min(len(self.alert_buffer), MAX_ALERTS_PER_REQUEST)

            return [self.alert_buffer.popleft() for _ in range(count)]

    def return_alert_batch(self, batch):

        with self.lock:

            self.alert_buffer.extendleft(reversed(batch))

            while len(self.alert_buffer) > self.buffer_size:
                self.alert_buffer.popleft()
                self.dropped_alert_count += 1

    def flush_alerts(self):

        while True:

            batch = self.take_alert_batch()

            if not batch:
                return

            try:

                self.request(
                    "POST",
                    "/api/device/alerts",
                    {
                        "session_id": self.session_id,
                        "items": batch,
                    }
                )

            except ServerError as error:

                if error.retryable or error.unauthorized:

                    self.return_alert_batch(batch)

                    raise

                self.dropped_alert_count += len(batch)

                self.log(
                    f"[MÁY CHỦ] Máy chủ từ chối {len(batch)} cảnh báo ({error}), bỏ lô này."
                )

                continue

            self.sent_alert_count += len(batch)

    def notify_sos(self, sent, sos_id=None):

        if self.on_sos_result is None:
            return

        try:
            self.on_sos_result(sent, sos_id)
        except Exception as error:
            self.log(f"[MÁY CHỦ] Lỗi xử lý kết quả SOS: {error}")

    def send_pending_sos(self):

        while True:

            with self.lock:
                item = self.sos_queue[0] if self.sos_queue else None

            if item is None:
                return

            try:

                data = self.request(
                    "POST",
                    "/api/device/sos",
                    {"created_at": item["created_at"]}
                )

            except ServerError as error:

                if error.retryable and not error.unauthorized:

                    self.next_sos = time.monotonic() + self.sos_retry_interval

                    if not item["failed_once"]:

                        item["failed_once"] = True

                        self.log("[MÁY CHỦ] Chưa gửi được SOS, đang thử lại...")

                        self.notify_sos(False)

                    raise

                with self.lock:
                    self.sos_queue.popleft()

                self.log(f"[MÁY CHỦ] Máy chủ từ chối SOS ({error}).")

                self.notify_sos(False)

                if error.unauthorized:
                    raise

                continue

            with self.lock:
                self.sos_queue.popleft()

            self.sent_sos_count += 1

            self.log("[MÁY CHỦ] Đã gửi tín hiệu SOS.")

            self.notify_sos(True, data.get("sos_id"))

    def report_rejection(self, action, error):

        key = (getattr(action, "__name__", ""), str(error))

        if key in self.reported_rejections:
            return

        self.reported_rejections.add(key)

        self.log(f"[MÁY CHỦ] Máy chủ trả lỗi {error} khi gọi {key[0]}.")

    def guarded(self, action):

        try:

            action()

            return True

        except ServerError as error:

            if error.retryable or error.unauthorized:
                self.mark_disconnected(error)
            else:
                self.report_rejection(action, error)

        except Exception as error:

            self.mark_disconnected(ServerError(f"lỗi không mong muốn: {error}"))

        return False

    def step(self):

        now = time.monotonic()

        if self.sos_queue and now >= self.next_sos:
            self.guarded(self.send_pending_sos)

        if not self.connected:

            if now < self.next_connect:
                return

            self.next_connect = now + self.retry_interval

            if not self.guarded(self.connect):
                return

        if self.session_id is None and not self.session_unavailable:

            if not self.guarded(self.open_session) and not self.connected:
                return

        now = time.monotonic()

        if now >= self.next_heartbeat:

            self.next_heartbeat = now + self.heartbeat_interval

            if not self.guarded(self.heartbeat):
                return

        if now >= self.next_flush:

            self.next_flush = now + self.batch_interval

            self.guarded(self.flush_alerts)

    def run(self):

        while not self.stop_event.is_set():

            self.step()

            self.wake_event.wait(0.2)
            self.wake_event.clear()

        self.finish()

    def finish(self):

        if not self.connected:
            self.guarded(self.connect)

        if (
            self.connected
            and self.session_id is None
            and not self.session_unavailable
        ):
            self.guarded(self.open_session)

        if self.connected and self.sos_queue:
            self.guarded(self.send_pending_sos)

        if self.connected:
            self.guarded(self.flush_alerts)

        if self.connected:

            stats = self.final_stats or session_stats_from_summary(
                None,
                self.reported_alert_count
            )

            if self.guarded(lambda: self.close_session(stats)):

                self.log(
                    f"[MÁY CHỦ] Đã đóng phiên #{self.session_id}: "
                    f"{self.sent_alert_count} cảnh báo đã đồng bộ."
                )

        if self.sos_queue:

            self.log(
                f"[MÁY CHỦ] Còn {len(self.sos_queue)} tín hiệu SOS chưa gửi được."
            )

        remaining = self.pending_alert_count()

        if remaining:

            self.log(
                f"[MÁY CHỦ] Còn {remaining} cảnh báo chưa gửi được "
                "(máy chủ không phản hồi)."
            )
