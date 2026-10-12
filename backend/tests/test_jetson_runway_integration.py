import json
import os
import csv
from pathlib import Path
import numpy as np
import cv2
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.runway_light_service import (
    detection_quality_ok,
    validate_neighboring_lights,
    draw,
    draw_corner_box,
    scan_window,
    runway_light_service,
)
from backend.app.services.export_service import export_service
from backend.app.services.database_service import database_service

def test_runway_light_paint_rejection():
    """
    PRD Section 13: Rejects painted markings with high white fraction and low saturation.
    """
    # Create synthetic frame with bright white asphalt paint marking
    frame = np.full((200, 200, 3), 40, dtype=np.uint8)  # dark asphalt
    # Paint white marking stripe
    frame[80:120, 80:120] = [250, 250, 250]

    # Candidate false-positive detection over white stripe
    false_det = {
        "xyxy": (85.0, 85.0, 115.0, 115.0),
        "class_id": 0,  # candidate LIGHT OFF
        "conf": 0.28,
        "class_name": "LIGHT OFF",
    }

    # Should be rejected due to white paint fraction
    is_valid = detection_quality_ok(
        frame=frame,
        det=false_det,
        post_filter=True,
        paint_reject=True,
    )
    assert is_valid is False

def test_runway_light_neighboring_validation():
    """
    PRD Section 14: Validates runway light row pattern (● ON ● ON ● OFF ● ON ● ON).
    """
    detections = [
        {"xyxy": (100.0, 100.0, 120.0, 120.0), "class_id": 1, "conf": 0.85},
        {"xyxy": (160.0, 100.0, 180.0, 120.0), "class_id": 1, "conf": 0.88},
        {"xyxy": (220.0, 100.0, 240.0, 120.0), "class_id": 0, "conf": 0.40},  # Candidate OFF surrounded
        {"xyxy": (280.0, 100.0, 300.0, 120.0), "class_id": 1, "conf": 0.82},
        {"xyxy": (340.0, 100.0, 360.0, 120.0), "class_id": 1, "conf": 0.89},
    ]

    validated = validate_neighboring_lights(detections, max_dx=100.0, max_dy=20.0)
    assert len(validated) == 5

    off_det = next(d for d in validated if d["class_id"] == 0)
    assert off_det.get("neighbor_context") == "SURROUNDED_BY_ON"
    assert off_det.get("fault_candidate") is True

def test_runway_light_drawing_annotation():
    """
    PRD Section 23: Draws scan window, corner boxes, and status banner.
    """
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    band = scan_window(480, start_ratio=0.52, height_ratio=0.20)
    detections = [
        {"xyxy": (120.0, 260.0, 140.0, 280.0), "class_id": 1, "conf": 0.90, "state": "ON", "track_id": 1},
        {"xyxy": (200.0, 260.0, 220.0, 280.0), "class_id": 0, "conf": 0.75, "state": "OFF", "track_id": 2},
    ]

    annotated = draw(
        frame=frame,
        detections=detections,
        band=band,
        frame_idx=10,
        fps=30.0,
        box_style="corner",
    )
    assert annotated.shape == (480, 640, 3)
    # The scan window and banner must have non-zero pixels
    assert np.count_nonzero(annotated) > 0

def test_export_service_csv_generation(tmp_path):
    """
    PRD Section 22: Exports detection information to CSV.
    """
    export_srv = export_service
    test_sid = "test_export_sid_001"

    dummy_dets = [
        {
            "frame_id": 1,
            "time_sec": 0.033,
            "track_id": 101,
            "model_name": "runway_light",
            "class_id": 1,
            "class_name": "LIGHT ON",
            "state": "ON",
            "confidence": 0.89,
            "bbox": [100, 200, 120, 220],
        },
        {
            "frame_id": 2,
            "time_sec": 0.066,
            "track_id": 102,
            "model_name": "FOD",
            "class_id": 0,
            "class_name": "FOD",
            "state": "FOD",
            "confidence": 0.94,
            "bbox": [300, 210, 320, 230],
        },
    ]

    csv_path = export_srv.export_session_csv(test_sid, detections=dummy_dets)
    assert csv_path.exists()

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        assert reader[0]["track_id"] == "101"
        assert reader[0]["class_name"] == "LIGHT ON"
        assert reader[1]["track_id"] == "102"
        assert reader[1]["class_name"] == "FOD"

def test_export_service_summary_json():
    """
    PRD Section 22: Exports session summary statistics to JSON.
    """
    test_sid = "test_summary_sid_002"
    dummy_summary = {
        "session_id": test_sid,
        "total_frames": 100,
        "processed_frames": 100,
        "nav_count": 5,
        "fod_count": 2,
        "light_on_count": 20,
        "light_off_count": 1,
        "confirmed_faults": 1,
    }

    summary_path = export_service.export_session_summary(test_sid, summary_data=dummy_summary)
    assert summary_path.exists()

    with open(summary_path, mode="r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["session_id"] == test_sid
        assert data["light_on_count"] == 20
        assert data["confirmed_faults"] == 1

def test_session_export_endpoint():
    """
    PRD Section 22: Tests GET /api/v1/session/{session_id}/export endpoint.
    """
    sid = database_service.create_session(source="data/videos/runway_demo.mp4", source_type="VIDEO_FILE")
    with TestClient(app) as client:
        res = client.get(f"/api/v1/session/{sid}/export")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "EXPORTED"
        assert "csv" in data["files"]
        assert "summary" in data["files"]
