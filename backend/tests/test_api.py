import io
from fastapi.testclient import TestClient
from PIL import Image
from backend.app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "drone-navigation-api"

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "healthy"
    assert "database" in data
    assert "model" in data

def test_drones_list():
    client.post("/api/v1/drones", json={"name": "Garuda Hawk Test", "serial_number": "GH-TEST-001"})
    response = client.get("/api/v1/drones")
    assert response.status_code == 200
    drones = response.json()
    assert isinstance(drones, list)
    assert len(drones) > 0

def test_missions_list():
    client.post("/api/v1/missions", json={"name": "Runway Survey Test", "description": "Verification flight"})
    response = client.get("/api/v1/missions")
    assert response.status_code == 200
    missions = response.json()
    assert isinstance(missions, list)
    assert len(missions) > 0


def test_detection_image():
    # Generate in-memory 512x512 RGB test image
    img = Image.new("RGB", (512, 512), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    response = client.post(
        "/api/v1/detection/image",
        files={"file": ("test_optical_beacon.jpg", buf, "image/jpeg")},
        data={"confidence": 0.40}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "processing_time_ms" in data
    assert "detections" in data
    assert isinstance(data["detections"], list)

def test_command_centre_status():
    response = client.get("/api/v1/command-centre/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["system_health"] == "OPTIMAL"
    assert "drone_connected" in data
    assert "connection_status" in data
    assert "models" in data
    assert "camera" in data

def test_command_centre_telemetry_disconnected():
    response = client.get("/api/v1/command-centre/telemetry")
    assert response.status_code == 200
    data = response.json()
    # Initially no drone is connected
    assert data["connected"] is False
    assert data["telemetry"] is None
    assert "DRONE NOT CONNECTED" in data["message"]

def test_command_centre_recent_missions():
    response = client.get("/api/v1/command-centre/recent-missions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_mission_report():
    # First get or create mission
    missions_res = client.get("/api/v1/missions")
    assert missions_res.status_code == 200
    missions = missions_res.json()
    assert len(missions) > 0
    m_id = missions[0]["id"]
    report_res = client.get(f"/api/v1/missions/{m_id}/report")
    assert report_res.status_code == 200
    report = report_res.json()
    assert report["mission_id"] == m_id
    assert "name" in report
    assert "status" in report

def test_analysis_job_results_and_media_endpoints():
    # Create an image analysis job
    import io
    file_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\x00" * 100
    upload_res = client.post(
        "/api/v1/analysis/images",
        files={"file": ("test_audit_img.jpg", io.BytesIO(file_content), "image/jpeg")},
        data={"analysis_type": "FOD"}
    )
    assert upload_res.status_code == 200
    job_data = upload_res.json()
    job_id = job_data["job_id"]

    # Retrieve results for this job
    results_res = client.get(f"/api/v1/analysis/{job_id}/results")
    assert results_res.status_code == 200
    res_data = results_res.json()
    assert res_data["job_id"] == job_id
    assert res_data["analysis_type"] == "FOD"
    assert "created_at" in res_data
    assert "sample_detections" in res_data

    # Check original media endpoint
    orig_res = client.get(f"/api/v1/analysis/{job_id}/original")
    assert orig_res.status_code == 200
    assert orig_res.headers["content-type"] == "image/jpeg"

    # List jobs
    jobs_res = client.get("/api/v1/analysis/jobs/all")
    assert jobs_res.status_code == 200
    assert any(j["id"] == job_id for j in jobs_res.json())


def test_surveillance_live_endpoints():
    # 1. Validation test - missing url
    bad_res = client.post("/api/v1/surveillance/live/start", json={})
    assert bad_res.status_code == 400

    # 2. Start simulated/demo live surveillance
    start_res = client.post(
        "/api/v1/surveillance/live/start",
        json={
            "stream_url": "demo://optical_runway_feed",
            "camera_name": "Test Runway Optical",
            "model_type": "NAVIGATION",
            "is_simulated": True,
        }
    )
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert start_data["success"] is True
    session_id = start_data["session_id"]

    # 3. Get status
    status_res = client.get(f"/api/v1/surveillance/live/{session_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "status" in status_data

    # 4. List active sessions
    sessions_res = client.get("/api/v1/surveillance/live/sessions")
    assert sessions_res.status_code == 200
    assert any(s["session_id"] == session_id for s in sessions_res.json())

    # 5. Stop live surveillance
    stop_res = client.post("/api/v1/surveillance/live/stop", json={"session_id": session_id})
    assert stop_res.status_code == 200
    assert stop_res.json()["success"] is True


def test_surveillance_offline_endpoints():
    import io
    file_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\x00" * 100
    upload_res = client.post(
        "/api/v1/surveillance/offline/upload",
        files={"file": ("test_surveillance.jpg", io.BytesIO(file_content), "image/jpeg")},
        data={"analysis_type": "NAVIGATION"}
    )
    assert upload_res.status_code == 200
    job_data = upload_res.json()
    job_id = job_data["job_id"]

    # Get status
    status_res = client.get(f"/api/v1/surveillance/offline/{job_id}/status")
    assert status_res.status_code == 200

    # Get results
    results_res = client.get(f"/api/v1/surveillance/offline/{job_id}/results")
    assert results_res.status_code == 200
    assert results_res.json()["job_id"] == job_id

    # Get original media
    orig_res = client.get(f"/api/v1/surveillance/offline/{job_id}/original")
    assert orig_res.status_code == 200

    # List offline jobs
    list_res = client.get("/api/v1/surveillance/offline/jobs")
    assert list_res.status_code == 200
    assert any(j["id"] == job_id for j in list_res.json())


