import os
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.navigation_service import navigation_service
from backend.app.services.fod_service import fod_service
from backend.app.services.runway_light_service import runway_light_service
from backend.app.services.database_service import database_service

client = TestClient(app)

REAL_RUNWAY_IMG = "valid/images/2025_12_09_20_03_42_mp4-0034_jpg.rf.c8297d35ce70d808ca1bf45afba04f14.jpg"
REAL_DEMO_VIDEO = "data/videos/runway_demo.mp4"


def test_models_loaded_and_isolated():
    """Verify that all three models are loaded from disk with real weights."""
    assert navigation_service.loaded is True
    assert fod_service.loaded is True
    assert runway_light_service.loaded is True

    # Verify distinct weights
    assert "navigation_best.pt" in str(navigation_service.model_path)
    assert "FOD_Karhtikeyan.pt" in str(fod_service.model_path)
    assert "runway_light_best.pt" in str(runway_light_service.model_path)


def test_real_image_analysis_navigation():
    """Test full upload -> start -> results lifecycle for Navigation on real image."""
    assert os.path.exists(REAL_RUNWAY_IMG)
    with open(REAL_RUNWAY_IMG, "rb") as f:
        img_bytes = f.read()

    # Upload via /api/v1/navigation/upload
    resp = client.post(
        "/api/v1/navigation/upload",
        files={"file": ("nav_test.jpg", img_bytes, "image/jpeg")}
    )
    assert resp.status_code == 200
    data = resp.json()
    job_id = data["job_id"]
    assert data["analysis_type"] == "NAVIGATION"
    assert data["media_type"] == "IMAGE"

    # Start analysis
    start_resp = client.post(f"/api/v1/navigation/{job_id}/start")
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["status"] == "COMPLETED"

    # Fetch results
    res_resp = client.get(f"/api/v1/navigation/{job_id}/results")
    assert res_resp.status_code == 200
    res = res_resp.json()
    assert res["analysis_type"] == "NAVIGATION"
    assert res["status"] == "COMPLETED"
    # Module isolation: non-navigation counts must be 0
    assert res["fod_count"] == 0
    assert res["light_on_count"] == 0
    assert res["light_off_count"] == 0
    assert res["confirmed_faults"] == 0

    # Verify annotated media exists and can be retrieved
    annotated_resp = client.get(f"/api/v1/analysis/{job_id}/video")
    assert annotated_resp.status_code == 200
    assert len(annotated_resp.content) > 0


def test_real_image_analysis_fod():
    """Test full upload -> start -> results lifecycle for FOD on real image."""
    assert os.path.exists(REAL_RUNWAY_IMG)
    with open(REAL_RUNWAY_IMG, "rb") as f:
        img_bytes = f.read()

    # Upload via /api/v1/fod/upload
    resp = client.post(
        "/api/v1/fod/upload",
        files={"file": ("fod_test.jpg", img_bytes, "image/jpeg")}
    )
    assert resp.status_code == 200
    data = resp.json()
    job_id = data["job_id"]
    assert data["analysis_type"] == "FOD"
    assert data["media_type"] == "IMAGE"

    # Start analysis
    start_resp = client.post(f"/api/v1/fod/{job_id}/start")
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["status"] == "COMPLETED"

    # Fetch results
    res_resp = client.get(f"/api/v1/fod/{job_id}/results")
    assert res_resp.status_code == 200
    res = res_resp.json()
    assert res["analysis_type"] == "FOD"
    assert res["status"] == "COMPLETED"
    # Module isolation: non-FOD counts must be 0
    assert res["nav_count"] == 0
    assert res["light_on_count"] == 0
    assert res["light_off_count"] == 0
    assert res["confirmed_faults"] == 0

    # Verify annotated media exists and can be retrieved
    annotated_resp = client.get(f"/api/v1/analysis/{job_id}/video")
    assert annotated_resp.status_code == 200
    assert len(annotated_resp.content) > 0


