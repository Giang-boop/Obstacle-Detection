# ======================================================================
#  FILE: detector/box_tracker.py
#  CHUC NANG: Gọi BYTETracker của Ultralytics, gán track_id ổn định cho từng vật.
# ======================================================================

import numpy as np

from ultralytics.engine.results import Boxes
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import IterableSimpleNamespace, yaml_load
from ultralytics.utils.checks import check_yaml

class BoxTracker:

    def __init__(self, tracker_config, frame_rate=30):

        tracker_args = IterableSimpleNamespace(
            **yaml_load(check_yaml(tracker_config))
        )

        self.tracker = BYTETracker(
            tracker_args,
            frame_rate=frame_rate
        )

    def update(self, detections, frame_shape):

        rows = np.array(
            [
                [*d["box"], d["confidence"], d["class_id"]]
                for d in detections
            ],
            dtype=np.float32
        ).reshape(-1, 6)

        tracks = self.tracker.update(
            Boxes(rows, frame_shape),
            None
        )

        if len(tracks) == 0:
            return [dict(d, track_id=None) for d in detections]

        tracked = []

        for track in tracks:

            source = detections[int(track[7])]

            tracked.append(dict(
                source,
                box=tuple(float(v) for v in track[:4]),
                track_id=int(track[4]),
                confidence=float(track[5]),
            ))

        return tracked
