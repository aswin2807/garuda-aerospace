import os
import cv2
import json
import time
import pytest
import numpy as np
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.navigation_service import navigation_service
from backend.app.services.fod_service import fod_service
from backend.app.services.runway_light_service import runway_light_service
from backend.app.services.frame_processor import frame_processor
from backend.app.services.tracking_service import tracking_service
from backend.app.services.detection_aggregator import detection_aggregator
from backend.app.services.database_service import database_service
from backend.app.services.video_service import video_service

client = TestClient(app)

# ============================================================
# Test 1 — Model Loading (PRD Section 43 Test 1)
# ============================================================
def test_prd_test_1_model_loading():
    """
    Verify:
    navigation_best.pt       PASS
    FOD_Karhtikeyan.pt       PASS
    runway_light_best.pt     PASS
    """
    assert navigation_service.loaded is True, "navigation_best.pt must be loaded"
    assert fod_service.loaded is True, "FOD_Karhtikeyan.pt must be loaded"
    assert runway_light_service.loaded is True, "runway_light_best.pt must be loaded"

# ============================================================
# Test 2 — Video Frame Reading (PRD Section 43 Test 2)
# ============================================================
def test_prd_test_2_video_frame_reading():
    """
    Verify: Frame received = True from video file
    """
    video_path = "data/videos/runway_demo.mp4"
    assert os.path.exists(video_path), f"Video file {video_path} must exist"

    cap = cv2.VideoCapture(video_path)
    assert cap.isOpened(), "VideoCapture must open video file"

    ret, frame = cap.read()
    cap.release()

    assert ret is True, "Frame read must succeed"
    assert frame is not None, "Frame array must not be None"
    assert frame.shape[0] > 0 and frame.shape[1] > 0, "Frame dimensions must be positive"

# ============================================================
# Test 3 — YOLO Inference (PRD Section 43 Test 3)
# ============================================================
def test_prd_test_3_yolo_inference():
    """
    Run each model against real images from test dataset
    """
    sample_frame = cv2.imread("test/images/2025_12_09_20_03_42_mp4-0061_jpg.rf.924873919e1ef71cb0aebcbb105f2ea7.jpg")
    if sample_frame is None:
        sample_frame = np.ones((512, 512, 3), dtype=np.uint8) * 128

    # Navigation inference
    nav_dets = navigation_service.predict(sample_frame, conf_threshold=0.20)
    assert isinstance(nav_dets, list)

    # FOD inference
    fod_dets = fod_service.predict(sample_frame, conf=0.15)
    assert isinstance(fod_dets, list)

    # Runway Light inference
    light_dets = runway_light_service.predict(sample_frame, conf=0.15)
    assert isinstance(light_dets, list)

# ============================================================
# Test 4 — Detection Count & Tracking (PRD Section 43 Test 4)
# ============================================================
def test_prd_test_4_detection_count_and_tracking():
    """
    Verify tracking assigns persistent track IDs across frames and counts are accurate
    """
    tracking_service.reset_session()

    fake_dets_f1 = [
        {"model": "fod", "class_name": "FOD", "confidence": 0.88, "bbox": [100, 100, 200, 200]},
        {"model": "runway_light", "class_name": "LIGHT ON", "confidence": 0.92, "bbox": [300, 300, 350, 350]}
    ]

    tracked_f1 = tracking_service.update(fake_dets_f1, frame_id=1)
    assert len(tracked_f1) == 2
    id1 = tracked_f1[0]["track_id"]
    id2 = tracked_f1[1]["track_id"]
    assert id1 is not None and id2 is not None

    # Frame 2: same objects slightly moved
    fake_dets_f2 = [
        {"model": "fod", "class_name": "FOD", "confidence": 0.89, "bbox": [102, 101, 201, 201]},
        {"model": "runway_light", "class_name": "LIGHT ON", "confidence": 0.91, "bbox": [301, 300, 351, 350]}
    ]
    tracked_f2 = tracking_service.update(fake_dets_f2, frame_id=2)
    assert tracked_f2[0]["track_id"] == id1, "FOD object must maintain persistent track_id across frames"
    assert tracked_f2[1]["track_id"] == id2, "LIGHT ON object must maintain persistent track_id"

    # Verify session unique totals = 1 FOD, 1 LIGHT ON (not 2 FOD!)
    unique_counts = tracking_service.get_session_unique_counts()
    assert unique_counts["fod"] == 1
    assert unique_counts["light_on"] == 1

