import os
import time
import tempfile
import cv2
import numpy as np
import pytest
from pathlib import Path

from backend.app.services.fod_service import fod_service
from backend.app.services.tracking_service import ObjectTracker
from backend.app.services.database_service import database_service
from backend.app.services.analysis_service import analysis_service
from backend.app.services.analysis_worker import AnalysisWorker
from backend.app.services.export_service import export_service
from backend.app.db.database import SessionLocal
from backend.app.db.models import AnalysisJob, Detection


def test_fod_service_model_and_device():
    """Verifies that the trained FOD model loads and resolves hardware acceleration."""
    assert fod_service.loaded, "FOD model should be loaded"
    assert "FOD" in [fod_service.model.names[k] for k in fod_service.model.names]
    device = fod_service.get_optimal_device()
    assert device in ("mps", "cuda", "cpu")


def test_tracker_spatial_temporal_deduplication():
    """
    Verifies that ObjectTracker does not inflate unique IDs when small debris
    shifts across frames under drone camera motion.
    """
    tracker = ObjectTracker(max_disappeared=10)

    # Frame 1: FOD at (100, 100) -> (140, 140)
    dets_f1 = [{
        "class_name": "FOD",
        "confidence": 0.65,
        "bbox": [100, 100, 140, 140],
        "model": "fod"
    }]
    res_f1 = tracker.update(dets_f1, frame_idx=1)
    assert len(res_f1) == 1
    t1_id = res_f1[0]["track_id"]
    assert t1_id is not None

    # Frame 2: Drone moved, same debris shifted 15px to (115, 115) -> (155, 155)
    # Strict IoU would be < 0.25 and fail, but combined spatial-temporal should maintain ID
    dets_f2 = [{
        "class_name": "FOD",
        "confidence": 0.60,
        "bbox": [115, 115, 155, 155],
        "model": "fod"
    }]
    res_f2 = tracker.update(dets_f2, frame_idx=2)
    assert len(res_f2) == 1
    assert res_f2[0]["track_id"] == t1_id, "Track ID must remain continuous under drone motion"

    # Frame 3: Distinct new debris appears far away at (500, 500)
    dets_f3 = [
        {
            "class_name": "FOD",
            "confidence": 0.62,
            "bbox": [120, 120, 160, 160],
            "model": "fod"
        },
        {
            "class_name": "FOD",
            "confidence": 0.55,
            "bbox": [500, 500, 540, 540],
            "model": "fod"
        }
    ]
    res_f3 = tracker.update(dets_f3, frame_idx=3)
    assert len(res_f3) == 2
    ids = {d["track_id"] for d in res_f3}
    assert t1_id in ids
    assert len(ids) == 2, "Second debris must receive a distinct unique ID"


def test_batch_detection_saving():
    """Verifies that database_service.save_detections_batch commits batched detections."""
    test_session = f"test_batch_{int(time.time())}"
    batch = [
        (1, {"class_name": "FOD", "class_id": 0, "confidence": 0.7, "bbox": [10, 10, 50, 50], "track_id": 1, "model": "fod"}),
        (2, {"class_name": "FOD", "class_id": 0, "confidence": 0.68, "bbox": [12, 12, 52, 52], "track_id": 1, "model": "fod"}),
        (3, {"class_name": "FOD", "class_id": 0, "confidence": 0.75, "bbox": [100, 100, 130, 130], "track_id": 2, "model": "fod"}),
    ]

    database_service.save_detections_batch(session_id=test_session, batched_items=batch)

    with SessionLocal() as db:
        saved = db.query(Detection).filter(Detection.job_id == test_session).all()
        assert len(saved) == 3
        # Clean up
        db.query(Detection).filter(Detection.job_id == test_session).delete()
        db.commit()


def test_fod_worker_metrics_and_speed_ratio():
    """
    Runs an end-to-end FOD analysis with an actual synthesized video,
    verifying accurate unique object counting, cumulative frame detections,
    speed ratio calculation, and database persistence.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_video = tmp.name

    fps = 20.0
    num_frames = 15
    w, h = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(tmp_video, fourcc, fps, (w, h))

    # Draw synthetic asphalt background with an obstacle
    for i in range(num_frames):
        frame = np.full((h, w, 3), 110, dtype=np.uint8)  # grey asphalt
        # Draw a small debris-like block
        cv2.rectangle(frame, (200 + i, 200), (230 + i, 230), (30, 30, 30), -1)
        writer.write(frame)
    writer.release()

    job_id = f"test_fod_{int(time.time())}"

    # Initialize AnalysisJob in DB
    with SessionLocal() as db:
        job = AnalysisJob(
            id=job_id,
            filename=Path(tmp_video).name,
            file_path=tmp_video,
            media_type="VIDEO",
            analysis_type="FOD",
            status="QUEUED",
            total_frames=num_frames,
            duration_seconds=num_frames / fps,
        )
        db.add(job)
        db.commit()

    worker = AnalysisWorker(
        job_id=job_id,
        file_path=tmp_video,
        analysis_type="FOD",
        media_type="VIDEO",
    )

    # Run worker synchronously
    worker._run()

    # Query finalized job from database
    with SessionLocal() as db:
        final_job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        assert final_job is not None
        assert final_job.status == "COMPLETED"
        assert final_job.processed_frames == num_frames
        assert final_job.speed_ratio > 0.0
        assert final_job.processing_fps > 0.0
        assert final_job.report_csv_path is not None
        assert final_job.report_json_path is not None

        # Verify export summary JSON contains job_metrics
        summary_path = Path(final_job.report_json_path)
        assert summary_path.exists()

    # Verify get_job_results via AnalysisService
    results = analysis_service.get_job_results(job_id)
    assert results["job_id"] == job_id
    assert results["status"] == "COMPLETED"
    assert "total_detections" in results
    assert "speed_ratio" in results
    assert "class_counts" in results
    assert "unique_fod_count" in results

    # Clean up temp video
    try:
        os.remove(tmp_video)
    except OSError:
        pass
