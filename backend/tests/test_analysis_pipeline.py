import io
import os
import tempfile
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app
from backend.app.services.analysis_service import analysis_service

client = TestClient(app)


def create_test_video_bytes(num_frames: int = 6, width: int = 160, height: int = 120, fps: float = 10.0) -> bytes:
    """Generates a small valid MP4 video in memory."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Draw a small circle
        cv2.circle(frame, (width // 2, height // 2), 15 + i * 2, (200, 255, 100), -1)
        out.write(frame)
    out.release()

    with open(tmp_path, "rb") as f:
        data = f.read()

    try:
        os.remove(tmp_path)
    except OSError:
        pass

    return data


def create_test_image_bytes(width: int = 256, height: int = 256) -> bytes:
    """Generates a small test JPEG image."""
    img = Image.new("RGB", (width, height), color=(60, 120, 180))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_upload_video_invalid_format():
    """Rejects unsupported video format with 400 Bad Request."""
    response = client.post(
        "/api/v1/analysis/videos",
        files={"file": ("test.txt", b"not a video", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported video format" in response.json()["detail"]


def test_upload_video_empty_file():
    """Rejects empty video upload."""
    response = client.post(
        "/api/v1/analysis/videos",
        files={"file": ("empty.mp4", b"", "video/mp4")},
    )
    assert response.status_code == 400
    assert "Empty video file" in response.json()["detail"]


def test_upload_video_success_paused_on_upload():
    """
    PRD Section 7: Video must remain PAUSED on upload.
    Metadata (total frames, fps, duration) is extracted immediately.
    """
    video_bytes = create_test_video_bytes(num_frames=6, fps=10.0)
    response = client.post(
        "/api/v1/analysis/videos",
        files={"file": ("flight_test.mp4", video_bytes, "video/mp4")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("QUEUED", "UPLOADED")
    assert data["media_type"] == "VIDEO"
    assert data["total_frames"] == 6
    assert data["video_fps"] == pytest.approx(10.0, rel=0.1)
    assert "job_id" in data
    assert data["job_id"].startswith("analysis_")


def test_upload_image_invalid_and_success():
    """Tests image upload validation and job initialization."""
    # Invalid extension
    res_bad = client.post(
        "/api/v1/analysis/images",
        files={"file": ("photo.pdf", b"fake pdf", "application/pdf")},
    )
    assert res_bad.status_code == 400

    # Valid image
    img_bytes = create_test_image_bytes()
    res_good = client.post(
        "/api/v1/analysis/images",
        files={"file": ("aerial_test.jpg", img_bytes, "image/jpeg")},
    )
    assert res_good.status_code == 200
    data = res_good.json()
    assert data["status"] in ("QUEUED", "UPLOADED")
    assert data["media_type"] == "IMAGE"
    assert data["total_frames"] == 1
    assert "job_id" in data


def test_image_analysis_execution_and_results():
    """
    Tests running static image analysis with YOLO models.
    Verifies inference completes, detections are stored, and results are returned.
    """
    img_bytes = create_test_image_bytes()
    upload_res = client.post(
        "/api/v1/analysis/images",
        files={"file": ("runway_photo.jpg", img_bytes, "image/jpeg")},
    )
    job_id = upload_res.json()["job_id"]

    # Start image analysis
    start_res = client.post(f"/api/v1/analysis/{job_id}/start")
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert start_data["status"] == "COMPLETED"

    # Query job status
    status_res = client.get(f"/api/v1/analysis/{job_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["status"] == "COMPLETED"
    assert status_data["processed_frames"] == 1
    assert status_data["progress"] == 100.0

    # Query full results
    results_res = client.get(f"/api/v1/analysis/{job_id}/results")
    assert results_res.status_code == 200
    results_data = results_res.json()
    assert results_data["status"] == "COMPLETED"
    assert "nav_count" in results_data
    assert "fod_count" in results_data
    assert "light_on_count" in results_data
    assert "light_off_count" in results_data


def test_video_analysis_lifecycle_pause_resume_cancel():
    """
    Tests video job start, pause, resume, and cancel lifecycles (PRD Section 13, 14).
    """
    video_bytes = create_test_video_bytes(num_frames=20, fps=10.0)
    upload_res = client.post(
        "/api/v1/analysis/videos",
        files={"file": ("long_flight.mp4", video_bytes, "video/mp4")},
    )
    job_id = upload_res.json()["job_id"]

    # Start analysis
    start_res = client.post(f"/api/v1/analysis/{job_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "ANALYZING"

    # Pause analysis
    pause_res = client.post(f"/api/v1/analysis/{job_id}/pause")
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"

    # Resume analysis
    resume_res = client.post(f"/api/v1/analysis/{job_id}/resume")
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "ANALYZING"

    # Cancel analysis
    cancel_res = client.post(f"/api/v1/analysis/{job_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"


def test_analysis_nonexistent_job():
    """Returns 404 for non-existent job ID."""
    res = client.get("/api/v1/analysis/nonexistent_job_123")
    assert res.status_code == 404

    res_results = client.get("/api/v1/analysis/nonexistent_job_123/results")
    assert res_results.status_code == 404


def test_list_all_analysis_jobs():
    """Verifies listing recent jobs returns a list."""
    res = client.get("/api/v1/analysis/jobs/all")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_analysis_websocket_progress():
    """
    PRD Section 39: WebSocket connection to /ws/v1/analysis/{job_id}
    receives initial analysis status.
    """
    img_bytes = create_test_image_bytes()
    upload_res = client.post(
        "/api/v1/analysis/images",
        files={"file": ("ws_test.jpg", img_bytes, "image/jpeg")},
    )
    job_id = upload_res.json()["job_id"]

    with client.websocket_connect(f"/ws/v1/analysis/{job_id}") as websocket:
        msg = websocket.receive_json()
        assert msg["type"] == "analysis_progress"
        assert msg["job_id"] == job_id
        assert msg["media_type"] == "IMAGE"

        # Send heartbeat ping
        websocket.send_json({"type": "ping"})
        pong = websocket.receive_json()
        assert pong["type"] == "pong"
