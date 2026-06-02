import cv2
from loguru import logger

from app.vision.tracker import CentroidTracker
from app.db.event_writer import save_event
from app.core.camera_config import load_camera_config
from app.vision.auto_calibration import AutoCameraCalibrator


class VideoProcessor:
    def __init__(
        self,
        video_path: str,
        store_id: str = "brigade_bangalore",
        camera_id: str = "cam_entrance",
        frame_skip: int = 5,
    ):
        self.video_path = video_path
        self.store_id = store_id
        self.camera_id = camera_id
        self.frame_skip = frame_skip

        logger.info("Running auto camera calibration.")
        self.camera_config = AutoCameraCalibrator(
                video_path=video_path,
                sample_frames=300,
                frame_skip=10,
            ).infer()
        self.camera_role = self.camera_config.get("camera_role", "unknown")

        self.tracker = CentroidTracker(max_distance=90, max_missing=25)

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=300,
            varThreshold=50,
            detectShadows=True,
        )

        self.track_states = {}
        self.last_entry_frame = None
        self.last_exit_frame = None
        self.last_passby_frame = None
        self.entry_points = []
        self.max_entry_distance = 120
        self.fps = 30
        self.passby_points = []
        self.max_passby_distance = 180

    def _normalize_point(self, cx, cy, width, height):
        return cx / width, cy / height

    def _line_side(self, point, p1, p2):
        x, y = point
        x1, y1 = p1
        x2, y2 = p2

        value = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)

        if value > 0:
            return "positive"
        if value < 0:
            return "negative"
        return "on"

    def _get_zone(self, cx, cy, width, height):
        nx, ny = self._normalize_point(cx, cy, width, height)

        zones = self.camera_config.get("zones", {})

        for zone_name, box in zones.items():
            x1, y1, x2, y2 = box

            if x1 <= nx <= x2 and y1 <= ny <= y2:
                return zone_name

        return "unknown"

    def _detect_moving_people(self, frame):
        mask = self.bg_subtractor.apply(frame)

        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        detections = []

        for contour in contours:
            area = cv2.contourArea(contour)

            if area < 900:
                continue

            x, y, w, h = cv2.boundingRect(contour)

            if h < 40 or w < 20:
                continue

            cx = x + w // 2
            cy = y + h // 2

            detections.append((cx, cy, (x, y, w, h)))

        return detections

    def _crossed_entry_line(self, old_point, new_point):
      line = self.camera_config.get("entry_line")

      if line is None:
          return False, False, "none", "none"

      p1 = tuple(line["p1"])
      p2 = tuple(line["p2"])

      old_side = self._line_side(old_point, p1, p2)
      new_side = self._line_side(new_point, p1, p2)

      outside_side = line["outside_side"]
      inside_side = line["inside_side"]

      is_entry = old_side == outside_side and new_side == inside_side
      is_exit = old_side == inside_side and new_side == outside_side

      return is_entry, is_exit, old_side, new_side
    def _is_duplicate_entry(self, cx, cy, frame_index):
        for entry in self.entry_points:
            old_x = entry["x"]
            old_y = entry["y"]
            old_frame = entry["frame_index"]

            distance = ((cx - old_x) ** 2 + (cy - old_y) ** 2) ** 0.5
            frame_gap = abs(frame_index - old_frame)

            if distance <= self.max_entry_distance and frame_gap <= int(180 * self.fps):
                return True

        return False
    def _is_duplicate_passby(self, cx, cy, frame_index):
      for event in self.passby_points:
          old_x = event["x"]
          old_y = event["y"]
          old_frame = event["frame_index"]

          distance = ((cx - old_x) ** 2 + (cy - old_y) ** 2) ** 0.5
          frame_gap = abs(frame_index - old_frame)

          # Same nearby motion within a short time window is likely
          # the same passerby being re-tracked as a new track.
          if distance <= self.max_passby_distance and frame_gap <= int(20 * self.fps):
              return True

      return False
      
    def _cooldown_allowed(self, last_frame, current_frame, cooldown_seconds):
        if last_frame is None:
            return True

        cooldown_frames = int(cooldown_seconds * self.fps)

        return current_frame - last_frame >= cooldown_frames
    
    def _handle_track_event(self, track_id, track_data, width, height, frame_index):
        centroid = track_data["centroid"]
        previous_centroid = track_data["previous_centroid"]
        track_age = track_data.get("age", 0)

        rules = self.camera_config.get("event_rules", {})
        min_track_age = rules.get("min_track_age_frames", 3)
        count_entry_exit = rules.get("count_entry_exit", False)
        generate_passby = rules.get("generate_passby", False)

        if previous_centroid is None:
            return

        if track_age < min_track_age:
            return

        cx, cy = centroid
        old_cx, old_cy = previous_centroid

        old_point = self._normalize_point(old_cx, old_cy, width, height)
        new_point = self._normalize_point(cx, cy, width, height)

        zone = self._get_zone(cx, cy, width, height)

        state = self.track_states.get(
            track_id,
            {
                "entered": False,
                "exited": False,
                "visited_product": False,
                "visited_billing": False,
                "passby": False,
                "last_zone": None,
            },
        )

        is_entry, is_exit, old_side, new_side = self._crossed_entry_line(
            old_point,
            new_point,
        )

        entry_cooldown_seconds = rules.get("entry_cooldown_seconds", 90)
        entry_cooldown_frames = int(entry_cooldown_seconds * self.fps)

        entry_allowed = True

        if self.last_entry_frame is not None:
            if frame_index - self.last_entry_frame < entry_cooldown_frames:
                entry_allowed = False

        is_duplicate_entry = self._is_duplicate_entry(cx, cy, frame_index)

        if count_entry_exit and is_entry and not state["entered"] and entry_allowed and not is_duplicate_entry:
            save_event(
                store_id=self.store_id,
                camera_id=self.camera_id,
                event_type="entry",
                track_id=f"T{track_id}",
                zone="entrance",
                direction="in",
                x=float(cx),
                y=float(cy),
                meta={
                    "source": "opencv_motion",
                    "camera_role": self.camera_role,
                    "old_side": old_side,
                    "new_side": new_side,
                    "frame_index": frame_index,
                    "track_age": track_age,
                    "duplicate_suppression": "spatial_temporal_entry_filter",
                },
            )

            state["entered"] = True
            state["exited"] = False
            self.last_entry_frame = frame_index

            self.entry_points.append(
                {
                    "x": float(cx),
                    "y": float(cy),
                    "frame_index": frame_index,
                    "track_id": f"T{track_id}",
                }
            )

            logger.info(f"Entry event generated for T{track_id}")

        exit_enabled = rules.get("exit_enabled", False)

        if count_entry_exit and exit_enabled and is_exit and state["entered"] and not state["exited"]:
            save_event(
                store_id=self.store_id,
                camera_id=self.camera_id,
                event_type="exit",
                track_id=f"T{track_id}",
                zone="exit",
                direction="out",
                x=float(cx),
                y=float(cy),
                meta={
                    "source": "opencv_motion",
                    "camera_role": self.camera_role,
                    "old_side": old_side,
                    "new_side": new_side,
                    "frame_index": frame_index,
                    "track_age": track_age,
                },
            )

            state["exited"] = True
            self.last_exit_frame = frame_index

            logger.info(f"Exit event generated for T{track_id}")
        is_duplicate_passby = self._is_duplicate_passby(cx, cy, frame_index)

        passby_allowed = self._cooldown_allowed(
              self.last_passby_frame,
              frame_index,
              8,
          )

        if (
                generate_passby
                and zone in {"outside_walkway", "store_front"}
                and not state["passby"]
                and not is_duplicate_passby
                and passby_allowed
            ):
                save_event(
                    store_id=self.store_id,
                    camera_id=self.camera_id,
                    event_type="outside_passby",
                    track_id=f"T{track_id}",
                    zone=zone,
                    x=float(cx),
                    y=float(cy),
                    meta={
                        "source": "opencv_motion",
                        "camera_role": self.camera_role,
                        "frame_index": frame_index,
                        "track_age": track_age,
                        "duplicate_suppression": "spatial_temporal_passby_filter",
                    },
                )

                state["passby"] = True
                self.last_passby_frame = frame_index

                self.passby_points.append(
                    {
                        "x": float(cx),
                        "y": float(cy),
                        "frame_index": frame_index,
                        "track_id": f"T{track_id}",
                    }
                )

                logger.info(f"Outside passby event generated for T{track_id}")

        if self.camera_role == "inside_store":
            if zone == "product_zone" and not state["visited_product"]:
                save_event(
                    store_id=self.store_id,
                    camera_id=self.camera_id,
                    event_type="zone_visit",
                    track_id=f"T{track_id}",
                    zone="product_zone",
                    x=float(cx),
                    y=float(cy),
                    meta={
                        "source": "opencv_motion",
                        "camera_role": self.camera_role,
                        "frame_index": frame_index,
                        "track_age": track_age,
                    },
                )

                state["visited_product"] = True

                logger.info(f"Product zone event generated for T{track_id}")

            if zone == "billing" and not state["visited_billing"]:
                save_event(
                    store_id=self.store_id,
                    camera_id=self.camera_id,
                    event_type="billing_visit",
                    track_id=f"T{track_id}",
                    zone="billing",
                    x=float(cx),
                    y=float(cy),
                    meta={
                        "source": "opencv_motion",
                        "camera_role": self.camera_role,
                        "frame_index": frame_index,
                        "track_age": track_age,
                    },
                )

                state["visited_billing"] = True

                logger.info(f"Billing event generated for T{track_id}")

        state["last_zone"] = zone
        self.track_states[track_id] = state
    def process(self):
        cap = cv2.VideoCapture(self.video_path)

        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {self.video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 30

        logger.info(f"Processing video: {self.video_path}")
        logger.info(f"Camera ID: {self.camera_id}")
        logger.info(f"Total frames: {total_frames}")
        logger.info(f"FPS: {self.fps}")

        frame_index = 0
        processed_frames = 0

        while True:
            success, frame = cap.read()

            if not success:
                break

            frame_index += 1

            if frame_index % self.frame_skip != 0:
                continue

            height, width = frame.shape[:2]

            detections = self._detect_moving_people(frame)
            tracks = self.tracker.update(detections)

            for track_id, track_data in tracks.items():
                self._handle_track_event(
                    track_id=track_id,
                    track_data=track_data,
                    width=width,
                    height=height,
                    frame_index=frame_index,
                )

            processed_frames += 1

        cap.release()

        logger.info(f"Processed frames: {processed_frames}")
        logger.info("Video processing completed.")

        return {
            "video_path": self.video_path,
            "camera_id": self.camera_id,
            "processed_frames": processed_frames,
            "status": "completed",
            "calibration_used": self.camera_config.get("description"),
        }