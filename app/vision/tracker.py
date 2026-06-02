import math


class CentroidTracker:
    def __init__(self, max_distance=80, max_missing=20):
        self.next_id = 1
        self.tracks = {}
        self.missing = {}
        self.age = {}
        self.max_distance = max_distance
        self.max_missing = max_missing

    def _distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    def update(self, detections):
        updated_tracks = {}
        used_track_ids = set()

        for detection in detections:
            cx, cy, box = detection

            best_id = None
            best_distance = float("inf")

            for track_id, track_data in self.tracks.items():
                if track_id in used_track_ids:
                    continue

                old_cx, old_cy = track_data["centroid"]
                dist = self._distance((cx, cy), (old_cx, old_cy))

                if dist < best_distance and dist <= self.max_distance:
                    best_distance = dist
                    best_id = track_id

            if best_id is None:
                best_id = self.next_id
                self.next_id += 1
                self.age[best_id] = 0

            used_track_ids.add(best_id)
            self.age[best_id] = self.age.get(best_id, 0) + 1

            updated_tracks[best_id] = {
                "centroid": (cx, cy),
                "box": box,
                "previous_centroid": self.tracks.get(best_id, {}).get("centroid"),
                "age": self.age.get(best_id, 0),
            }

            self.missing[best_id] = 0

        for track_id in list(self.tracks.keys()):
            if track_id not in updated_tracks:
                self.missing[track_id] = self.missing.get(track_id, 0) + 1

                if self.missing[track_id] <= self.max_missing:
                    old_track = self.tracks[track_id]
                    old_track["age"] = self.age.get(track_id, 0)
                    updated_tracks[track_id] = old_track
                else:
                    self.age.pop(track_id, None)
                    self.missing.pop(track_id, None)

        self.tracks = updated_tracks

        return self.tracks