def test_real_image_analysis_runway_light():
    """Test full upload -> start -> results lifecycle for Runway Light on real runway image."""
    assert os.path.exists(REAL_RUNWAY_IMG)
    with open(REAL_RUNWAY_IMG, "rb") as f:
        img_bytes = f.read()

    # Upload via /api/v1/runway-light/upload
    resp = client.post(
        "/api/v1/runway-light/upload",
        files={"file": ("runway_test.jpg", img_bytes, "image/jpeg")}
    )
    assert resp.status_code == 200
    data = resp.json()
    job_id = data["job_id"]
    assert data["analysis_type"] == "RUNWAY_LIGHT"
    assert data["media_type"] == "IMAGE"

    # Start analysis
    start_resp = client.post(f"/api/v1/runway-light/{job_id}/start")
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["status"] == "COMPLETED"

    # Fetch results
    res_resp = client.get(f"/api/v1/runway-light/{job_id}/results")
    assert res_resp.status_code == 200
    res = res_resp.json()
    assert res["analysis_type"] == "RUNWAY_LIGHT"
    assert res["status"] == "COMPLETED"
    # Module isolation: non-runway counts must be 0
    assert res["nav_count"] == 0
    assert res["fod_count"] == 0

    # Ensure real predictions were detected (the sample image has ~8 runway lights)
    assert res["light_on_count"] > 0 or res["light_off_count"] > 0
    assert "row_results" in res
    assert isinstance(res["row_results"], list)

    # Fetch dedicated summary
    sum_resp = client.get(f"/api/v1/runway-light/{job_id}/summary")
    assert sum_resp.status_code == 200
    summary = sum_resp.json()
    assert summary["job_id"] == job_id
    assert summary["total_lights"] >= 0
    assert isinstance(summary["matrix"], list)

    # Verify annotated media exists and can be retrieved
    annotated_resp = client.get(f"/api/v1/analysis/{job_id}/video")
    assert annotated_resp.status_code == 200
    assert len(annotated_resp.content) > 0


def test_video_analysis_lifecycle():
    """Test full upload -> start -> progress -> wait -> completion lifecycle on real video."""
    assert os.path.exists(REAL_DEMO_VIDEO)
    with open(REAL_DEMO_VIDEO, "rb") as f:
        vid_bytes = f.read()

    # Upload video to /api/v1/analysis/videos with RUNWAY_LIGHT
    resp = client.post(
        "/api/v1/analysis/videos",
        files={"file": ("test_runway_demo.mp4", vid_bytes, "video/mp4")},
        data={"analysis_type": "RUNWAY_LIGHT"}
    )
    assert resp.status_code == 200
    data = resp.json()
    job_id = data["job_id"]
    assert data["analysis_type"] == "RUNWAY_LIGHT"
    assert data["status"] == "QUEUED"
    assert data["total_frames"] > 0

    # Start analysis
    start_resp = client.post(f"/api/v1/analysis/{job_id}/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "ANALYZING"

    # Poll status until COMPLETED (up to 30 seconds)
    completed = False
    for _ in range(60):
        time.sleep(0.5)
        st_resp = client.get(f"/api/v1/analysis/{job_id}")
        assert st_resp.status_code == 200
        st = st_resp.json()
        if st["status"] == "COMPLETED":
            completed = True
            break
        elif st["status"] == "FAILED":
            pytest.fail(f"Video analysis failed: {st.get('error_message')}")

    assert completed is True

    # Check results
    res_resp = client.get(f"/api/v1/analysis/{job_id}/results")
    assert res_resp.status_code == 200
    res = res_resp.json()
    assert res["status"] == "COMPLETED"
    assert res["processed_frames"] > 0
    assert res["analysis_type"] == "RUNWAY_LIGHT"

    # Test report export CSV
    csv_resp = client.get(f"/api/v1/analysis/{job_id}/report?format=csv")
    assert csv_resp.status_code == 200
    assert b"frame,time_sec,track_id" in csv_resp.content

    # Test report export JSON
    json_resp = client.get(f"/api/v1/analysis/{job_id}/report?format=json")
    assert json_resp.status_code == 200
    assert b"RUNWAY LIGHT FAULT ANALYSIS REPORT" in json_resp.content

    # Test annotated video retrieval (HTTP 200 and range 206)
    vid_resp = client.get(f"/api/v1/analysis/{job_id}/video")
    assert vid_resp.status_code == 200
    assert len(vid_resp.content) > 0

    range_resp = client.get(f"/api/v1/analysis/{job_id}/video", headers={"Range": "bytes=0-1023"})
    assert range_resp.status_code == 206
    assert len(range_resp.content) == 1024


def test_surveillance_endpoints():
    """Verify live and offline surveillance API endpoints."""
    # Create a live surveillance session
    start_resp = client.post(
        "/api/v1/surveillance/live/start",
        json={"source_type": "WEBCAM", "source_url": "0", "model": "RUNWAY_LIGHT"}
    )
    assert start_resp.status_code == 200
    sess = start_resp.json()
    session_id = sess["session_id"]
    assert sess["status"] in ("CONNECTING", "CONNECTED", "ACTIVE")

    # Fetch status
    st_resp = client.get(f"/api/v1/surveillance/live/{session_id}/status")
    assert st_resp.status_code == 200
    assert st_resp.json()["session_id"] == session_id

    # Stop session
    stop_resp = client.post(f"/api/v1/surveillance/live/{session_id}/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["status"] in ("STOPPED", "DISCONNECTED")
