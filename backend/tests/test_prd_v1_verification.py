import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.model_verifier import model_verifier
from backend.app.services.analysis_service import analysis_service
from backend.app.db.database import SessionLocal
from backend.app.db.models import AnalysisJob

client = TestClient(app)


def test_model_verifier_manifest_and_checksums():
    """FR-01: Cryptographic model verification and manifest integrity."""
    nav_info = model_verifier.verify_model("NAVIGATION")
    assert nav_info["is_valid"] is True
    assert nav_info["num_classes"] == 80
    assert nav_info["native_imgsz"] == 640
    assert len(nav_info["sha256"]) == 64
    assert nav_info["suitability_status"] == "VALIDATED_COCO_GENERAL"

    fod_info = model_verifier.verify_model("FOD")
    assert fod_info["is_valid"] is True
    assert fod_info["num_classes"] == 1
    assert fod_info["native_imgsz"] == 1024
    assert len(fod_info["sha256"]) == 64
    assert fod_info["suitability_status"] == "VALIDATED_FOD_SPECIFIC"

    light_info = model_verifier.verify_model("RUNWAY_LIGHT")
    assert light_info["is_valid"] is True
    assert light_info["num_classes"] == 2
    assert light_info["native_imgsz"] == 640
    assert len(light_info["sha256"]) == 64
    assert light_info["suitability_status"] == "VALIDATED_RUNWAY_LIGHT_SPECIFIC"


def test_models_status_api_provenance():
    """FR-01 & Section 29: Models status endpoint exposes verification metadata."""
    res = client.get("/api/v1/models/status")
    assert res.status_code == 200
    data = res.json()

    assert "navigation" in data
    assert "fod" in data
    assert "runway_light" in data

    assert data["navigation"]["sha256"] is not None
    assert data["navigation"]["native_imgsz"] == 640
    assert data["navigation"]["suitability_status"] == "VALIDATED_COCO_GENERAL"

    assert data["fod"]["sha256"] is not None
    assert data["fod"]["native_imgsz"] == 1024
    assert data["fod"]["suitability_status"] == "VALIDATED_FOD_SPECIFIC"

    assert data["runway_light"]["sha256"] is not None
    assert data["runway_light"]["native_imgsz"] == 640
    assert data["runway_light"]["suitability_status"] == "VALIDATED_RUNWAY_LIGHT_SPECIFIC"


def test_job_creation_records_model_provenance():
    """FR-01: Job creation records model version, path, and confidence threshold."""
    # Test video job creation
    dummy_bytes = b"fake video header data for testing"
    vjob = analysis_service.create_video_job("test_provenance.mp4", dummy_bytes, analysis_type="FOD")
    assert vjob["status"] == "QUEUED"
    assert vjob["outcome_status"] == "QUEUED"
    assert vjob["model_path"] is not None
    assert vjob["model_version"] is not None
    assert vjob["confidence_threshold"] == pytest.approx(0.18, 0.01)

    # Query DB to verify persistence
    with SessionLocal() as db:
        db_job = db.query(AnalysisJob).filter(AnalysisJob.id == vjob["id"]).first()
        assert db_job is not None
        assert db_job.model_version is not None
        assert db_job.confidence_threshold == pytest.approx(0.18, 0.01)
        assert db_job.outcome_status == "QUEUED"


def test_status_transparency_invariants():
    """Section 9.2: Differentiate COMPLETED_WITH_DETECTIONS vs COMPLETED_NO_DETECTIONS."""
    with SessionLocal() as db:
        # Create a job with 0 detections
        job_empty = AnalysisJob(
            id="test_transparency_0",
            filename="empty.mp4",
            file_path="/dummy/path/empty.mp4",
            media_type="VIDEO",
            analysis_type="RUNWAY_LIGHT",
            status="COMPLETED",
            outcome_status="COMPLETED_NO_DETECTIONS",
            total_detections=0,
            light_on_count=0,
            light_off_count=0,
            unknown_light_count=0,
        )
        # Create a job with detections
        job_dets = AnalysisJob(
            id="test_transparency_1",
            filename="lights.mp4",
            file_path="/dummy/path/lights.mp4",
            media_type="VIDEO",
            analysis_type="RUNWAY_LIGHT",
            status="COMPLETED",
            outcome_status="COMPLETED_WITH_DETECTIONS",
            total_detections=15,
            light_on_count=12,
            light_off_count=3,
            unknown_light_count=0,
        )
        db.merge(job_empty)
        db.merge(job_dets)
        db.commit()

    res_empty = client.get("/api/v1/analysis/test_transparency_0")
    assert res_empty.status_code == 200
    data_empty = res_empty.json()
    assert data_empty["status"] == "COMPLETED"
    assert data_empty["outcome_status"] == "COMPLETED_NO_DETECTIONS"

    res_dets = client.get("/api/v1/analysis/test_transparency_1")
    assert res_dets.status_code == 200
    data_dets = res_dets.json()
    assert data_dets["status"] == "COMPLETED"
    assert data_dets["outcome_status"] == "COMPLETED_WITH_DETECTIONS"
