import cv2
from collections import defaultdict
from loguru import logger


class AutoCameraCalibrator:
    def __init__(self, video_path: str, sample_frames: int = 300, frame_skip: int = 10):
        self.video_path = video_path
        self.sample_frames = sample_frames
        self.frame_skip = frame_skip

    def _detect_motion_centers(self, frame, bg_subtractor):
        mask = bg_subtractor.apply(frame)

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

        centers = []

        for contour in contours:
            area = cv2.contourArea(contour)

            if area < 1200:
                continue

            x, y, w, h = cv2.boundingRect(contour)

            if h < 40 or w < 20:
                continue

            cx = x + w // 2
            cy = y + h // 2

            centers.append((cx, cy))

        return centers

    def infer(self):
        cap = cv2.VideoCapture(self.video_path)

        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {self.video_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=200,
            varThreshold=50,
            detectShadows=True,
        )

        region_hits = defaultdict(int)
        frame_index = 0
        sampled = 0

        while sampled < self.sample_frames:
            success, frame = cap.read()

            if not success:
                break

            frame_index += 1

            if frame_index % self.frame_skip != 0:
                continue

            centers = self._detect_motion_centers(frame, bg_subtractor)

            for cx, cy in centers:
                nx = cx / width
                ny = cy / height

                if nx >= 0.72:
                    region_hits["right"] += 1
                if nx <= 0.28:
                    region_hits["left"] += 1
                if ny >= 0.72:
                    region_hits["bottom"] += 1
                if ny <= 0.28:
                    region_hits["top"] += 1
                if 0.28 < nx < 0.72 and 0.28 < ny < 0.72:
                    region_hits["center"] += 1

            sampled += 1

        cap.release()

        edge_hits = (
            region_hits["right"]
            + region_hits["left"]
            + region_hits["bottom"]
            + region_hits["top"]
        )

        center_hits = region_hits["center"]
        total_motion_hits = edge_hits + center_hits

        logger.info(f"Auto calibration region hits: {dict(region_hits)}")

        if total_motion_hits < 10:
            return self._inside_store_config(
                "Very low motion evidence; treating as inside-store camera."
            )

        edge_ratio = edge_hits / total_motion_hits
        center_ratio = center_hits / total_motion_hits

        logger.info(
            f"Auto calibration ratios: edge_ratio={edge_ratio:.2f}, center_ratio={center_ratio:.2f}"
        )

        if edge_hits < 10:
            return self._inside_store_config(
                "Weak edge movement; treating as inside-store camera."
            )

        if center_ratio >= 0.55:
            return self._inside_store_config(
                "Center-dominant movement; treating as inside-store camera."
            )

        if center_hits < 30:
            return self._outside_passby_config(
                "Not enough interior motion to confirm store entry."
            )

        strongest_edge = max(
            ["right", "left", "bottom", "top"],
            key=lambda key: region_hits[key],
        )

        return self._entrance_config(strongest_edge)

    def _entrance_config(self, edge: str):
        if edge == "right":
            line = {
                "p1": [0.78, 0.05],
                "p2": [0.78, 0.95],
                "outside_side": "negative",
                "inside_side": "positive",
            }
            zones = {
                "entrance": [0.72, 0.00, 1.00, 1.00],
                "product_zone": [0.20, 0.15, 0.72, 0.95],
                "billing": [0.00, 0.00, 0.25, 0.60],
            }

        elif edge == "left":
            line = {
                "p1": [0.22, 0.05],
                "p2": [0.22, 0.95],
                "outside_side": "positive",
                "inside_side": "negative",
            }
            zones = {
                "entrance": [0.00, 0.00, 0.28, 1.00],
                "product_zone": [0.28, 0.15, 0.90, 0.95],
                "billing": [0.70, 0.00, 1.00, 0.60],
            }

        elif edge == "bottom":
            line = {
                "p1": [0.05, 0.72],
                "p2": [0.95, 0.72],
                "outside_side": "positive",
                "inside_side": "negative",
            }
            zones = {
                "entrance": [0.00, 0.72, 1.00, 1.00],
                "product_zone": [0.15, 0.20, 0.85, 0.72],
                "billing": [0.70, 0.00, 1.00, 0.35],
            }

        else:
            line = {
                "p1": [0.05, 0.28],
                "p2": [0.95, 0.28],
                "outside_side": "negative",
                "inside_side": "positive",
            }
            zones = {
                "entrance": [0.00, 0.00, 1.00, 0.28],
                "product_zone": [0.15, 0.28, 0.85, 0.90],
                "billing": [0.70, 0.65, 1.00, 1.00],
            }

        return {
            "description": f"Auto inferred entrance camera from {edge} boundary.",
            "camera_role": "entrance",
            "entry_line": line,
            "event_rules": {
                "entry_cooldown_seconds": 90,
                "exit_enabled": False,
                "min_track_age_frames": 3,
                "count_entry_exit": True,
                "generate_passby": False,
            },
            "zones": zones,
        }

    def _inside_store_config(self, reason: str):
        return {
            "description": f"Auto inferred inside-store camera. {reason}",
            "camera_role": "inside_store",
            "entry_line": None,
            "event_rules": {
                "entry_cooldown_seconds": 90,
                "exit_enabled": False,
                "min_track_age_frames": 3,
                "count_entry_exit": False,
                "generate_passby": False,
            },
            "zones": {
                "product_zone": [0.10, 0.10, 0.90, 0.95],
                "billing": [0.70, 0.00, 1.00, 0.45],
            },
        }

    def _outside_passby_config(self, reason: str):
        return {
            "description": f"Auto inferred outside-passby camera. {reason}",
            "camera_role": "outside_passby",
            "entry_line": None,
            "event_rules": {
                "entry_cooldown_seconds": 90,
                "exit_enabled": False,
                "min_track_age_frames": 3,
                "count_entry_exit": False,
                "generate_passby": True,
            },
            "zones": {
                "outside_walkway": [0.35, 0.00, 1.00, 1.00],
                "store_front": [0.00, 0.00, 0.35, 1.00],
            },
        }
