import time
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.camera_service import camera_service

client = TestClient(app)

def test_camera_connect_invalid_ip():
    response = client.post(
        "/api/v1/camera/connect",
        json={
            "ip": "invalid-ip-999.999.999",
            "port": 554,
            "protocol": "RTSP",
            "path": "/stream"
        }
    )
    assert response.status_code == 400
    assert "Invalid IP address" in response.json()["detail"]

def test_camera_connect_unreachable_ip():
    # Attempt connecting to a non-existent local test address
    response = client.post(
        "/api/v1/camera/connect",
        json={
            "ip": "192.0.2.1",  # TEST-NET-1 (non-routable)
            "port": 554,
            "protocol": "RTSP",
            "path": "/stream"
        }
    )
    assert response.status_code == 504
    assert "Camera cannot be reached" in response.json()["detail"]

def test_camera_connect_simulated_success():
    response = client.post(
        "/api/v1/camera/connect",
        json={
            "camera_id": "CAM-TEST-SIM",
            "camera_name": "Test Drone Nav Camera",
            "stream_url": "demo://navigation_drone_feed",
            "is_simulated": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["camera_id"] == "CAM-TEST-SIM"
    assert data["status"] in ["LIVE", "CONNECTED", "CONNECTING"]

    # Allow background thread to process at least one frame
    time.sleep(0.3)

    # Check status endpoint
    status_resp = client.get("/api/v1/camera/CAM-TEST-SIM/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["camera_id"] == "CAM-TEST-SIM"
    assert status_data["status"] in ["LIVE", "CONNECTED"]
    assert "detections" in status_data

    # Check disconnect endpoint
    disc_resp = client.post("/api/v1/camera/CAM-TEST-SIM/disconnect")
    assert disc_resp.status_code == 200
    assert disc_resp.json()["success"] is True
    assert disc_resp.json()["status"] == "DISCONNECTED"

def test_camera_list():
    response = client.get("/api/v1/camera/list")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_camera_websocket_stream():
    # Connect demo stream first
    client.post(
        "/api/v1/camera/connect",
        json={
            "camera_id": "CAM-WS-TEST",
            "camera_name": "WS Test Camera",
            "stream_url": "demo://navigation_drone_feed",
            "is_simulated": True
        }
    )
    time.sleep(0.2)

    with client.websocket_connect("/ws/v1/camera/CAM-WS-TEST/stream") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "camera_frame"
        assert msg["camera_id"] == "CAM-WS-TEST"
        assert "status" in msg
        assert "detections" in msg

    client.post("/api/v1/camera/CAM-WS-TEST/disconnect")
