# ======================================================================
#  FILE: detector/main.py
#  CHUC NANG: Chương trình chính của app thiết bị: đọc tham số dòng lệnh, chạy vòng lặp YOLO, vẽ HUD/bounding box/mũi tên dự đoán, phím Q thoát / S gửi SOS, đồng bộ dữ liệu lên máy chủ khi thoát.
# ======================================================================

import argparse
import json
import os
import cv2
import time

import numpy as np

from ultralytics import YOLO

import config

from config import (
    MODEL_PATH,
    INPUT_MODE,
    CAMERA_ID,
    VIDEO_PATH,
    IMG_SIZE,
    LOG_DIR
)

from runtime_settings import settings

from detection_utils import (
    get_box_color,
    draw_detection,
    draw_motion,
    draw_detection_zone,
    to_ascii
)

from camera_reader import create_frame_reader

from frame_pipeline import FramePipeline

from perf_logger import PerformanceLogger, TimelineVideoWriter

from tts_engine import (
    speak,
    stop_tts,
    set_speech_callback,
    set_tts_muted
)

from server_client import (
    ServerClient,
    build_alert_item,
    session_stats_from_summary
)

parser = argparse.ArgumentParser()
parser.add_argument("--profile", choices=["A", "B", "C"], default=None)
parser.add_argument("--headless", action="store_true")
parser.add_argument("--mute", action="store_true")
parser.add_argument("--device", default=config.DEVICE)
parser.add_argument("--no-realtime", action="store_true")
parser.add_argument("--save-video", default=None)
parser.add_argument("--run-name", default=None)
parser.add_argument("--video", default=VIDEO_PATH)
parser.add_argument("--model", default=MODEL_PATH)
parser.add_argument("--camera", action="store_true")
parser.add_argument("--max-frames", type=int, default=None)
parser.add_argument("--server-url", default=config.SERVER_URL)
parser.add_argument("--device-key", default=config.DEVICE_KEY)
parser.add_argument("--offline", action="store_true")
args = parser.parse_args()

SOS_PRIORITY = 3

SOS_OVERLAY_SECONDS = 4.0

sos_state = {
    "text": None,
    "time": 0.0,
    "last_press": float("-inf"),
}

def show_sos(text):

    sos_state["text"] = text
    sos_state["time"] = time.perf_counter()

def on_sos_result(sent, sos_id):

    if sent:

        show_sos(f"SOS: DA GUI TIN HIEU CAU CUU (#{sos_id})")

        speak(
            "Đã gửi tín hiệu cầu cứu",
            priority=SOS_PRIORITY
        )

    else:

        show_sos("SOS: CHUA GUI DUOC, DANG THU LAI")

        speak(
            "Chưa gửi được tín hiệu cầu cứu, đang thử lại",
            priority=SOS_PRIORITY
        )

server_client = None

if config.ENABLE_SERVER and not args.offline:

    server_client = ServerClient(
        server_url=args.server_url,
        device_key=args.device_key,
        model_name=os.path.basename(args.model),
        on_sos_result=on_sos_result
    )

    print(
        "[INFO] Máy chủ:",
        args.server_url
    )

    server_client.start()

else:

    print(
        "[INFO] Chế độ ngoại tuyến: không kết nối máy chủ."
    )

def request_sos():

    now = time.perf_counter()

    if now - sos_state["last_press"] < config.SOS_DEBOUNCE_SECONDS:
        return

    sos_state["last_press"] = now

    print(
        "[SOS] Người dùng bấm phím SOS."
    )

    if server_client is None:

        show_sos("SOS: CHE DO NGOAI TUYEN, KHONG GUI DUOC")

        speak(
            "Chưa gửi được tín hiệu cầu cứu, thiết bị đang ở chế độ ngoại tuyến",
            priority=SOS_PRIORITY
        )

        return

    show_sos("SOS: DANG GUI...")

    server_client.send_sos()

use_latest_frame_buffer = config.USE_LATEST_FRAME_BUFFER
use_distance_smoothing = config.USE_DISTANCE_SMOOTHING
use_tracking = config.USE_TRACKING

if args.profile == "A":
    use_latest_frame_buffer = False
    use_distance_smoothing = False
    use_tracking = False

elif args.profile == "B":
    use_latest_frame_buffer = True
    use_distance_smoothing = True
    use_tracking = False

elif args.profile == "C":
    use_latest_frame_buffer = True
    use_distance_smoothing = True
    use_tracking = True

pipeline = FramePipeline(
    use_tracking=use_tracking,
    use_distance_smoothing=use_distance_smoothing
)

association = pipeline.association

alert_manager = pipeline.alert_manager

profile_name = args.profile or "CONFIG"

input_mode = 1 if args.camera else INPUT_MODE

show_window = config.SHOW_WINDOW and not args.headless

video_realtime = config.VIDEO_REALTIME and not args.no_realtime

print("=" * 60)
print("BLIND ASSISTANCE - OBSTACLE DETECTION")
print("=" * 60)

