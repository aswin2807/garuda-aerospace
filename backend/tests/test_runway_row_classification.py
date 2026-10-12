import pytest
import numpy as np

from backend.app.core.config import settings
from backend.app.services.runway_light_service import (
    RunwayGridTracker,
    RunwayLightSlot,
    ByteTrackLite,
    detection_quality_ok,
    infer_missing_off_from_rows,
    runway_light_service,
    LIGHT_FAULT_CONFIRM_FRAMES
)
from backend.app.services.navigation_service import navigation_service
from backend.app.services.fod_service import fod_service


def test_runway_light_model_classes_and_isolation():
    """
    Verifies runway light model class mapping is strictly isolated:
    0: LIGHT OFF, 1: LIGHT ON.
    Navigation and FOD services remain independent and unmodified.
    """
    assert runway_light_service.classes.get(0) in ("LIGHT OFF", "off", "OFF")
    assert runway_light_service.classes.get(1) in ("LIGHT ON", "on", "ON")

    # Verify Navigation service is untouched
    nav_classes = navigation_service.get_classes()
    assert isinstance(nav_classes, dict)
    assert len(nav_classes) > 0

    # Verify FOD service is untouched
    assert hasattr(fod_service, "predict")
    assert isinstance(fod_service.classes, dict)
    assert 0 in fod_service.classes


def test_perspective_tilt_slope_estimation_and_clustering():
    """
    Verifies dynamic transversal tilt slope estimation (dy/dx).
    Ensures that runway rows with camera roll / perspective tilt are clustered
    into single cohesive rows rather than split into vertical fragments.
    """
    tracker = RunwayGridTracker()

    # Simulate 2 rows of runway lights with camera perspective tilt slope = -0.035
    # Row 1 base y = 1200, Row 2 base y = 1600
    tilt_slope = -0.035
    xs = np.arange(200.0, 3200.0, 180.0)

    detections = []
    # Row 1 lights
    for i, x in enumerate(xs):
        y = 1200.0 + tilt_slope * x
        detections.append({
            "xyxy": (float(x), float(y), float(x + 40), float(y + 50)),
            "conf": 0.88,
            "class_id": 1,
            "state": "ON",
            "track_id": int(i + 1)
        })

    # Row 2 lights
    for j, x in enumerate(xs):
        y = 1600.0 + tilt_slope * x
        detections.append({
            "xyxy": (float(x), float(y), float(x + 45), float(y + 55)),
            "conf": 0.85,
            "class_id": 0 if j == 3 else 1,
            "state": "OFF" if j == 3 else "ON",
            "track_id": int(len(xs) + j + 1)
        })

    # Update tracker
    updated = tracker.update(detections, frame_idx=1)
    assert len(updated) == len(detections)

    stats = tracker.get_summary_stats()
    # Must identify exactly 2 rows
    assert stats["total_rows"] == 2
    assert len(stats["row_results"]) == 2

    # Each row must contain all of its horizontal lights
    row_counts = [r["total"] for r in stats["row_results"]]
    assert row_counts == [len(xs), len(xs)]

    # Row 1 must have row_id == 1 and Row 2 must have row_id == 2
    r1_slots = [s for s in stats["matrix"] if s["row_id"] == 1]
    r2_slots = [s for s in stats["matrix"] if s["row_id"] == 2]
    assert len(r1_slots) == len(xs)
    assert len(r2_slots) == len(xs)


def test_row_by_row_mathematical_consistency_formula():
    """
    Verifies that for every row and overall:
    Total detected lights = ON + OFF + UNKNOWN
    """
    tracker = RunwayGridTracker()

    # Create detections across 2 rows with mix of ON, OFF, and UNKNOWN
    dets = [
        # Row 1: 3 ON, 1 OFF
        {"xyxy": (100.0, 200.0, 130.0, 230.0), "conf": 0.90, "class_id": 1, "state": "ON", "track_id": 1},
        {"xyxy": (200.0, 200.0, 230.0, 230.0), "conf": 0.92, "class_id": 1, "state": "ON", "track_id": 2},
        {"xyxy": (300.0, 200.0, 330.0, 230.0), "conf": 0.85, "class_id": 0, "state": "OFF", "track_id": 3},
        {"xyxy": (400.0, 200.0, 430.0, 230.0), "conf": 0.91, "class_id": 1, "state": "ON", "track_id": 4},
        # Row 2: 1 ON, 1 UNKNOWN, 1 OFF
        {"xyxy": (100.0, 600.0, 130.0, 630.0), "conf": 0.88, "class_id": 1, "state": "ON", "track_id": 5},
        {"xyxy": (200.0, 600.0, 230.0, 630.0), "conf": 0.15, "class_id": 1, "state": "UNKNOWN", "track_id": 6},
        {"xyxy": (300.0, 600.0, 330.0, 630.0), "conf": 0.80, "class_id": 0, "state": "OFF", "track_id": 7},
    ]

    tracker.update(dets, frame_idx=1)
    stats = tracker.get_summary_stats()

    # Overall formula
    assert stats["total_lights"] == stats["lights_on"] + stats["lights_off"] + stats["lights_unknown"]
    assert stats["total_lights"] == 7

    # Per-row formula
    for row in stats["row_results"]:
        assert row["total"] == row["on"] + row["off"] + row["unknown"]


