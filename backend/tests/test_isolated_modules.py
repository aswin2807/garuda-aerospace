import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app
from backend.app.services.analysis_service import analysis_service

client = TestClient(app)


def create_test_image_bytes():
    img = Image.new("RGB", (640, 640), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_navigation_isolated_endpoint():
    """Test /api/v1/navigation/upload and isolated execution."""
    img_bytes = create_test_image_bytes()
    resp = client.post(
        "/api/v1/navigation/upload",
        files={"file": ("test_nav.jpg", img_bytes, "image/jpeg")}
    )
    assert resp.status_code == 200
    data = resp.json()
    job_id = data["job_id"]
    assert data["analysis_type"] == "NAVIGATION"

    # Start analysis
    start_resp = client.post(f"/api/v1/navigation/{job_id}/start")
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["analysis_type"] == "NAVIGATION"
    assert start_data["status"] == "COMPLETED"

    # Fetch status
    status_resp = client.get(f"/api/v1/navigation/{job_id}")
    assert status_resp.status_code == 200
    st = status_resp.json()
    assert st["analysis_type"] == "NAVIGATION"
    assert st["fod_count"] == 0
    assert st["light_on_count"] == 0
    assert st["light_off_count"] == 0
    assert st["confirmed_faults"] == 0

    # Fetch results
    res_resp = client.get(f"/api/v1/navigation/{job_id}/results")
    assert res_resp.status_code == 200
    res = res_resp.json()
    assert res["analysis_type"] == "NAVIGATION"
    assert res["fod_count"] == 0
    assert res["light_on_count"] == 0
    assert res["light_off_count"] == 0
    assert res["confirmed_faults"] == 0

    # History
    hist_resp = client.get("/api/v1/navigation/history")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert any(j["id"] == job_id for j in hist)


def test_fod_isolated_endpoint():
    """Test /api/v1/fod/upload and isolated execution."""
    img_bytes = create_test_image_bytes()
    resp = client.post(
        "/api/v1/fod/upload",
        files={"file": ("test_fod.jpg", img_bytes, "image/jpeg")}
    )
    assert resp.status_code == 200
    data = resp.json()
    job_id = data["job_id"]
    assert data["analysis_type"] == "FOD"

    # Start analysis
    start_resp = client.post(f"/api/v1/fod/{job_id}/start")
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["analysis_type"] == "FOD"
    assert start_data["status"] == "COMPLETED"

    # Fetch results
    res_resp = client.get(f"/api/v1/fod/{job_id}/results")
    assert res_resp.status_code == 200
    res = res_resp.json()
    assert res["analysis_type"] == "FOD"
    assert res["nav_count"] == 0
    assert res["light_on_count"] == 0
    assert res["light_off_count"] == 0
    assert res["confirmed_faults"] == 0

    # History
    hist_resp = client.get("/api/v1/fod/history")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert any(j["id"] == job_id for j in hist)


def test_runway_light_isolated_endpoint():
    """Test /api/v1/runway-light/upload and isolated execution with row results."""
    img_bytes = create_test_image_bytes()
    resp = client.post(
        "/api/v1/runway-light/upload",
        files={"file": ("test_runway.jpg", img_bytes, "image/jpeg")}
    )
    assert resp.status_code == 200
    data = resp.json()
    job_id = data["job_id"]
    assert data["analysis_type"] == "RUNWAY_LIGHT"

    # Start analysis
    start_resp = client.post(f"/api/v1/runway-light/{job_id}/start")
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["analysis_type"] == "RUNWAY_LIGHT"
    assert start_data["status"] == "COMPLETED"

    # Fetch results
    res_resp = client.get(f"/api/v1/runway-light/{job_id}/results")
    assert res_resp.status_code == 200
    res = res_resp.json()
    assert res["analysis_type"] == "RUNWAY_LIGHT"
    assert res["nav_count"] == 0
    assert res["fod_count"] == 0
    assert "row_results" in res
    assert isinstance(res["row_results"], list)

    # History
    hist_resp = client.get("/api/v1/runway-light/history")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert any(j["id"] == job_id for j in hist)


def test_analysis_upload_with_explicit_type():
    """Test /api/v1/analysis/upload with explicit analysis_type form parameter."""
    img_bytes = create_test_image_bytes()
    resp = client.post(
        "/api/v1/analysis/upload",
        files={"file": ("test_universal.jpg", img_bytes, "image/jpeg")},
        data={"analysis_type": "FOD"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_type"] == "FOD"
