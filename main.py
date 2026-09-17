import cv2
import time

from ultralytics import YOLO

from config import (
    MODEL_PATH,
    INPUT_MODE,
    CAMERA_ID,
    VIDEO_PATH,
    CONFIDENCE_THRESHOLD,
    ALERT_COOLDOWN,
    VIETNAMESE_NAMES
)

from detection_utils import (
    calculate_distance,
    is_in_front_zone,
    get_danger_level,
    get_alert_message,
    draw_detection,
    draw_detection_zone
)

from tts_engine import (
    speak,
    stop_tts
)


# ============================================================
# START
# ============================================================

print("=" * 60)
print("BLIND ASSISTANCE - OBSTACLE DETECTION")
print("=" * 60)


# ============================================================
# LOAD MODEL
# ============================================================

print(
    "[INFO] Loading model:",
    MODEL_PATH
)

try:

    model = YOLO(
        MODEL_PATH
    )

except Exception as e:

    print(
        "[ERROR] Không thể load best.pt"
    )

    print(e)

    raise SystemExit(1)


print(
    "[INFO] Model loaded successfully."
)

print(
    "[INFO] Classes:"
)

for class_id, class_name in model.names.items():

    print(
        f"  {class_id}: {class_name}"
    )


# ============================================================
# OPEN CAMERA / VIDEO
# ============================================================

if INPUT_MODE == 1:

    print(
        "[INFO] MODE: CAMERA"
    )

    cap = cv2.VideoCapture(
        CAMERA_ID
    )

    cap.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        1280
    )

    cap.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        720
    )

else:

    print(
        "[INFO] MODE: VIDEO"
    )

    print(
        "[INFO] Video:",
        VIDEO_PATH
    )

    cap = cv2.VideoCapture(
        VIDEO_PATH
    )


# ============================================================
# CHECK CAMERA / VIDEO
# ============================================================

if not cap.isOpened():

    print(
        "[ERROR] Không thể mở camera/video."
    )

    raise SystemExit(1)


print(
    "[INFO] Input started."
)

print(
    "[INFO] Nhấn Q để thoát."
)


# ============================================================
# VARIABLES
# ============================================================

last_alert_time = 0.0

last_alert_level = None

last_alert_object = None

fps = 0.0

frame_count = 0

fps_start_time = time.time()


# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        # ----------------------------------------------------
        # READ FRAME
        # ----------------------------------------------------

        ret, frame = cap.read()

        if not ret:

            if INPUT_MODE == 2:

                print(
                    "[INFO] Video đã phát hết."
                )

            else:

                print(
                    "[ERROR] Không đọc được camera."
                )

            break


        # ----------------------------------------------------
        # FRAME SIZE
        # ----------------------------------------------------

        frame_height, frame_width = (
            frame.shape[:2]
        )


        # ----------------------------------------------------
        # YOLO
        # ----------------------------------------------------

        results = model(
            frame,
            conf=CONFIDENCE_THRESHOLD,
            verbose=False
        )


        # ----------------------------------------------------
        # NEAREST OBJECT
        # ----------------------------------------------------

        nearest_object = None

        nearest_distance = float(
            "inf"
        )

        nearest_confidence = 0.0

        nearest_box_height = 0

        nearest_k = 0.0


        # ----------------------------------------------------
        # PROCESS DETECTIONS
        # ----------------------------------------------------

        for result in results:

            if result.boxes is None:

                continue


            for box in result.boxes:

                # --------------------------------------------
                # BOX
                # --------------------------------------------

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0].tolist()
                )


                # --------------------------------------------
                # CONFIDENCE
                # --------------------------------------------

                confidence = float(
                    box.conf[0]
                )

                if confidence < CONFIDENCE_THRESHOLD:

                    continue


                # --------------------------------------------
                # CLASS
                # --------------------------------------------

                class_id = int(
                    box.cls[0]
                )

                class_name = str(
                    model.names[class_id]
                )


                # --------------------------------------------
                # DISTANCE
                # --------------------------------------------

                distance, box_height, k = (
                    calculate_distance(
                        class_name,
                        x1,
                        y1,
                        x2,
                        y2
                    )
                )


                # --------------------------------------------
                # DANGER LEVEL
                # --------------------------------------------

                level = get_danger_level(
                    distance
                )


                # --------------------------------------------
                # DRAW
                # --------------------------------------------

                draw_detection(
                    frame,
                    x1,
                    y1,
                    x2,
                    y2,
                    class_name,
                    confidence,
                    distance,
                    level
                )


                # --------------------------------------------
                # FRONT ZONE
                # --------------------------------------------

                in_front = is_in_front_zone(
                    x1,
                    x2,
                    frame_width
                )


                if in_front:

                    cv2.putText(
                        frame,
                        "FRONT",
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


                    # ----------------------------------------
                    # NEAREST OBJECT
                    # ----------------------------------------

                    if distance < nearest_distance:

                        nearest_distance = distance

                        nearest_object = class_name

                        nearest_confidence = confidence

                        nearest_box_height = box_height

                        nearest_k = k


        # ====================================================
        # ALERT
        # ====================================================

        current_time = time.time()


        if nearest_object is not None:

            level = get_danger_level(
                nearest_distance
            )

            message = get_alert_message(
                level,
                nearest_object,
                nearest_distance
            )


            if message is not None:

                elapsed = (
                    current_time
                    - last_alert_time
                )


                if elapsed >= ALERT_COOLDOWN:

                    speak(
                        message
                    )

                    last_alert_time = (
                        current_time
                    )

                    last_alert_level = level

                    last_alert_object = (
                        nearest_object
                    )

        else:

            last_alert_level = None

            last_alert_object = None


        # ====================================================
        # FPS
        # ====================================================

        frame_count += 1

        elapsed_fps = (
            current_time
            - fps_start_time
        )


        if elapsed_fps >= 1.0:

            fps = (
                frame_count
                / elapsed_fps
            )

            frame_count = 0

            fps_start_time = (
                current_time
            )


        # ====================================================
        # DETECTION ZONE
        # ====================================================

        draw_detection_zone(
            frame
        )


        # ====================================================
        # FPS TEXT
        # ====================================================

        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (
                20,
                40
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (
                255,
                255,
                255
            ),
            2
        )


        # ====================================================
        # MODE
        # ====================================================

        if INPUT_MODE == 1:

            mode_text = "MODE: CAMERA"

        else:

            mode_text = "MODE: VIDEO"


        cv2.putText(
            frame,
            mode_text,
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


        # ====================================================
        # NEAREST OBJECT INFO
        # ====================================================

        if nearest_object is not None:

            level = get_danger_level(
                nearest_distance
            )

            vietnamese_name = (
                VIETNAMESE_NAMES.get(
                    nearest_object,
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
                    f"LEVEL: {level} | "
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


        # ====================================================
        # DISPLAY
        # ====================================================

        cv2.imshow(
            "Blind Assistance - Obstacle Detection",
            frame
        )


        # ====================================================
        # KEY
        # ====================================================

        key = cv2.waitKey(1) & 0xFF


        if key == ord("q"):

            break


finally:

    print()
    print(
        "[INFO] Stopping system..."
    )

    cap.release()

    cv2.destroyAllWindows()

    stop_tts()

    print(
        "[INFO] System stopped."
    )