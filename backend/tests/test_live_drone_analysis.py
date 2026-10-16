import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.camera_service import camera_service, sanitize_stream_url
from backend.app.services.runway_light_service import runway_light_service

client = TestClient(app)

def test_credential_sanitization_security():
    """FR-01: Ensure plain-text camera credentials are never exposed in URLs or logs."""
    raw_url = "rtsp://admin:SecretPass123!@192.168.1.100:554/live/ch0"
    sanitized = sanitize_stream_url(raw_url)
    assert "SecretPass123!" not in sanitized
    assert ":****@" in sanitized
    assert "rtsp://admin:****@192.168.1.100:554/live/ch0" == sanitized

    # Safe url without credentials should remain unchanged
    safe_url = "rtsp://192.168.1.100:554/live/ch0"
    assert sanitize_stream_url(safe_url) == safe_url

    # Demo url should remain unchanged
    demo_url = "demo://navigation_drone_feed"
    assert sanitize_stream_url(demo_url) == demo_url

def test_connect_with_credentials_masks_password():
    """FR-01: Connect request with username and password masks password in response and status."""
    connect_resp = client.post(
        "/api/v1/camera/connect",
        json={
            "camera_id": "CAM-CREDS-TEST",
            "camera_name": "Perimeter Drone Cam",
            "ip": "192.0.2.10",
            "port": 554,
            "protocol": "RTSP",
            "path": "/stream",
            "username": "operator",
            "password": "SuperSecretPassword999",
            "is_simulated": True  # avoid 504 network probe on dummy IP
        }
    )
    assert connect_resp.status_code == 200
    data = connect_resp.json()
    assert data["success"] is True
    assert "SuperSecretPassword999" not in data["stream_url"]
    assert "SuperSecretPassword999" not in data["message"]
    assert ":****@" in data["stream_url"]

    # Verify status endpoint also masks credentials
    status_resp = client.get("/api/v1/camera/CAM-CREDS-TEST/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "SuperSecretPassword999" not in status_data["stream_url"]

    client.post("/api/v1/camera/CAM-CREDS-TEST/disconnect")

def test_live_drone_flight_analysis_lifecycle():
    """FR-02, FR-03, FR-04: Full live drone flight detection lifecycle."""
    flight_custom_id = "FLIGHT-GARUDA-2026-TEST01"

    # 1. Connect drone IP camera stream with designated flight ID
    connect_resp = client.post(
        "/api/v1/camera/connect",
        json={
            "camera_id": "DRONE-CAM-FLIGHT-01",
            "camera_name": "Garuda Optical Drone 01",
            "flight_id": flight_custom_id,
            "stream_url": "demo://navigation_drone_feed",
            "is_simulated": True
        }
    )
    assert connect_resp.status_code == 200
    conn_data = connect_resp.json()
    assert conn_data["success"] is True
    assert conn_data["flight_id"] == flight_custom_id
    assert conn_data["flight_status"] in ["FLYING", "ANALYSIS_ACTIVE"]

    # 2. Allow live YOLO11 frames to be processed (poll until first frame finishes warmup)
    for _ in range(40):
        time.sleep(0.15)
        status_resp = client.get("/api/v1/camera/DRONE-CAM-FLIGHT-01/status")
        if status_resp.status_code == 200 and status_resp.json().get("frames_analyzed", 0) >= 1:
            break

    # 3. Inspect Drone Analysis Column metrics via status endpoint (FR-04)
    status_resp = client.get("/api/v1/camera/DRONE-CAM-FLIGHT-01/status")
    assert status_resp.status_code == 200
    status = status_resp.json()

    # FR-04 Mandatory Fields Verification:
    assert status["flight_id"] == flight_custom_id
    assert status["status"] in ["CONNECTED", "LIVE", "CONNECTING"]
    assert status["flight_status"] in ["FLYING", "ANALYSIS_ACTIVE"]
    assert "latest_detected_object" in status
    assert "latest_confidence" in status
    assert "last_detection_time" in status
    assert "total_detections" in status
    assert "frames_analyzed" in status
    assert status["frames_analyzed"] >= 1
    assert "pre_landing_summary" in status

    # FR-03 YOLO11 Model verification:
    assert "runway_light_best.pt" in status["model"]

    # 4. Finalize Flight / Pre-Landing Summary (FR-06)
    complete_resp = client.post("/api/v1/camera/DRONE-CAM-FLIGHT-01/complete-flight")
    assert complete_resp.status_code == 200
    comp_data = complete_resp.json()
    assert comp_data["success"] is True
    assert comp_data["flight_id"] == flight_custom_id
    assert comp_data["flight_status"] == "COMPLETED"
    assert comp_data["summary_status"] == "READY"

    summary = comp_data["summary"]
    assert summary["flight_id"] == flight_custom_id
    assert summary["flight_status"] == "COMPLETED"
    assert summary["summary_status"] == "READY"
    assert "total_unique_objects" in summary
    assert "light_on_count" in summary
    assert "light_off_count" in summary
    assert "min_confidence" in summary
    assert "avg_confidence" in summary
    assert "max_confidence" in summary
    assert "flight_duration_sec" in summary
    assert summary["frames_analyzed"] >= 1
    assert summary["model"] == "runway_light_best.pt"

    # 5. Verify GET /flight-summary endpoint retrieves the finalized summary
    fetch_summary_resp = client.get("/api/v1/camera/DRONE-CAM-FLIGHT-01/flight-summary")
    assert fetch_summary_resp.status_code == 200
    fetched_summary = fetch_summary_resp.json()
    assert fetched_summary["flight_id"] == flight_custom_id
    assert fetched_summary["flight_status"] == "COMPLETED"
    assert fetched_summary["summary_status"] == "READY"

    # 6. Disconnect Camera
    disc_resp = client.post("/api/v1/camera/DRONE-CAM-FLIGHT-01/disconnect")
    assert disc_resp.status_code == 200
    disc_data = disc_resp.json()
    assert disc_data["success"] is True
    assert disc_data["status"] == "DISCONNECTED"
    assert disc_data["pre_landing_summary"] is not None

def test_websocket_broadcast_contains_drone_analysis_fields():
    """FR-04, FR-05: Real-time WebSocket transmission includes all Drone Analysis column metrics."""
    client.post(
        "/api/v1/camera/connect",
        json={
            "camera_id": "WS-ANALYSIS-TEST",
            "camera_name": "Drone Analysis WS Test",
            "flight_id": "FLIGHT-WS-001",
            "stream_url": "demo://navigation_drone_feed",
            "is_simulated": True
        }
    )
    time.sleep(0.2)

    with client.websocket_connect("/ws/v1/camera/WS-ANALYSIS-TEST/stream") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "camera_frame"
        assert msg["camera_id"] == "WS-ANALYSIS-TEST"
        assert msg["flight_id"] == "FLIGHT-WS-001"
        assert "flight_status" in msg
        assert "camera_status" in msg
        assert "latest_detected_object" in msg
        assert "latest_confidence" in msg
        assert "last_detection_time" in msg
        assert "frames_analyzed" in msg
        assert "pre_landing_summary" in msg
        assert "counts" in msg
        assert "detections" in msg

    client.post("/api/v1/camera/WS-ANALYSIS-TEST/disconnect")

def test_empty_flight_pending_summary():
    """FR-06: Pre-landing summary is clearly marked PENDING if flight ends before processing completes."""
    stream = camera_service.connect_camera(
        camera_id="CAM-ZERO-FRAME",
        stream_url="demo://empty",
        is_simulated=True,
        flight_id="FLIGHT-ZERO-01"
    )
    # Complete immediately before analyzing any frame
    summary = stream.complete_flight()
    assert summary["summary_status"] == "PENDING"
    assert summary["frames_analyzed"] == 0

    camera_service.disconnect_camera("CAM-ZERO-FRAME")
