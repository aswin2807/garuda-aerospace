import time
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.inference_service import inference_service
from backend.app.services.rtsp_service import LatestFrameReader
from backend.app.services.camera_service import camera_service

client = TestClient(app)

def test_quality_metrics():
    # Normal frame
    frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    brightness, sharpness, warnings = inference_service.quality_metrics(frame)
    assert 120 <= brightness <= 135
    assert isinstance(sharpness, float)
    assert "IMAGE IS BLURRY" in warnings  # Constant color frame has 0 laplacian variance

    # Dark frame
    dark_frame = np.full((480, 640, 3), 20, dtype=np.uint8)
    _, _, dark_warnings = inference_service.quality_metrics(dark_frame)
    assert "IMAGE TOO DARK" in dark_warnings

    # Overexposed frame
    bright_frame = np.full((480, 640, 3), 240, dtype=np.uint8)
    _, _, bright_warnings = inference_service.quality_metrics(bright_frame)
    assert "IMAGE OVEREXPOSED" in bright_warnings

def test_tile_positions():
    # Length smaller than tile
    assert inference_service.tile_positions(500, 640, 0.25) == [0]
    
    # Standard length: 1920 with 640 tile and 0.25 overlap
    positions = inference_service.tile_positions(1920, 640, 0.25)
    assert len(positions) >= 3
    assert positions[0] == 0
    assert positions[-1] == 1920 - 640

def test_nms_detections():
    # Create overlapping boxes of same class
    dets = [
        [100.0, 100.0, 200.0, 200.0, 0.90, 1],
        [105.0, 102.0, 198.0, 202.0, 0.85, 1],  # Heavy overlap -> should be suppressed
        [300.0, 300.0, 400.0, 400.0, 0.88, 1],  # Distinct -> kept
        [100.0, 100.0, 200.0, 200.0, 0.82, 0],  # Different class -> kept
    ]
    suppressed = inference_service.nms_detections(dets, score_threshold=0.18, nms_threshold=0.45)
    assert len(suppressed) == 3
    # Check sorted by confidence descending
    assert suppressed[0][4] >= suppressed[1][4] >= suppressed[2][4]

def test_predict_frame_pipeline():
    test_img = np.zeros((720, 1280, 3), dtype=np.uint8)
    # Add high-contrast white beacon block
    test_img[300:360, 500:580] = 255

    res = inference_service.predict_frame(test_img)
    assert res["width"] == 1280
    assert res["height"] == 720
    assert "detections" in res
    assert "quality" in res
    assert res["inference_time_ms"] >= 0

def test_latest_frame_reader_simulation():
    reader = LatestFrameReader("demo://test_feed", is_simulated=True).start()
    time.sleep(0.15)
    ok, frame, frame_id = reader.read_latest()
    assert ok is True
    assert frame is not None
    assert frame_id >= 1
    w, h, fps = reader.get_properties()
    assert w > 0 and h > 0
    reader.stop()

def test_websocket_detection_endpoint():
    # Connect camera first
    conn_resp = client.post(
        "/api/v1/camera/connect",
        json={
            "camera_id": "CAM-WS-TEST",
            "rtsp_url": "demo://navigation_drone_feed",
            "is_simulated": True
        }
    )
    assert conn_resp.status_code == 200
    time.sleep(0.2)

    with client.websocket_connect("/ws/v1/detection/CAM-WS-TEST") as ws:
        msg = ws.receive_json()
        assert msg["camera_id"] == "CAM-WS-TEST"
        assert msg["status"] in ["CONNECTED", "LIVE", "CONNECTING"]
        assert "detections" in msg
        assert "fps" in msg
        assert "width" in msg
        assert "height" in msg

    client.post("/api/v1/camera/CAM-WS-TEST/disconnect")
