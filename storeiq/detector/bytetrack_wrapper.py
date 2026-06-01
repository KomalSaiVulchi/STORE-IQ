"""ByteTrack-inspired multi-object tracking with IoU matching and Kalman filtering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .yolo_detector import Detection


@dataclass
class KalmanState:
    """Simplified Kalman filter state for bounding box tracking."""

    x: np.ndarray  # [cx, cy, w, h, vx, vy, vw, vh]
    P: np.ndarray  # Covariance matrix

    @classmethod
    def from_bbox(cls, bbox: Tuple[int, int, int, int]) -> KalmanState:
        """Initialize state from a bounding box."""
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        w = float(x2 - x1)
        h = float(y2 - y1)
        x = np.array([cx, cy, w, h, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
        P = np.eye(8, dtype=np.float64) * 10.0
        P[4:, 4:] *= 100.0  # Higher uncertainty for velocities
        return cls(x=x, P=P)

    def predict(self) -> None:
        """Predict next state using constant velocity model."""
        F = np.eye(8, dtype=np.float64)
        F[0, 4] = 1.0  # cx += vx
        F[1, 5] = 1.0  # cy += vy
        F[2, 6] = 1.0  # w += vw
        F[3, 7] = 1.0  # h += vh
        Q = np.eye(8, dtype=np.float64)
        Q[:4, :4] *= 1.0
        Q[4:, 4:] *= 0.01
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

    def update(self, bbox: Tuple[int, int, int, int]) -> None:
        """Update state with an observed bounding box."""
        x1, y1, x2, y2 = bbox
        z = np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0, float(x2 - x1), float(y2 - y1)], dtype=np.float64)
        H = np.zeros((4, 8), dtype=np.float64)
        H[:4, :4] = np.eye(4)
        R = np.eye(4, dtype=np.float64) * 1.0
        y = z - H @ self.x
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(8) - K @ H) @ self.P

    def to_bbox(self) -> Tuple[int, int, int, int]:
        """Convert state to bounding box."""
        cx, cy, w, h = self.x[:4]
        x1 = int(cx - w / 2)
        y1 = int(cy - h / 2)
        x2 = int(cx + w / 2)
        y2 = int(cy + h / 2)
        return (x1, y1, x2, y2)


@dataclass
class Track:
    """Tracked object state."""

    track_id: int
    bbox: Tuple[int, int, int, int]
    confidence: float
    is_staff: bool = False
    kalman: KalmanState = field(repr=False, default=None)
    age: int = 0
    hits: int = 1
    time_since_update: int = 0


class ByteTrackWrapper:
    """IoU-based multi-object tracker with Kalman filtering.

    Implements the core ByteTrack algorithm:
    1. Split detections into high-confidence and low-confidence groups
    2. Match high-confidence detections to existing tracks using IoU
    3. Match remaining tracks to low-confidence detections
    4. Create new tracks for unmatched high-confidence detections
    5. Remove stale tracks that haven't been updated recently
    """

    def __init__(
        self,
        high_thresh: float = 0.5,
        low_thresh: float = 0.1,
        match_thresh: float = 0.3,
        max_time_lost: int = 30,
    ) -> None:
        """Initialize tracker with configurable thresholds."""
        self._next_id = 1
        self._tracks: List[Track] = []
        self._high_thresh = high_thresh
        self._low_thresh = low_thresh
        self._match_thresh = match_thresh
        self._max_time_lost = max_time_lost

    def update(self, detections: List[Detection]) -> List[Track]:
        """Update tracker with new detections using IoU matching.

        Args:
            detections: List of detection bounding boxes.

        Returns:
            List of Track objects with stable IDs.
        """
        # Predict new positions for all existing tracks
        for track in self._tracks:
            if track.kalman:
                track.kalman.predict()
                track.bbox = track.kalman.to_bbox()

        # Split detections into high and low confidence
        high_dets = [d for d in detections if d.confidence >= self._high_thresh]
        low_dets = [d for d in detections if self._low_thresh <= d.confidence < self._high_thresh]

        # First association: high-confidence detections to existing tracks
        unmatched_tracks_idx = list(range(len(self._tracks)))
        unmatched_dets_idx = list(range(len(high_dets)))

        if self._tracks and high_dets:
            iou_matrix = self._compute_iou_matrix(
                [t.bbox for t in self._tracks],
                [d.bbox for d in high_dets],
            )
            matched_pairs, unmatched_tracks_idx, unmatched_dets_idx = self._hungarian_match(
                iou_matrix, self._match_thresh
            )
            # Update matched tracks
            for track_idx, det_idx in matched_pairs:
                self._tracks[track_idx].bbox = high_dets[det_idx].bbox
                self._tracks[track_idx].confidence = high_dets[det_idx].confidence
                self._tracks[track_idx].is_staff = high_dets[det_idx].is_staff
                self._tracks[track_idx].hits += 1
                self._tracks[track_idx].time_since_update = 0
                if self._tracks[track_idx].kalman:
                    self._tracks[track_idx].kalman.update(high_dets[det_idx].bbox)

        # Second association: remaining tracks to low-confidence detections
        remaining_tracks = [self._tracks[i] for i in unmatched_tracks_idx]
        if remaining_tracks and low_dets:
            iou_matrix = self._compute_iou_matrix(
                [t.bbox for t in remaining_tracks],
                [d.bbox for d in low_dets],
            )
            matched_pairs_2, still_unmatched_idx, _ = self._hungarian_match(iou_matrix, self._match_thresh)
            for rt_idx, det_idx in matched_pairs_2:
                track = remaining_tracks[rt_idx]
                track.bbox = low_dets[det_idx].bbox
                track.confidence = low_dets[det_idx].confidence
                track.is_staff = low_dets[det_idx].is_staff
                track.hits += 1
                track.time_since_update = 0
                if track.kalman:
                    track.kalman.update(low_dets[det_idx].bbox)
            # Update unmatched_tracks_idx to only truly unmatched
            matched_rt_indices = {rt_idx for rt_idx, _ in matched_pairs_2}
            unmatched_tracks_idx = [
                unmatched_tracks_idx[i]
                for i in range(len(remaining_tracks))
                if i not in matched_rt_indices
            ]

        # Increment time_since_update for unmatched tracks
        for idx in unmatched_tracks_idx:
            self._tracks[idx].time_since_update += 1
            self._tracks[idx].age += 1

        # Create new tracks for unmatched high-confidence detections
        for det_idx in unmatched_dets_idx:
            det = high_dets[det_idx]
            kalman = KalmanState.from_bbox(det.bbox)
            track = Track(
                track_id=self._next_id,
                bbox=det.bbox,
                confidence=det.confidence,
                is_staff=det.is_staff,
                kalman=kalman,
            )
            self._next_id += 1
            self._tracks.append(track)

        # Remove stale tracks
        self._tracks = [t for t in self._tracks if t.time_since_update <= self._max_time_lost]

        # Increment age for all tracks
        for track in self._tracks:
            track.age += 1

        # Return active tracks (recently updated)
        return [t for t in self._tracks if t.time_since_update == 0]

    @staticmethod
    def _compute_iou_matrix(
        boxes_a: List[Tuple[int, int, int, int]],
        boxes_b: List[Tuple[int, int, int, int]],
    ) -> np.ndarray:
        """Compute IoU matrix between two sets of bounding boxes."""
        m, n = len(boxes_a), len(boxes_b)
        iou = np.zeros((m, n), dtype=np.float64)
        for i, (ax1, ay1, ax2, ay2) in enumerate(boxes_a):
            for j, (bx1, by1, bx2, by2) in enumerate(boxes_b):
                inter_x1 = max(ax1, bx1)
                inter_y1 = max(ay1, by1)
                inter_x2 = min(ax2, bx2)
                inter_y2 = min(ay2, by2)
                inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
                area_a = (ax2 - ax1) * (ay2 - ay1)
                area_b = (bx2 - bx1) * (by2 - by1)
                union = area_a + area_b - inter_area
                iou[i, j] = inter_area / union if union > 0 else 0.0
        return iou

    @staticmethod
    def _hungarian_match(
        iou_matrix: np.ndarray, threshold: float
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Greedy matching based on IoU scores.

        Returns:
            Tuple of (matched_pairs, unmatched_row_indices, unmatched_col_indices).
        """
        m, n = iou_matrix.shape
        matched = []
        used_rows = set()
        used_cols = set()

        # Sort all (row, col) pairs by IoU descending
        indices = []
        for i in range(m):
            for j in range(n):
                if iou_matrix[i, j] >= threshold:
                    indices.append((iou_matrix[i, j], i, j))
        indices.sort(reverse=True)

        for _, row, col in indices:
            if row not in used_rows and col not in used_cols:
                matched.append((row, col))
                used_rows.add(row)
                used_cols.add(col)

        unmatched_rows = [i for i in range(m) if i not in used_rows]
        unmatched_cols = [j for j in range(n) if j not in used_cols]
        return matched, unmatched_rows, unmatched_cols
