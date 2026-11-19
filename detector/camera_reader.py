# ======================================================================
#  FILE: detector/camera_reader.py
#  CHUC NANG: Đọc camera/video ở thread riêng — LatestFrameReader luôn giữ frame mới nhất và bỏ frame cũ khi YOLO xử lý chậm hơn camera.
# ======================================================================

import threading
import time

import cv2

from config import VIDEO_SLOWDOWN, CAMERA_WIDTH, CAMERA_HEIGHT

def open_capture(source, is_camera):

    cap = cv2.VideoCapture(source)

    if is_camera:

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    return cap

class SequentialFrameReader:

    def __init__(self, source, is_camera, realtime=True):

        self.cap = open_capture(source, is_camera)
        self.is_camera = is_camera
        self.realtime = realtime and not is_camera
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.frame_index = 0
        self.start_time = None
        self.dropped_frames = 0

    def isOpened(self):

        return self.cap.isOpened()

    def read(self):

        if self.start_time is None:
            self.start_time = time.perf_counter()

        if self.realtime:

            scheduled = self.start_time + self.frame_index * VIDEO_SLOWDOWN / self.fps
            wait = scheduled - time.perf_counter()

            if wait > 0:
                time.sleep(wait)

            capture_time = scheduled

        ret, frame = self.cap.read()

        if not self.realtime:
            capture_time = time.perf_counter()

        index = self.frame_index
        self.frame_index += 1

        return ret, frame, index, capture_time

    def release(self):

        self.cap.release()

class LatestFrameReader:

    def __init__(self, source, is_camera, realtime=True):

        self.cap = open_capture(source, is_camera)
        self.is_camera = is_camera
        self.realtime = realtime or is_camera
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0

        self.condition = threading.Condition()
        self.latest = None
        self.last_returned_index = -1
        self.finished = False
        self.stopped = False
        self.dropped_frames = 0

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )

        if self.cap.isOpened():
            self.thread.start()

    def isOpened(self):

        return self.cap.isOpened()

    def _run(self):

        start_time = time.perf_counter()
        index = 0

        while not self.stopped:

            if self.realtime and not self.is_camera:

                scheduled = start_time + index * VIDEO_SLOWDOWN / self.fps
                wait = scheduled - time.perf_counter()

                if wait > 0:
                    time.sleep(wait)

            ret, frame = self.cap.read()

            if not ret:
                break

            if self.realtime and not self.is_camera:
                capture_time = start_time + index * VIDEO_SLOWDOWN / self.fps
            else:
                capture_time = time.perf_counter()

            with self.condition:

                if (
                    self.latest is not None
                    and self.latest[1] > self.last_returned_index
                ):
                    self.dropped_frames += 1

                self.latest = (frame, index, capture_time)
                self.condition.notify_all()

                if not self.realtime:
                    while (
                        not self.stopped
                        and self.latest[1] > self.last_returned_index
                    ):
                        self.condition.wait(0.5)

            index += 1

        with self.condition:
            self.finished = True
            self.condition.notify_all()

    def read(self, timeout=5.0):

        with self.condition:

            deadline = time.perf_counter() + timeout

            while (
                self.latest is None
                or self.latest[1] <= self.last_returned_index
            ):

                if self.finished:
                    return False, None, -1, None

                remaining = deadline - time.perf_counter()

                if remaining <= 0:
                    return False, None, -1, None

                self.condition.wait(remaining)

            frame, index, capture_time = self.latest
            self.last_returned_index = index
            self.condition.notify_all()

            return True, frame, index, capture_time

    def release(self):

        with self.condition:
            self.stopped = True
            self.condition.notify_all()

        if self.thread.is_alive():
            self.thread.join(timeout=2)

        self.cap.release()

def create_frame_reader(
    source,
    is_camera,
    use_latest_frame_buffer=True,
    realtime=True
):

    if use_latest_frame_buffer:
        return LatestFrameReader(source, is_camera, realtime)

    return SequentialFrameReader(source, is_camera, realtime)

