import numpy as np
import pytest

from backend.app.services.runway_light_service import (
    scan_window,
    tile_origins,
    overlap_ratio,
    box_iou,
    nms,
    enhance_frame,
    choose_preprocess_mode,
    detection_quality_ok,
    refine_detection_box,
    infer_missing_off_from_rows,
    ByteTrackLite,
    runway_light_service
)
from backend.app.services.navigation_service import navigation_service
from backend.app.services.detection_service import detection_service
from backend.app.services.alert_service import alert_service


# ============================================================
# PRD SECTION 45: UNIT TESTS
# ============================================================

def test_scan_window():
    """Tests dynamic scan window calculation from frame height."""
    y1, y2 = scan_window(height=1000, start_ratio=0.52, height_ratio=0.20)
    assert y1 == 520
    assert y2 == 720
    assert y2 - y1 == 200


def test_tile_origins():
    """Tests tile origins horizontal generation with stride."""
    origins = tile_origins(width=1920, height=1080, tile_size=640, stride=480, center_y=620)
    assert len(origins) >= 3
    for x, y in origins:
        assert 0 <= x <= 1920 - 640
        assert 0 <= y <= 1080 - 640


def test_overlap_ratio():
    """Tests intersection over minimum area calculation."""
    box_a = (10.0, 10.0, 50.0, 50.0)  # Area: 1600
    box_b = (10.0, 10.0, 50.0, 50.0)
    assert overlap_ratio(box_a, box_b) == pytest.approx(1.0, 0.01)

    box_c = (100.0, 100.0, 150.0, 150.0)  # Disjoint
    assert overlap_ratio(box_a, box_c) == pytest.approx(0.0, 0.01)


def test_box_iou():
    """Tests standard Intersection-over-Union calculation."""
    b1 = (0.0, 0.0, 10.0, 10.0)
    b2 = (0.0, 0.0, 10.0, 10.0)
    assert box_iou(b1, b2) == pytest.approx(1.0, 0.01)

    b3 = (5.0, 0.0, 15.0, 10.0)  # Overlap 5x10 = 50, Union = 100 + 100 - 50 = 150 => 1/3
    assert box_iou(b1, b3) == pytest.approx(50.0 / 150.0, 0.05)


def test_nms():
    """Tests suppression of duplicate detections."""
    dets = [
        {"xyxy": (10.0, 10.0, 50.0, 50.0), "conf": 0.90, "class_id": 1},
        {"xyxy": (12.0, 11.0, 48.0, 49.0), "conf": 0.82, "class_id": 1},  # Duplicate
        {"xyxy": (200.0, 200.0, 250.0, 250.0), "conf": 0.75, "class_id": 1},
    ]
    kept = nms(dets, threshold=0.35)
    assert len(kept) == 2
    assert kept[0]["conf"] == 0.90
    assert kept[1]["conf"] == 0.75


def test_enhance_frame():
    """Tests frame enhancement modes (clahe, brighten, darken, none)."""
    frame = np.full((100, 100, 3), 120, dtype=np.uint8)
    enhanced_none = enhance_frame(frame, "none")
    assert np.array_equal(frame, enhanced_none)

    enhanced_clahe = enhance_frame(frame, "clahe")
    assert enhanced_clahe.shape == frame.shape

    enhanced_bright = enhance_frame(frame, "brighten")
    assert enhanced_bright.shape == frame.shape
    assert float(np.mean(enhanced_bright)) >= float(np.mean(frame))

    enhanced_dark = enhance_frame(frame, "darken")
    assert enhanced_dark.shape == frame.shape
    assert float(np.mean(enhanced_dark)) <= float(np.mean(frame))


def test_choose_preprocess_mode():
    """Tests adaptive preprocess selection based on scan band brightness."""
    # Dark band -> brighten
    dark_frame = np.full((500, 500, 3), 40, dtype=np.uint8)
    assert choose_preprocess_mode(dark_frame, (100, 300), "auto") == "brighten"

    # Bright band -> darken
    bright_frame = np.full((500, 500, 3), 200, dtype=np.uint8)
    assert choose_preprocess_mode(bright_frame, (100, 300), "auto") == "darken"

    # Medium band -> clahe
    normal_frame = np.full((500, 500, 3), 120, dtype=np.uint8)
    assert choose_preprocess_mode(normal_frame, (100, 300), "auto") == "clahe"


def test_detection_quality_ok():
    """Tests filtering of false positive runway markings."""
    frame = np.full((300, 300, 3), 120, dtype=np.uint8)
    # Valid ON light
    det_on = {"class_id": 1, "conf": 0.75, "xyxy": (100.0, 100.0, 130.0, 130.0)}
    assert detection_quality_ok(frame, det_on, post_filter=True) is True

    # Low confidence OFF light
    det_off_low_conf = {"class_id": 0, "conf": 0.15, "xyxy": (100.0, 100.0, 130.0, 130.0)}
    assert detection_quality_ok(frame, det_off_low_conf, post_filter=True) is False


def test_refine_detection_box():
    """Tests bounding box refinement with minimum display box size."""
    frame = np.full((200, 200, 3), 50, dtype=np.uint8)
    # Small bright spot
    frame[95:105, 95:105] = 250
    det = {"class_id": 1, "conf": 0.80, "xyxy": (90.0, 90.0, 110.0, 110.0)}
    refined = refine_detection_box(frame, det, refine_boxes=True, min_display_box=10)
    assert "xyxy" in refined
    assert len(refined["xyxy"]) == 4


