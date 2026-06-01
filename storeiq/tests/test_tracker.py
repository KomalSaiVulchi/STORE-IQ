"""Unit tests for the ByteTrack tracker."""
# PROMPT: Add prompt block for tracking AI-assisted changes
# CHANGES MADE: None required for this file's logic, added prompt block for consistency.

from detector.bytetrack_wrapper import ByteTrackWrapper, Track, KalmanState
from detector.yolo_detector import Detection


def test_new_track_creation():
    """First detection should create a new track with ID 1."""
    tracker = ByteTrackWrapper()
    detections = [Detection(bbox=(100, 100, 200, 300), confidence=0.9)]
    tracks = tracker.update(detections)
    assert len(tracks) == 1
    assert tracks[0].track_id == 1
    assert tracks[0].confidence == 0.9


def test_track_persistence_across_frames():
    """Same object in consecutive frames should keep the same track ID."""
    tracker = ByteTrackWrapper()
    # Frame 1
    det1 = [Detection(bbox=(100, 100, 200, 300), confidence=0.9)]
    tracks1 = tracker.update(det1)
    first_id = tracks1[0].track_id

    # Frame 2: slightly moved
    det2 = [Detection(bbox=(105, 105, 205, 305), confidence=0.88)]
    tracks2 = tracker.update(det2)
    assert len(tracks2) == 1
    assert tracks2[0].track_id == first_id


def test_multiple_tracks():
    """Multiple detections should create multiple tracks."""
    tracker = ByteTrackWrapper()
    detections = [
        Detection(bbox=(10, 10, 80, 200), confidence=0.9),
        Detection(bbox=(300, 100, 400, 350), confidence=0.85),
    ]
    tracks = tracker.update(detections)
    assert len(tracks) == 2
    ids = {t.track_id for t in tracks}
    assert len(ids) == 2


def test_low_confidence_matching():
    """Low confidence detections should match existing tracks but not create new ones."""
    tracker = ByteTrackWrapper(high_thresh=0.5, low_thresh=0.1)
    # Frame 1: high confidence
    det1 = [Detection(bbox=(100, 100, 200, 300), confidence=0.9)]
    tracks1 = tracker.update(det1)
    first_id = tracks1[0].track_id

    # Frame 2: low confidence at same position
    det2 = [Detection(bbox=(105, 105, 205, 305), confidence=0.3)]
    tracks2 = tracker.update(det2)
    assert len(tracks2) == 1
    assert tracks2[0].track_id == first_id


def test_track_stale_removal():
    """Tracks without updates should be removed after max_time_lost frames."""
    tracker = ByteTrackWrapper(max_time_lost=2)
    det = [Detection(bbox=(100, 100, 200, 300), confidence=0.9)]
    tracker.update(det)

    # 3 empty frames should remove the track
    tracker.update([])
    tracker.update([])
    tracks = tracker.update([])
    assert len(tracks) == 0


def test_iou_matrix():
    """IoU matrix should correctly compute overlaps."""
    iou = ByteTrackWrapper._compute_iou_matrix(
        [(0, 0, 10, 10)],
        [(5, 5, 15, 15)],
    )
    # Intersection: 5x5=25, Union: 100+100-25=175
    expected = 25.0 / 175.0
    assert abs(iou[0, 0] - expected) < 0.01


def test_kalman_state():
    """KalmanState should initialize and predict correctly."""
    state = KalmanState.from_bbox((100, 100, 200, 300))
    assert state.x[0] == 150.0  # cx
    assert state.x[1] == 200.0  # cy
    bbox = state.to_bbox()
    assert bbox == (100, 100, 200, 300)

    # Prediction should not change much with zero velocity
    state.predict()
    bbox = state.to_bbox()
    assert abs(bbox[0] - 100) <= 1
    assert abs(bbox[1] - 100) <= 1
