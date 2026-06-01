import cv2
from loguru import logger

from app.vision.tracker import CentroidTracker
from app.db.event_writer import save_event


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

        self.tracker = CentroidTracker(max_distance=90, max_missing=25)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=300,
            varThreshold=50,
            detectShadows=True,
        )

        self.track_states = {}

    def _get_zone(self, cx, cy, width, height):
        if cy > int(height * 0.70):
            return "entrance"
        if cx > int(width * 0.70):
            return "billing"
        return "product_zone"

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

    def _handle_track_event(self, track_id, centroid, previous_centroid, width, height):
        if previous_centroid is None:
            return

        cx, cy = centroid
        old_cx, old_cy = previous_centroid

        zone = self._get_zone(cx, cy, width, height)

        entry_line_y = int(height * 0.72)
        exit_line_y = int(height * 0.90)

        state = self.track_states.get(
            track_id,
            {
                "entered": False,
                "exited": False,
                "visited_product": False,
                "visited_billing": False,
            },
        )

        if old_cy > entry_line_y and cy <= entry_line_y and not state["entered"]:
            save_event(
                store_id=self.store_id,
                camera_id=self.camera_id,
                event_type="entry",
                track_id=f"T{track_id}",
                zone="entrance",
                direction="in",
                x=float(cx),
                y=float(cy),
                meta={"source": "opencv_motion", "line": "entry_line"},
            )
            state["entered"] = True
            logger.info(f"Entry event generated for T{track_id}")

        if old_cy < exit_line_y and cy >= exit_line_y and state["entered"] and not state["exited"]:
            save_event(
                store_id=self.store_id,
                camera_id=self.camera_id,
                event_type="exit",
                track_id=f"T{track_id}",
                zone="exit",
                direction="out",
                x=float(cx),
                y=float(cy),
                meta={"source": "opencv_motion", "line": "exit_line"},
            )
            state["exited"] = True
            logger.info(f"Exit event generated for T{track_id}")

        if state["entered"] and zone == "product_zone" and not state["visited_product"]:
            save_event(
                store_id=self.store_id,
                camera_id=self.camera_id,
                event_type="zone_visit",
                track_id=f"T{track_id}",
                zone="product_zone",
                x=float(cx),
                y=float(cy),
                meta={"source": "opencv_motion"},
            )
            state["visited_product"] = True
            logger.info(f"Product zone event generated for T{track_id}")

        if state["entered"] and zone == "billing" and not state["visited_billing"]:
            save_event(
                store_id=self.store_id,
                camera_id=self.camera_id,
                event_type="billing_visit",
                track_id=f"T{track_id}",
                zone="billing",
                x=float(cx),
                y=float(cy),
                meta={"source": "opencv_motion"},
            )
            state["visited_billing"] = True
            logger.info(f"Billing event generated for T{track_id}")

        self.track_states[track_id] = state

    def process(self):
        cap = cv2.VideoCapture(self.video_path)

        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {self.video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info(f"Processing video: {self.video_path}")
        logger.info(f"Total frames: {total_frames}")

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
                    centroid=track_data["centroid"],
                    previous_centroid=track_data["previous_centroid"],
                    width=width,
                    height=height,
                )

            processed_frames += 1

        cap.release()

        logger.info(f"Processed frames: {processed_frames}")
        logger.info("Video processing completed.")

        return {
            "video_path": self.video_path,
            "processed_frames": processed_frames,
            "status": "completed",
        }