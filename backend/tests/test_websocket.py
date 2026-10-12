import io
import json
import base64
from fastapi.testclient import TestClient
from PIL import Image
from backend.app.main import app

def test_websocket_detection():
    client = TestClient(app)
    
    # Generate test image base64
    img = Image.new("RGB", (512, 512), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")

    with client.websocket_connect("/ws/v1/detection/DR-01") as websocket:
        # Send frame payload
        websocket.send_text(json.dumps({
            "image": b64_data,
            "confidence_threshold": 0.40
        }))

        # Receive detection result
        data = websocket.receive_text()
        result = json.loads(data)

        assert result["type"] == "detection"
        assert result["drone_id"] == "DR-01"
        assert "detections" in result
        assert "inference_time_ms" in result
        assert result["width"] == 512
        assert result["height"] == 512

def test_websocket_ping_pong():
    client = TestClient(app)
    with client.websocket_connect("/ws/v1/detection/DR-01") as websocket:
        websocket.send_text(json.dumps({"type": "ping"}))
        data = websocket.receive_text()
        result = json.loads(data)
        assert result["type"] == "pong"
