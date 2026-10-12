import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.runway_light_service import (
    RunwayGridTracker,
    RunwayLightSlot,
    LIGHT_FAULT_CONFIRM_FRAMES,
    runway_light_service
)
from backend.app.services.analysis_service import analysis_service

client = TestClient(app)

def test_runway_grid_geometric_sorting_not_detection_order():
    """
    PRD Requirement: Column assignment must NEVER rely on YOLO detection order.
    Detections given in reverse horizontal order must still be assigned C1 (left) to CN (right).
    """
    tracker = RunwayGridTracker()

    # Provide detections in ROW 1 where detection 0 is on the RIGHT and detection 1 is on the LEFT
    reverse_order_dets = [
        {"xyxy": (500.0, 100.0, 520.0, 120.0), "class_id": 1, "conf": 0.90, "state": "ON"},  # Right
        {"xyxy": (100.0, 100.0, 120.0, 120.0), "class_id": 1, "conf": 0.92, "state": "ON"},  # Left
    ]

    updated = tracker.update(reverse_order_dets, frame_idx=1)
    assert len(updated) == 2

    # Find the left detection (x ~ 100) and right detection (x ~ 500)
    left_det = next(d for d in updated if d["xyxy"][0] < 200)
    right_det = next(d for d in updated if d["xyxy"][0] > 400)

    assert left_det["column_id"] == 1
    assert left_det["light_id"] == "R1-C1"
    assert right_det["column_id"] == 2
    assert right_det["light_id"] == "R1-C2"


def test_persistent_identity_across_frames():
    """
    PRD Requirement: When a track is followed, its column identity must persist across frames.
    """
    tracker = RunwayGridTracker()

    # Frame 1: 3 lights in Row 1
    f1_dets = [
        {"xyxy": (100.0, 100.0, 120.0, 120.0), "class_id": 1, "conf": 0.90, "state": "ON", "track_id": 10},
        {"xyxy": (200.0, 100.0, 220.0, 120.0), "class_id": 1, "conf": 0.90, "state": "ON", "track_id": 20},
        {"xyxy": (300.0, 100.0, 320.0, 120.0), "class_id": 1, "conf": 0.90, "state": "ON", "track_id": 30},
    ]
    tracker.update(f1_dets, frame_idx=1)

    # In frame 2, the first light (track 10) has a momentary observation gap (missing)
    # Track 20 and 30 must retain their slots R1-C2 and R1-C3 and NOT shift to R1-C1!
    f2_dets = [
        {"xyxy": (202.0, 101.0, 222.0, 121.0), "class_id": 1, "conf": 0.91, "state": "ON", "track_id": 20},
        {"xyxy": (301.0, 100.0, 321.0, 120.0), "class_id": 1, "conf": 0.92, "state": "ON", "track_id": 30},
    ]
    updated_f2 = tracker.update(f2_dets, frame_idx=2)

    det20 = next(d for d in updated_f2 if d["track_id"] == 20)
    det30 = next(d for d in updated_f2 if d["track_id"] == 30)

    assert det20["light_id"] == "R1-C2"
    assert det30["light_id"] == "R1-C3"


def test_temporal_fault_confirmation_rule():
    """
    PRD Requirement: Fault confirmed only after LIGHT_FAULT_CONFIRM_FRAMES = 5 frames.
    Temporary flickers do not flip state.
    """
    slot = RunwayLightSlot(light_id="R1-C1", row_id=1, column_id=1, track_id=5)

    # Frame 1 to 4: Detected as OFF
    for f in range(1, 5):
        slot.update(frame_idx=f, state="OFF", conf=0.85, bbox=(100.0, 100.0, 120.0, 120.0))
        assert slot.consecutive_off == f
        assert slot.is_confirmed_fault is False  # Not yet confirmed (needs 5)

    # Frame 5: 5th consecutive frame of OFF -> Confirmed!
    slot.update(frame_idx=5, state="OFF", conf=0.85, bbox=(100.0, 100.0, 120.0, 120.0))
    assert slot.consecutive_off == 5
    assert slot.is_confirmed_fault is True
    assert slot.confirmed_state == "OFF"


def test_missing_observation_does_not_convert_to_off():
    """
    PRD Requirement: Missing detection != OFF. Observation gap must never be blindly defaulted to OFF.
    """
    tracker = RunwayGridTracker()

    # Frame 1 and 2: Light is clearly ON
    for f in range(1, 3):
        tracker.update([
            {"xyxy": (100.0, 100.0, 120.0, 120.0), "class_id": 1, "conf": 0.95, "state": "ON", "track_id": 1}
        ], frame_idx=f)

    slot = tracker.slots["R1-C1"]
    assert slot.confirmed_state == "ON"
    assert slot.is_confirmed_fault is False

    # Frames 3, 4, 5: Light is missing from detections (empty list)
    for f in range(3, 6):
        tracker.update([], frame_idx=f)

    # Slot must STILL be ON, consecutive_off must NOT increase, must NOT be a fault!
    assert slot.confirmed_state == "ON"
    assert slot.consecutive_off == 0
    assert slot.is_confirmed_fault is False


def test_unique_counting_formula():
    """
    PRD Requirement: Total Lights = ON + OFF + UNKNOWN.
    Deduplicated physical lights.
    """
    tracker = RunwayGridTracker()

    # Simulate 3 lights: 1 ON, 1 confirmed OFF, 1 UNKNOWN
    tracker.update([
        {"xyxy": (100.0, 100.0, 120.0, 120.0), "class_id": 1, "conf": 0.95, "state": "ON", "track_id": 1},
        {"xyxy": (200.0, 100.0, 220.0, 120.0), "class_id": 0, "conf": 0.85, "state": "OFF", "track_id": 2},
        {"xyxy": (300.0, 100.0, 320.0, 120.0), "class_id": 1, "conf": 0.20, "state": "UNKNOWN", "track_id": 3},
    ], frame_idx=1)

    # Run for 5 frames so track 2 confirms OFF
    for f in range(2, 6):
        tracker.update([
            {"xyxy": (100.0, 100.0, 120.0, 120.0), "class_id": 1, "conf": 0.95, "state": "ON", "track_id": 1},
            {"xyxy": (200.0, 100.0, 220.0, 120.0), "class_id": 0, "conf": 0.85, "state": "OFF", "track_id": 2},
        ], frame_idx=f)

    stats = tracker.get_summary_stats()
    assert stats["total_lights"] == stats["lights_on"] + stats["lights_off"] + stats["lights_unknown"]
    assert stats["lights_on"] >= 1
    assert stats["lights_off"] >= 1
    assert stats["confirmed_faults"] == 1


def test_runway_summary_api_endpoint():
    """
    Tests GET /api/v1/runway-light/{job_id}/summary returns structured matrix and counts.
    """
    # Create a dummy runway job
    job_info = analysis_service.create_video_job(
        filename="test_runway_matrix.mp4",
        file_bytes=b"dummy_bytes",
        analysis_type="RUNWAY_LIGHT"
    )
    job_id = job_info["job_id"]

    resp = client.get(f"/api/v1/runway-light/{job_id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert "total_lights" in data
    assert "lights_on" in data
    assert "lights_off" in data
    assert "lights_unknown" in data
    assert "confirmed_faults" in data
    assert "matrix" in data
    assert "faults" in data
