import io
import os
import json
import uuid
import tempfile
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.database import SessionLocal
from backend.app.db.models import AnalysisJob, Detection, RunwayLightResult, get_utc_now
from backend.app.services.analysis_service import analysis_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Ensures test db session is clean before/after tests."""
    yield


def test_offline_upload_validation_empty_file():
    """Empty files (0 bytes) should be rejected with HTTP 400."""
    response = client.post(
        "/api/v1/surveillance/offline/upload",
        files={"file": ("empty.mp4", b"", "video/mp4")},
        data={"analysis_type": "RUNWAY_LIGHT"},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_offline_upload_validation_unsupported_format():
    """Unsupported extensions should be rejected with HTTP 400."""
    response = client.post(
        "/api/v1/surveillance/offline/upload",
        files={"file": ("malicious.exe", b"fake binary payload", "application/octet-stream")},
        data={"analysis_type": "RUNWAY_LIGHT"},
    )
    assert response.status_code == 400
    assert "unsupported format" in response.json()["detail"].lower()


def test_offline_upload_valid_video():
    """Valid video uploads should create an AnalysisJob with RUNWAY_LIGHT type."""
    sample_content = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41"
    response = client.post(
        "/api/v1/surveillance/offline/upload",
        files={"file": ("runway_inspection_test.mp4", sample_content, "video/mp4")},
        data={"analysis_type": "RUNWAY_LIGHT"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] in ("QUEUED", "UPLOADED")
    assert data["analysis_type"] == "RUNWAY_LIGHT"

    # Verify saved in database
    with SessionLocal() as db:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == data["job_id"]).first()
        assert job is not None
        assert job.analysis_type == "RUNWAY_LIGHT"
        assert job.media_type == "VIDEO"


def test_offline_upload_valid_image():
    """Valid image uploads should create an image AnalysisJob."""
    sample_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"
    response = client.post(
        "/api/v1/surveillance/offline/upload",
        files={"file": ("runway_still.jpg", sample_jpg, "image/jpeg")},
        data={"analysis_type": "RUNWAY_LIGHT"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["media_type"] == "IMAGE"
    assert data["analysis_type"] == "RUNWAY_LIGHT"


def test_offline_job_lifecycle_endpoints():
    """Verify start, pause, resume, cancel endpoints handle jobs accurately."""
    test_id = f"test_lifecycle_{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        job = AnalysisJob(
            id=test_id,
            filename="flight_test.mp4",
            file_path="/tmp/nonexistent.mp4",
            media_type="VIDEO",
            analysis_type="RUNWAY_LIGHT",
            status="QUEUED",
        )
        db.add(job)
        db.commit()

    # Query status
    status_res = client.get(f"/api/v1/surveillance/offline/{test_id}/status")
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["job_id"] == test_id
    assert st_data["analysis_type"] == "RUNWAY_LIGHT"

    # Cancel job
    cancel_res = client.post(f"/api/v1/surveillance/offline/{test_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    with SessionLocal() as db:
        updated_job = db.query(AnalysisJob).filter(AnalysisJob.id == test_id).first()
        assert updated_job.status == "CANCELLED"

    # Verify 404 for nonexistent job
    not_found = client.get("/api/v1/surveillance/offline/job_does_not_exist_9999/status")
    assert not_found.status_code == 404


def test_offline_job_results_timestamp_calculation_and_model_isolation():
    """
    Verify get_job_results:
    1. Returns precise timestamp_seconds and timestamp_formatted (MM:SS.s).
    2. Strict model isolation: RUNWAY_LIGHT does not label detections as FOD debris.
    """
    job_id = f"test_runway_offline_{uuid.uuid4().hex[:8]}"
    fps = 30.0

    with SessionLocal() as db:
        job = AnalysisJob(
            id=job_id,
            filename="runway_approach.mp4",
            file_path="/tmp/runway_approach.mp4",
            media_type="VIDEO",
            analysis_type="RUNWAY_LIGHT",
            status="COMPLETED",
            total_frames=300,
            processed_frames=300,
            video_fps=fps,
            duration_seconds=10.0,
            elapsed_seconds=5.2,
            light_on_count=12,
            light_off_count=2,
            confirmed_faults=1,
            total_detections=14,
            avg_confidence=0.91,
            model_path="ml_engine/models/runway_light_best.pt",
        )
        db.add(job)

        # Detection 1: frame 30 -> 1.0 second -> "00:01.0"
        d1 = Detection(
            id=f"det_{uuid.uuid4().hex[:8]}",
            job_id=job_id,
            frame_number=30,
            analysis_type="RUNWAY_LIGHT",
            model_name="runway_light",
            class_name="LIGHT ON",
            confidence=0.94,
            x1=100.0,
            y1=150.0,
            x2=130.0,
            y2=180.0,
            track_id=1,
        )
        # Detection 2: frame 75 -> 2.5 seconds -> "00:02.5"
        d2 = Detection(
            id=f"det_{uuid.uuid4().hex[:8]}",
            job_id=job_id,
            frame_number=75,
            analysis_type="RUNWAY_LIGHT",
            model_name="runway_light",
            class_name="LIGHT OFF",
            confidence=0.88,
            x1=200.0,
            y1=250.0,
            x2=230.0,
            y2=280.0,
            track_id=2,
        )
        # Detection 3: frame 1815 -> 60.5 seconds -> "01:00.5"
        d3 = Detection(
            id=f"det_{uuid.uuid4().hex[:8]}",
            job_id=job_id,
            frame_number=1815,
            analysis_type="RUNWAY_LIGHT",
            model_name="runway_light",
            class_name="LIGHT ON",
            confidence=0.96,
            x1=300.0,
            y1=350.0,
            x2=330.0,
            y2=380.0,
            track_id=3,
        )
        db.add_all([d1, d2, d3])
        db.commit()

    res = client.get(f"/api/v1/surveillance/offline/{job_id}/results")
    assert res.status_code == 200
    data = res.json()

    assert data["job_id"] == job_id
    assert data["analysis_type"] == "RUNWAY_LIGHT"
    assert data["status"] == "COMPLETED"
    assert data["light_on_count"] == 12
    assert data["light_off_count"] == 2
    assert data["confirmed_faults"] == 1
    # Model isolation guarantee: fod_count must be 0 for RUNWAY_LIGHT
    assert data["fod_count"] == 0

    samples = data.get("sample_detections", [])
    assert len(samples) == 3

    # Check d1 timestamps
    assert samples[0]["frame"] == 30
    assert samples[0]["timestamp_seconds"] == 1.0
    assert samples[0]["timestamp_formatted"] == "00:01.0"
    assert samples[0]["class_name"] == "LIGHT ON"
    assert samples[0]["debris_coordinates"] is None  # Not debris

    # Check d2 timestamps
    assert samples[1]["frame"] == 75
    assert samples[1]["timestamp_seconds"] == 2.5
    assert samples[1]["timestamp_formatted"] == "00:02.5"
    assert samples[1]["class_name"] == "LIGHT OFF"
    assert samples[1]["debris_coordinates"] is None

    # Check d3 timestamps
    assert samples[2]["frame"] == 1815
    assert samples[2]["timestamp_seconds"] == 60.5
    assert samples[2]["timestamp_formatted"] == "01:00.5"
    assert samples[2]["class_name"] == "LIGHT ON"


def test_offline_results_fallback_to_runway_light_result():
    """If detection rows are not present in Detection table, verify fallback to RunwayLightResult."""
    job_id = f"test_rw_fallback_{uuid.uuid4().hex[:8]}"
    fps = 30.0

    with SessionLocal() as db:
        job = AnalysisJob(
            id=job_id,
            filename="runway_lights_grid.mp4",
            file_path="/tmp/runway_lights_grid.mp4",
            media_type="VIDEO",
            analysis_type="RUNWAY_LIGHT",
            status="COMPLETED",
            total_frames=120,
            processed_frames=120,
            video_fps=fps,
            duration_seconds=4.0,
            light_on_count=5,
            light_off_count=1,
            total_detections=6,
        )
        db.add(job)

        rl1 = RunwayLightResult(
            job_id=job_id,
            light_id="R1-C1",
            row_id=1,
            column_id=1,
            frame_id=45,
            class_name="LIGHT ON",
            confidence=0.92,
            status="ON",
            x1=50,
            y1=60,
            x2=80,
            y2=90,
            track_id=101,
            is_confirmed=True,
        )
        rl2 = RunwayLightResult(
            job_id=job_id,
            light_id="R1-C2",
            row_id=1,
            column_id=2,
            frame_id=90,
            class_name="LIGHT OFF",
            confidence=0.85,
            status="OFF",
            x1=100,
            y1=60,
            x2=130,
            y2=90,
            track_id=102,
            is_confirmed=True,
        )
        db.add_all([rl1, rl2])
        db.commit()

    res = client.get(f"/api/v1/surveillance/offline/{job_id}/results")
    assert res.status_code == 200
    data = res.json()
    samples = data.get("sample_detections", [])
    assert len(samples) == 2

    # Frame 45 at 30 fps -> 1.5 seconds -> "00:01.5"
    assert samples[0]["frame"] == 45
    assert samples[0]["timestamp_seconds"] == 1.5
    assert samples[0]["timestamp_formatted"] == "00:01.5"
    assert samples[0]["class_name"] == "LIGHT ON"

    # Frame 90 at 30 fps -> 3.0 seconds -> "00:03.0"
    assert samples[1]["frame"] == 90
    assert samples[1]["timestamp_seconds"] == 3.0
    assert samples[1]["timestamp_formatted"] == "00:03.0"
    assert samples[1]["class_name"] == "LIGHT OFF"


def test_offline_report_export_endpoints():
    """Verify CSV and JSON report export endpoints."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f_csv:
        f_csv.write(b"frame,timestamp_seconds,class_name,confidence\n30,1.0,LIGHT ON,0.94\n")
        csv_path = f_csv.name

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_json:
        f_json.write(json.dumps({"job_id": "test", "total_lights": 10}).encode("utf-8"))
        json_path = f_json.name

    job_id = f"test_reports_{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        job = AnalysisJob(
            id=job_id,
            filename="reports_video.mp4",
            file_path="/tmp/reports_video.mp4",
            media_type="VIDEO",
            analysis_type="RUNWAY_LIGHT",
            status="COMPLETED",
            report_csv_path=csv_path,
            report_json_path=json_path,
        )
        db.add(job)
        db.commit()

    # Test CSV download
    csv_res = client.get(f"/api/v1/surveillance/offline/{job_id}/report?format=csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert "LIGHT ON" in csv_res.text

    # Test JSON download
    json_res = client.get(f"/api/v1/surveillance/offline/{job_id}/report?format=json")
    assert json_res.status_code == 200
    assert json_res.json()["total_lights"] == 10

    # Cleanup temp files
    try:
        os.remove(csv_path)
        os.remove(json_path)
    except Exception:
        pass


def test_offline_jobs_listing():
    """Verify list_offline_jobs endpoint filters and limits correctly."""
    res = client.get("/api/v1/surveillance/offline/jobs?limit=10&analysis_type=RUNWAY_LIGHT")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    for j in data:
        if j.get("analysis_type"):
            assert j["analysis_type"] == "RUNWAY_LIGHT"