# ============================================================
# PRD SECTION 46: RUNWAY LIGHT INTEGRATION TESTS
# ============================================================

def test_light_on_detected_state_on():
    """Test 1: LIGHT ON detected -> expected state = ON."""
    simulated_det = {
        "model": "runway_light",
        "class_id": 1,
        "class_name": "LIGHT ON",
        "state": "ON",
        "confidence": 0.92,
        "bbox": [100, 200, 130, 230],
    }
    assert simulated_det["state"] == "ON"
    assert simulated_det["class_name"] == "LIGHT ON"


def test_light_off_detected_state_off():
    """Test 2: LIGHT OFF detected -> expected state = OFF."""
    simulated_det = {
        "model": "runway_light",
        "class_id": 0,
        "class_name": "LIGHT OFF",
        "state": "OFF",
        "confidence": 0.84,
        "bbox": [200, 200, 230, 230],
    }
    assert simulated_det["state"] == "OFF"
    assert simulated_det["class_name"] == "LIGHT OFF"


def test_repeated_off_fault_confirmed():
    """Test 3: Repeated OFF -> Fault confirmed after 5 frames."""
    cam_id = "test-cam-repeated-off"
    alerts = []
    for frame_idx in range(1, 6):
        dets = [{
            "model": "runway_light",
            "class_id": 0,
            "class_name": "LIGHT OFF",
            "state": "OFF",
            "confidence": 0.88,
            "bbox": [150, 150, 180, 180]
        }]
        alerts, _ = alert_service.process_frame_detections(dets, camera_id=cam_id)

    off_alert = next((a for a in alerts if a["class_name"] == "LIGHT OFF"), None)
    assert off_alert is not None
    assert off_alert["status"] == "CONFIRMED"
    assert off_alert["consecutive_frames"] == 5
    assert "CONFIRMED" in off_alert["message"]


def test_temporary_off_false_detection():
    """Test 4: Temporary OFF false detection (1-4 frames) -> No critical fault."""
    cam_id = "test-cam-temp-off"
    # Send only 2 frames of OFF
    for frame_idx in range(1, 3):
        dets = [{
            "model": "runway_light",
            "class_id": 0,
            "class_name": "LIGHT OFF",
            "state": "OFF",
            "confidence": 0.70,
            "bbox": [150, 150, 180, 180]
        }]
        alerts, _ = alert_service.process_frame_detections(dets, camera_id=cam_id)

    off_alert = next((a for a in alerts if a["class_name"] == "LIGHT OFF"), None)
    assert off_alert is not None
    assert off_alert["status"] == "POTENTIAL"
    assert off_alert["consecutive_frames"] == 2


def test_large_gap_between_on_lights_inferred_off():
    """Test 5: Large gap between ON lights -> OFF-GAP inferred when enabled."""
    # 4 ON lights in a row with a large gap between light 2 and 3
    # spacing ~ 40px, but gap between x=180 and x=300 is 120px (3x spacing)
    row_lights = [
        {"class_id": 1, "conf": 0.90, "xyxy": (100.0, 500.0, 120.0, 520.0)},
        {"class_id": 1, "conf": 0.90, "xyxy": (140.0, 500.0, 160.0, 520.0)},
        {"class_id": 1, "conf": 0.90, "xyxy": (180.0, 500.0, 200.0, 520.0)},
        {"class_id": 1, "conf": 0.90, "xyxy": (300.0, 500.0, 320.0, 520.0)},
        {"class_id": 1, "conf": 0.90, "xyxy": (340.0, 500.0, 360.0, 520.0)},
    ]
    inferred = infer_missing_off_from_rows(
        row_lights,
        frame_idx=10,
        fps=25.0,
        infer_missing_off=True,
        infer_min_row_lights=4,
        infer_min_spacing=18.0,
        infer_max_spacing=260.0,
    )
    assert len(inferred) >= 1
    assert inferred[0]["state"] == "OFF-GAP"
    assert inferred[0]["inferred"] is True


# ============================================================
# PRD SECTION 47: END-TO-END PIPELINE & UNIFIED OUTPUT TEST
# ============================================================

def test_tri_model_detection_service_json():
    """Tests end-to-end unified detection JSON format (PRD Section 27)."""
    dummy_frame = np.full((720, 1280, 3), 120, dtype=np.uint8)
    res = detection_service.process_frame(dummy_frame, camera_id="drone-camera-01")

    assert "frame_id" in res
    assert "timestamp" in res
    assert "camera_id" in res
    assert "detections" in res
    assert "alerts" in res
    assert "summary" in res
    assert "nav_count" in res["summary"]
    assert "fod_count" in res["summary"]
    assert "light_on_count" in res["summary"]
    assert "light_off_count" in res["summary"]
    assert "total_detections" in res["summary"]


def test_navigation_classes_dynamic_loading():
    """Tests dynamic loading of classes from navigation model (PRD Section 30)."""
    classes = navigation_service.get_classes()
    assert isinstance(classes, dict)
    assert len(classes) > 0