# ============================================================
# Test 5 — Database Persistence (PRD Section 43 Test 5)
# ============================================================
def test_prd_test_5_database_persistence():
    """
    Verify detection and session records are inserted into drone_nav.db
    """
    session_id = f"TEST-SESSION-{int(time.time())}"
    sid = database_service.create_session(source="test_source.mp4", session_id=session_id)
    assert sid == session_id

    fake_dets = [
        {"model": "fod", "class_name": "FOD", "confidence": 0.85, "bbox": {"x1": 50, "y1": 50, "x2": 150, "y2": 150}, "track_id": 99}
    ]
    database_service.save_detections(session_id=session_id, frame_id=1, detections=fake_dets)
    database_service.record_frame(session_id=session_id, frame_number=1, stream_fps=30.0, inference_ms=120.0, counts={"fod": 1})

    dets = database_service.get_session_detections(session_id)
    assert len(dets) >= 1
    assert dets[0]["class_name"] == "FOD"
    assert dets[0]["track_id"] == 99

# ============================================================
# Test 6 — WebSocket Payload Schema (PRD Section 43 Test 6)
# ============================================================
def test_prd_test_6_websocket_payload_schema():
    """
    Verify WebSocket detection update schema includes counts, session_totals, performance
    """
    with client.websocket_connect("/ws/v1/detection/DR-01") as ws:
        # Send a dummy 64x64 frame
        dummy_img = np.zeros((64, 64, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", dummy_img)
        b64_str = "data:image/jpeg;base64," + os.urandom(0).hex() # or base64 encode
        import base64
        b64_str = base64.b64encode(buf.tobytes()).decode("utf-8")

        ws.send_text(json.dumps({
            "image": b64_str,
            "confidence_threshold": 0.20
        }))

        resp_text = ws.receive_text()
        data = json.loads(resp_text)

        assert "counts" in data, "Payload must contain backend-computed counts"
        assert "navigation" in data["counts"]
        assert "fod" in data["counts"]
        assert "light_on" in data["counts"]
        assert "light_off" in data["counts"]
        assert "session_totals" in data, "Payload must contain session_totals"
        assert "performance" in data, "Payload must contain performance"

# ============================================================
# Test 7 — Full End-to-End Pipeline (PRD Section 43 Test 7)
# ============================================================
def test_prd_test_7_full_pipeline_video_start_stop():
    """
    Full pipeline: POST /api/v1/video/start -> background inference -> GET status -> POST stop
    """
    # 1. Start video analysis
    start_resp = client.post("/api/v1/video/start", json={"source": "data/videos/runway_demo.mp4"})
    assert start_resp.status_code == 200
    res = start_resp.json()
    assert res["status"] == "RUNNING"
    session_id = res["session_id"]

    # 2. Wait 1.5 seconds for frame reader and models to process
    time.sleep(1.5)

    # 3. Check status
    status_resp = client.get(f"/api/v1/video/{session_id}/status")
    assert status_resp.status_code == 200
    st_data = status_resp.json()
    assert st_data["status"] == "RUNNING"
    assert st_data.get("frames_read", 0) > 0
    assert st_data.get("frames_processed", 0) > 0

    # 4. Stop video session
    stop_resp = client.post(f"/api/v1/video/{session_id}/stop")
    assert stop_resp.status_code == 200
    stop_data = stop_resp.json()
    assert stop_data["status"] == "COMPLETED"
    assert "statistics" in stop_data

    # 5. Check session statistics API
    stats_resp = client.get(f"/api/v1/session/{session_id}/statistics")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["session_id"] == session_id
    assert stats["processed_frames"] > 0

# ============================================================
# Test 8 — Critical Debug Pipeline Endpoint (PRD Section 36 & 37)
# ============================================================
def test_prd_test_8_debug_pipeline_health():
    """
    Verify GET /api/v1/debug/pipeline and GET /api/v1/debug/pipeline/health
    """
    resp = client.get("/api/v1/debug/pipeline")
    assert resp.status_code == 200
    data = resp.json()
    assert "frames_received" in data
    assert "frames_processed" in data
    assert "navigation_inferences" in data
    assert "fod_inferences" in data
    assert "runway_inferences" in data
    assert "detections_received" in data
    assert "database_events" in data
    assert "websocket_clients" in data

    health_resp = client.get("/api/v1/debug/pipeline/health")
    assert health_resp.status_code == 200
    h_data = health_resp.json()
    assert "video" in h_data
    assert "frame_reader" in h_data
    assert "navigation" in h_data
    assert "fod" in h_data
    assert "runway_light" in h_data
    assert "database" in h_data
    assert "websocket" in h_data