def test_zero_synthetic_detections_in_default_pipeline():
    """
    PRD Requirement: Never create a light solely because a row has a gap.
    Never interpret a missed detection as proof that a light is OFF.
    infer_missing_off_from_rows must return [] by default.
    """
    assert settings.RUNWAY_INFER_MISSING_OFF is False

    row_dets = [
        {"class_id": 1, "conf": 0.90, "xyxy": (100.0, 500.0, 120.0, 520.0)},
        {"class_id": 1, "conf": 0.90, "xyxy": (140.0, 500.0, 160.0, 520.0)},
        {"class_id": 1, "conf": 0.90, "xyxy": (300.0, 500.0, 320.0, 520.0)},
        {"class_id": 1, "conf": 0.90, "xyxy": (340.0, 500.0, 360.0, 520.0)},
    ]
    inferred = infer_missing_off_from_rows(row_dets, infer_missing_off=False)
    assert inferred == []


def test_missing_observation_preserves_slot_state_without_off_flip():
    """
    Verifies that when a light is momentarily not detected (observation gap),
    it is NOT counted as OFF, consecutive_off does NOT increment,
    and it is never classified as a fault.
    """
    tracker = RunwayGridTracker()

    # Frame 1: Light is ON
    tracker.update([
        {"xyxy": (150.0, 300.0, 180.0, 330.0), "conf": 0.90, "class_id": 1, "state": "ON", "track_id": 1}
    ], frame_idx=1)

    slot = tracker.slots["R1-C1"]
    assert slot.confirmed_state == "ON"
    assert slot.consecutive_off == 0
    assert slot.is_confirmed_fault is False

    # Frames 2, 3, 4: No detections in frame (e.g. occlusion or camera turn)
    for f in range(2, 5):
        tracker.update([], frame_idx=f)

    # Slot must still be ON, not flipped to OFF
    assert slot.confirmed_state == "ON"
    assert slot.consecutive_off == 0
    assert slot.is_confirmed_fault is False

    stats = tracker.get_summary_stats()
    assert stats["lights_off"] == 0
    assert stats["confirmed_faults"] == 0


def test_bytetrack_maintains_track_id_across_state_toggle():
    """
    Verifies ByteTrackLite continues tracking the same physical bounding box
    even if the illumination class flips between ON and OFF.
    """
    tracker = ByteTrackLite(match_iou=0.20)

    # Frame 1: Light is ON (class 1)
    f1 = [{"xyxy": (200.0, 200.0, 240.0, 240.0), "conf": 0.90, "class_id": 1}]
    tracks1 = tracker.update(f1, frame_idx=1)
    assert len(tracks1) == 1
    track_id = tracks1[0]["track_id"]

    # Frame 2: Same physical box toggles to OFF (class 0)
    f2 = [{"xyxy": (202.0, 201.0, 242.0, 241.0), "conf": 0.85, "class_id": 0}]
    tracks2 = tracker.update(f2, frame_idx=2)
    assert len(tracks2) == 1
    # Must retain identical track_id
    assert tracks2[0]["track_id"] == track_id
    assert tracks2[0]["class_id"] == 0


def test_4k_foreground_light_box_filter_tolerance():
    """
    Verifies that detection_quality_ok does NOT discard genuine 4K foreground runway lights
    with dimensions up to 150 px and areas up to 15,000 px.
    """
    frame = np.full((2160, 3840, 3), 100, dtype=np.uint8)

    # 4K foreground light: 60x80 px (area = 4800 px)
    fg_det = {
        "class_id": 1,
        "conf": 0.85,
        "xyxy": (1800.0, 1600.0, 1860.0, 1680.0)
    }
    assert detection_quality_ok(frame, fg_det, post_filter=True) is True

    # 4K foreground OFF light: 75x90 px (area = 6750 px)
    fg_off_det = {
        "class_id": 0,
        "conf": 0.60,
        "xyxy": (1200.0, 1600.0, 1275.0, 1690.0)
    }
    assert detection_quality_ok(frame, fg_off_det, post_filter=True) is True