print(
    f"[INFO] Profile: {profile_name} | "
    f"Latest frame buffer: {use_latest_frame_buffer} | "
    f"Smoothing: {use_distance_smoothing} | "
    f"Tracking: {use_tracking}"
)

print(
    "[INFO] Loading model:",
    args.model
)

try:

    model = YOLO(
        args.model
    )

except Exception as e:

    print(
        "[ERROR] Không thể load model:",
        args.model
    )

    print(e)

    raise SystemExit(1)

print(
    "[INFO] Model loaded successfully."
)

model(
    np.zeros((640, 640, 3), dtype=np.uint8),
    imgsz=IMG_SIZE,
    device=args.device,
    verbose=False
)

print(
    "[INFO] Classes:"
)

for class_id, class_name in model.names.items():

    print(
        f"  {class_id}: {class_name}"
    )

if input_mode == 1:

    print(
        "[INFO] MODE: CAMERA"
    )

    source = CAMERA_ID

else:

    print(
        "[INFO] MODE: VIDEO"
    )

    print(
        "[INFO] Video:",
        args.video
    )

    source = args.video

total_source_frames = None

if input_mode != 1:

    probe = cv2.VideoCapture(source)
    total_source_frames = int(probe.get(cv2.CAP_PROP_FRAME_COUNT))
    source_fps = probe.get(cv2.CAP_PROP_FPS) or 30.0
    probe.release()

else:

    source_fps = 30.0

cap = create_frame_reader(
    source,
    is_camera=(input_mode == 1),
    use_latest_frame_buffer=use_latest_frame_buffer,
    realtime=video_realtime
)

if not cap.isOpened():

    print(
        "[ERROR] Không thể mở camera/video."
    )

    raise SystemExit(1)

print(
    "[INFO] Input started."
)

print(
    "[INFO] Nhấn Q để thoát, S để gửi tín hiệu cầu cứu (SOS)."
)

logger = PerformanceLogger(
    LOG_DIR,
    args.run_name or f"profile_{profile_name}",
    enabled=config.ENABLE_LOG,
    profile=profile_name
)

set_speech_callback(
    logger.on_speech_event
)

if args.mute:
    set_tts_muted(True)

last_alert_time = 0.0
last_alert_level = None
last_alert_object = None

last_message = None
last_message_time = 0.0

fps = 0.0
frame_count = 0
fps_start_time = time.time()

video_writer = None

