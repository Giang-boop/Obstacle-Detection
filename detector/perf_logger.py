# ======================================================================
#  FILE: detector/perf_logger.py
#  CHUC NANG: Ghi log hiệu năng mỗi lần chạy: frames.csv, objects.csv, alerts.csv, summary.json + ghi video demo theo timeline.
# ======================================================================

import csv
import json
import os
import threading
import time

def percentile(values, p):

    if not values:
        return None

    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))

    return ordered[index]

def mean(values):

    return sum(values) / len(values) if values else None

def r(value, digits=1):

    return None if value is None else round(value, digits)

class PerformanceLogger:

    def __init__(self, log_dir, run_name, enabled=True, profile=None):

        self.enabled = enabled
        self.profile = profile
        self.start_time = time.perf_counter()
        self.lock = threading.Lock()

        self.frames = []
        self.alerts = {}

        self.video_start = None
        self.lost_events = 0
        self.object_ids = {}

        stamp = time.strftime("%Y%m%d_%H%M%S")
        self.run_dir = os.path.join(log_dir, f"{run_name}_{stamp}")

        self.objects_file = None
        self.objects_writer = None

        if self.enabled:

            os.makedirs(self.run_dir, exist_ok=True)

            self.objects_file = open(
                os.path.join(self.run_dir, "objects.csv"),
                "w", newline="", encoding="utf-8-sig"
            )

            self.objects_writer = csv.writer(self.objects_file)

            self.objects_writer.writerow([
                "time_s", "frame", "object_id", "class", "confidence",
                "distance_raw_m", "distance_m", "position", "level", "state",
                "held", "approach_speed_mps", "ttc_s", "early_warning"
            ])

    def rel(self, t):

        return None if t is None else t - self.start_time

    def log_frame(
        self,
        frame_index,
        capture_time,
        loop_start,
        infer_ms,
        end_time,
        fps,
        dropped_frames,
        nearest_object,
        nearest_distance,
        nearest_id,
        object_count
    ):

        self.frames.append({
            "frame": frame_index,
            "time_s": r(self.rel(end_time), 3),
            "infer_ms": r(infer_ms, 2),
            "process_ms": r((end_time - loop_start) * 1000, 2),
            "frame_age_ms": r((end_time - capture_time) * 1000, 2),
            "fps": r(fps, 2),
            "dropped_frames": dropped_frames,
            "objects": object_count,
            "nearest_object": nearest_object or "",
            "nearest_id": "" if nearest_id is None else nearest_id,
            "nearest_distance_m": (
                "" if nearest_distance is None else r(nearest_distance, 3)
            ),
        })

    def log_object(self, now, frame_index, obj, state=None):

        if obj.object_id not in self.object_ids:
            self.object_ids[obj.object_id] = 0

        self.object_ids[obj.object_id] += 1

        if not self.enabled:
            return

        self.objects_writer.writerow([
            r(self.rel(now), 3),
            frame_index,
            obj.object_id,
            obj.class_name,
            r(obj.confidence, 3),
            r(obj.raw_distance, 3),
            r(obj.distance, 3),
            obj.position,
            obj.level,
            state or obj.state,
            int(obj.held),
            r(obj.approach_speed, 3),
            "" if obj.ttc is None else r(obj.ttc, 2),
            int(obj.early_warning),
        ])

    def log_lost(self, now, frame_index, obj):

        self.lost_events += 1
        self.log_object(now, frame_index, obj, state="LOST")

    def log_alert(self, alert, frame_index, capture_time, created_time):

        target = alert["target"]

        with self.lock:

            self.alerts[alert["alert_id"]] = {
                "alert_id": alert["alert_id"],
                "frame": frame_index,
                "object_id": target.object_id,
                "class": target.class_name,
                "level": target.level,
                "position": target.position,
                "distance_m": r(target.distance, 2),
                "confidence": r(target.confidence, 3),
                "early_warning": int(target.early_warning),
                "reason": alert["reason"],
                "message": alert["message"],
                "capture_s": r(self.rel(capture_time), 3),
                "detect_s": r(self.rel(created_time), 3),
                "speech_start_s": None,
                "capture_to_speech_ms": None,
                "detect_to_speech_ms": None,
                "status": "cho_doc",
                "video_speech_start_s": None,
                "video_speech_end_s": None,
                "_capture": capture_time,
                "_created": created_time,
            }

    def on_speech_event(self, event, message, timestamp):

        alert_id = message.get("alert_id")

        with self.lock:

            alert = self.alerts.get(alert_id)

            if alert is None:
                return

            if self.video_start is not None:

                video_time = r(timestamp - self.video_start, 3)

                if event == "start":
                    alert["video_speech_start_s"] = video_time

                elif event in ("done", "interrupted"):
                    alert["video_speech_end_s"] = video_time

            if event == "start":

                alert["speech_start_s"] = r(self.rel(timestamp), 3)
                alert["capture_to_speech_ms"] = r(
                    (timestamp - alert["_capture"]) * 1000
                )
                alert["detect_to_speech_ms"] = r(
                    (timestamp - alert["_created"]) * 1000
                )
                alert["status"] = "dang_doc"

            elif event == "done":
                alert["status"] = "da_doc"

            elif event == "interrupted":
                alert["status"] = "bi_ngat_boi_cau_nguy_hiem_hon"

            elif event == "replaced":
                alert["status"] = "bi_thay_boi_cau_moi_hon"

            elif event == "dropped_lower":
                alert["status"] = "bo_vi_dang_cho_cau_nguy_hiem_hon"

            elif event == "dropped_stale":
                alert["status"] = "bo_vi_cho_qua_lau"

    def distance_jitter(self):

        diffs = []
        previous = None

        for f in self.frames:

            if f["nearest_distance_m"] == "":
                previous = None
                continue

            key = (f["nearest_object"], f["nearest_id"])

            if previous is not None and previous[0] == key:
                diffs.append(abs(f["nearest_distance_m"] - previous[1]))

            previous = (key, f["nearest_distance_m"])

        return mean(diffs)

    def nearest_flicker(self):

        present = [f["nearest_distance_m"] != "" for f in self.frames]
        count = 0
        i = 1

        while i < len(present):

            if present[i - 1] and not present[i]:

                j = i
                while j < len(present) and not present[j] and j - i < 2:
                    j += 1

                if j < len(present) and present[j] and j - i <= 2:
                    count += 1

                i = j

            i += 1

        return count

    def summary(self, total_source_frames=None):

        frames = self.frames
        duration = (
            frames[-1]["time_s"] - frames[0]["time_s"] if len(frames) > 1 else 0
        )

        alerts = list(self.alerts.values())

        def count(status):
            return sum(1 for a in alerts if a["status"] == status)

        capture_lat = [
            a["capture_to_speech_ms"] for a in alerts
            if a["capture_to_speech_ms"] is not None
        ]

        detect_lat = [
            a["detect_to_speech_ms"] for a in alerts
            if a["detect_to_speech_ms"] is not None
        ]

        ages = [f["frame_age_ms"] for f in frames]
        infer = [f["infer_ms"] for f in frames]
        process = [f["process_ms"] for f in frames]

        track_lengths = list(self.object_ids.values())

        return {
            "profile": self.profile,
            "so_frame_xu_ly": len(frames),
            "so_frame_nguon": total_source_frames,
            "so_frame_bo_qua": frames[-1]["dropped_frames"] if frames else 0,
            "thoi_gian_chay_s": r(duration, 2),
            "fps_tb": r(len(frames) / duration if duration else None, 2),
            "inference_ms_tb": r(mean(infer), 2),
            "inference_ms_p95": r(percentile(infer, 95), 2),
            "xu_ly_1_frame_ms_tb": r(mean(process), 2),
            "do_tre_frame_ms_tb": r(mean(ages), 1),
            "do_tre_frame_ms_p95": r(percentile(ages, 95), 1),
            "do_tre_frame_ms_max": r(max(ages) if ages else None, 1),
            "so_canh_bao_tao_ra": len(alerts),
            "so_canh_bao_da_doc": count("da_doc") + count("dang_doc"),
            "so_canh_bao_bi_ngat": count("bi_ngat_boi_cau_nguy_hiem_hon"),
            "so_canh_bao_bi_thay": count("bi_thay_boi_cau_moi_hon"),
            "so_canh_bao_bo_qua": (
                count("bo_vi_dang_cho_cau_nguy_hiem_hon")
                + count("bo_vi_cho_qua_lau")
                + count("cho_doc")
            ),
            "tre_phat_hien_den_doc_ms_tb": r(mean(detect_lat)),
            "tre_phat_hien_den_doc_ms_p95": r(percentile(detect_lat, 95)),
            "tre_chup_frame_den_doc_ms_tb": r(mean(capture_lat)),
            "tre_chup_frame_den_doc_ms_p95": r(percentile(capture_lat, 95)),
            "do_rung_khoang_cach_m": r(self.distance_jitter(), 4),
            "so_lan_nhap_nhay_vat_gan_nhat": self.nearest_flicker(),
            "so_id_vat_the": len(track_lengths),
            "do_dai_tb_moi_id_frame": r(mean(track_lengths), 1),
            "so_su_kien_lost": self.lost_events,
            "canh_bao_som_do_lao_toi": sum(a["early_warning"] for a in alerts),
            "canh_bao_ben_trai_phai": sum(
                1 for a in alerts if a["position"] in ("LEFT", "RIGHT")
            ),
        }

    def close(self, total_source_frames=None):

        result = self.summary(total_source_frames)

        if not self.enabled:
            return result

        if self.objects_file:
            self.objects_file.close()

        if self.frames:

            with open(
                os.path.join(self.run_dir, "frames.csv"),
                "w", newline="", encoding="utf-8-sig"
            ) as f:
                writer = csv.DictWriter(f, fieldnames=list(self.frames[0].keys()))
                writer.writeheader()
                writer.writerows(self.frames)

        with self.lock:
            alerts = [
                {k: v for k, v in a.items() if not k.startswith("_")}
                for a in self.alerts.values()
            ]

        if alerts:

            with open(
                os.path.join(self.run_dir, "alerts.csv"),
                "w", newline="", encoding="utf-8-sig"
            ) as f:
                writer = csv.DictWriter(f, fieldnames=list(alerts[0].keys()))
                writer.writeheader()
                writer.writerows(alerts)

        with open(
            os.path.join(self.run_dir, "summary.json"),
            "w", encoding="utf-8"
        ) as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

class TimelineVideoWriter:

    def __init__(self, path, fps, size):

        import cv2

        self.writer = cv2.VideoWriter(
            path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            size
        )
        self.fps = fps
        self.start = None
        self.next_tick = 0
        self.displayed = None

    def show(self, frame, shown_at, video_start):

        if self.start is None:
            self.start = video_start

        while (
            self.displayed is not None
            and self.start + self.next_tick / self.fps < shown_at
        ):
            self.writer.write(self.displayed)
            self.next_tick += 1

        if self.displayed is None:
            self.next_tick = max(0, int((shown_at - self.start) * self.fps))
            black = frame * 0
            for _ in range(self.next_tick):
                self.writer.write(black)

        self.displayed = frame.copy()

    def release(self, end_time=None):

        if self.displayed is not None:

            if end_time is not None:
                while self.start + self.next_tick / self.fps < end_time:
                    self.writer.write(self.displayed)
                    self.next_tick += 1

            self.writer.write(self.displayed)

        self.writer.release()

