import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.inference_service import inference_service
from backend.app.services.fod_service import fod_service
from backend.app.services.runway_light_service import runway_light_service
from backend.app.services.alert_service import alert_service

client = TestClient(app)

def test_fod_service_loading():
    assert fod_service.loaded is True
    assert fod_service.status == "READY"
    assert any("FOD" in str(v) for v in fod_service.classes.values())

def test_runway_light_service_loading():
    assert runway_light_service.loaded is True
    assert runway_light_service.status == "READY"
    assert any("LIGHT OFF" in str(v) or "OFF" in str(v).upper() for v in runway_light_service.classes.values())
    assert any("LIGHT ON" in str(v) or "ON" in str(v).upper() for v in runway_light_service.classes.values())

def test_alert_service_temporal_confirmation():
    camera_id = "test-cam-temporal"
    
    # Frame 1..4: Potential fault
    for i in range(1, 5):
        dets = [
            {"model": "runway_light", "class_id": 0, "class_name": "LIGHT OFF", "confidence": 0.88, "bbox": {"x1": 10, "y1": 10, "x2": 50, "y2": 50}}
        ]
        alerts, counts = alert_service.process_frame_detections(dets, camera_id=camera_id)
        assert len(alerts) == 1
        assert alerts[0]["event_type"] == "RUNWAY_LIGHT_FAULT"
        assert alerts[0]["status"] == "POTENTIAL"
        assert alerts[0]["consecutive_frames"] == i
        assert counts["light_off_count"] == 1
    
    # Frame 5: Confirmed fault
    dets = [
        {"model": "runway_light", "class_id": 0, "class_name": "LIGHT OFF", "confidence": 0.92, "bbox": {"x1": 10, "y1": 10, "x2": 50, "y2": 50}}
    ]
    alerts, counts = alert_service.process_frame_detections(dets, camera_id=camera_id)
    assert len(alerts) == 1
    assert alerts[0]["event_type"] == "RUNWAY_LIGHT_FAULT"
    assert alerts[0]["status"] == "CONFIRMED"
    assert alerts[0]["consecutive_frames"] == 5

    # Frame with no faults -> reset counter
    alerts_empty, _ = alert_service.process_frame_detections([], camera_id=camera_id)
    assert len(alerts_empty) == 0

def test_alert_service_fod_alert():
    camera_id = "test-cam-fod"
    dets = [
        {"model": "fod", "class_id": 0, "class_name": "FOD", "confidence": 0.95, "bbox": {"x1": 100, "y1": 100, "x2": 150, "y2": 150}}
    ]
    alerts, counts = alert_service.process_frame_detections(dets, camera_id=camera_id)
    assert len(alerts) == 1
    assert alerts[0]["event_type"] == "FOD_DETECTED"
    assert alerts[0]["severity"] == "CRITICAL"
    assert alerts[0]["status"] == "CONFIRMED"
    assert counts["fod_count"] == 1

def test_predict_frame_dual_pipeline():
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    res = inference_service.predict_frame(frame, camera_id="test-dual-pipe")
    assert "detections" in res
    assert "quality" in res
    assert "alerts" in res
    assert "summary" in res
    assert "models" in res
    assert "fod" in res["models"]
    assert "runway_light" in res["models"]
    assert "brightness" in res["quality"]
    assert "sharpness" in res["quality"]

def test_models_status_prd_schema():
    response = client.get("/api/v1/models/status")
    assert response.status_code == 200
    data = response.json()
    # PRD Section 22 requires:
    # "fod": {"loaded": true, "model": "FOD_Karhtikeyan.pt"},
    # "runway_light": {"loaded": true, "model": "runway_light_best.pt"}
    assert "fod" in data
    assert data["fod"]["loaded"] is True
    assert "FOD_Karhtikeyan.pt" in data["fod"]["model"]
    
    assert "runway_light" in data
    assert data["runway_light"]["loaded"] is True
    assert "runway_light_best.pt" in data["runway_light"]["model"]