try:

    while True:

        ret, frame, frame_index, capture_time = cap.read()

        if not ret:

            if input_mode == 2:

                print(
                    "[INFO] Video đã phát hết."
                )

            else:

                print(
                    "[ERROR] Không đọc được camera."
                )

            break

        if args.max_frames is not None and frame_index >= args.max_frames:
            break

        loop_start = time.perf_counter()

        if logger.video_start is None:
            logger.video_start = capture_time - frame_index / source_fps

        frame_height, frame_width = (
            frame.shape[:2]
        )

        infer_start = time.perf_counter()

        raw_detections = pipeline.detect(
            model,
            frame,
            args.device
        )

        infer_ms = (
            time.perf_counter() - infer_start
        ) * 1000

        current_time = time.perf_counter()

        frame_result = pipeline.analyze(
            raw_detections,
            current_time,
            frame_width
        )

        objects = frame_result.objects
        lost_objects = frame_result.lost_objects
        alert = frame_result.alert

        nearest = frame_result.nearest

        nearest_object = None
        nearest_distance = None
        nearest_box_height = 0
        nearest_k = 0.0
        nearest_level = None
        nearest_id = pipeline.display_id(nearest)

        if nearest is not None:

            nearest_distance = nearest.distance
            nearest_object = nearest.class_name
            nearest_box_height = nearest.box_height
            nearest_k = nearest.k
            nearest_level = nearest.level

        if alert is not None:

            logger.log_alert(
                alert,
                frame_index,
                capture_time,
                current_time
            )

            speak(
                alert["message"],
                priority=alert["priority"],
                created_time=current_time,
                alert_id=alert["alert_id"],
                distance=alert["distance"]
            )

            if server_client is not None:

                server_client.report_alert(
                    build_alert_item(alert)
                )

            last_alert_time = alert_manager.last_alert_time
            last_alert_level = alert_manager.last_alert_level
            last_alert_object = alert_manager.last_alert_object

            last_message = alert["message"]
            last_message_time = current_time

        for obj in objects:
            logger.log_object(current_time, frame_index, obj)

        for obj in lost_objects:
            logger.log_lost(current_time, frame_index, obj)

        target = frame_result.target

        for obj in objects:

            x1, y1, x2, y2 = obj.box

            draw_detection(
                frame,
                x1,
                y1,
                x2,
                y2,
                obj.class_name,
                obj.confidence,
                obj.distance,
                obj.level,
                object_id=(
                    obj.object_id if association != "none" else None
                ),
                held=obj.held
            )

            info_parts = [
                {"LEFT": "TRAI", "CENTER": "GIUA", "RIGHT": "PHAI"}[obj.position]
            ]

            if obj.ttc is not None:
                info_parts.append(f"TTC {obj.ttc:.1f}s")

            if obj.held:
                info_parts.append("giu")

            cv2.putText(
                frame,
                " ".join(info_parts),
                (
                    x1,
                    min(
                        y2 + 25,
                        frame_height - 10
                    )
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (
                    255,
                    255,
                    0
                ),
                2
            )

            if use_tracking:

                draw_motion(
                    frame,
                    obj.center,
                    obj.predicted_center,
                    get_box_color(obj.level)
                )

            if target is obj:

                cv2.rectangle(
                    frame,
                    (x1 - 4, y1 - 4),
                    (x2 + 4, y2 + 4),
                    (255, 255, 255),
                    2
                )

        frame_count += 1

        now_wall = time.time()

        elapsed_fps = (
            now_wall
            - fps_start_time
        )

        if elapsed_fps >= 1.0:

            fps = (
                frame_count
                / elapsed_fps
            )

            frame_count = 0

            fps_start_time = (
                now_wall
            )

        draw_detection_zone(
            frame
        )

        frame_age_ms = (
            time.perf_counter() - capture_time
        ) * 1000

        cv2.putText(
            frame,
            f"FPS: {fps:.1f} | YOLO: {infer_ms:.0f} ms | "
            f"Tre: {frame_age_ms:.0f} ms | Bo: {cap.dropped_frames}",
            (
                20,
                40
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (
                255,
                255,
                255
            ),
            2
        )

        if input_mode == 1:

            mode_text = "MODE: CAMERA"

        else:

            mode_text = "MODE: VIDEO"

        cv2.putText(
            frame,
            f"{mode_text} | PROFILE: {profile_name}",
            (
                20,
                145
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (
                255,
                255,
                255
            ),
            2
        )

        if nearest_object is not None:

            vietnamese_name = to_ascii(
                settings.vietnamese_name(
                    nearest_object
                )
            )

            info = (
                f"Gan nhat: "
                f"{vietnamese_name} | "
                f"Distance: "
                f"{nearest_distance:.1f} m"
            )

            cv2.putText(
                frame,
                info,
                (
                    20,
                    75
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (
                    255,
                    255,
                    255
                ),
                2
            )

            cv2.putText(
                frame,
                (
                    f"LEVEL: {nearest_level} | "
                    f"K={nearest_k:.0f} | "
                    f"h={nearest_box_height}px"
                ),
                (
                    20,
                    110
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (
                    0,
                    255,
                    255
                ),
                2
            )

        else:

            cv2.putText(
                frame,
                "Khong phat hien vat can",
                (
                    20,
                    75
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (
                    0,
                    255,
                    0
                ),
                2
            )

        if (
            last_message is not None
            and current_time - last_message_time < 2.0
        ):

            cv2.rectangle(
                frame,
                (0, frame_height - 90),
                (frame_width, frame_height - 50),
                (0, 0, 0),
                -1
            )

            cv2.putText(
                frame,
                to_ascii(last_message),
                (
                    10,
                    frame_height - 62
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (
                    0,
                    255,
                    255
                ),
                2
            )

        if (
            sos_state["text"] is not None
            and time.perf_counter() - sos_state["time"] < SOS_OVERLAY_SECONDS
        ):

            cv2.rectangle(
                frame,
                (10, 160),
                (min(frame_width - 10, 490), 200),
                (0, 0, 200),
                -1
            )

            cv2.putText(
                frame,
                sos_state["text"],
                (
                    20,
                    187
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (
                    255,
                    255,
                    255
                ),
                2
            )

        end_time = time.perf_counter()

        logger.log_frame(
            frame_index,
            capture_time,
            loop_start,
            infer_ms,
            end_time,
            fps,
            cap.dropped_frames,
            nearest_object,
            nearest_distance,
            nearest_id,
            len(objects)
        )

        if args.save_video:

            if video_writer is None:

                video_writer = TimelineVideoWriter(
                    args.save_video,
                    source_fps,
                    (frame_width, frame_height)
                )

            video_writer.show(
                frame,
                end_time,
                logger.video_start
            )

        if show_window:

            cv2.imshow(
                "Blind Assistance - Obstacle Detection",
                frame
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):

                break

            if key in (ord("s"), ord("S")):

                request_sos()

finally:

    print()

    print(
        "[INFO] Stopping system..."
    )

    cap.release()

    if video_writer is not None:
        video_writer.release(time.perf_counter())

    if show_window:
        cv2.destroyAllWindows()

    time.sleep(1.5)

    stop_tts()

    summary = logger.close(total_source_frames)

    print(
        "[INFO] Tổng kết:"
    )

    print(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )

    if server_client is not None:

        print(
            "[INFO] Đồng bộ dữ liệu còn lại lên máy chủ..."
        )

        server_client.stop(
            session_stats_from_summary(
                summary,
                server_client.reported_alert_count
            )
        )

    if config.ENABLE_LOG:

        print(
            "[INFO] Log:",
            os.path.abspath(logger.run_dir)
        )

    print(
        "[INFO] System stopped."
    )

