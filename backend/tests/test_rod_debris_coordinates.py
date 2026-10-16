import pytest
import math
import time

from backend.app.services.debris_coordinate_service import debris_coordinate_service
from backend.app.services.database_service import database_service
from backend.app.db.database import SessionLocal
from backend.app.db.models import Detection, DetectionEvent
from backend.app.services.central_results_service import central_results_service


def test_representative_ground_contact_point():
    """
    FR-02 & FR-04: Ground contact point for objects lying flat on runway surface
    must be the bottom-center of the bounding box ((x1+x2)/2, y2).
    """
    # Test list format [x1, y1, x2, y2]
    bbox_list = [100.0, 200.0, 300.0, 400.0]
    px, py = debris_coordinate_service.get_ground_contact_point(bbox_list)
    assert px == 200.0, "x should be (100+300)/2 = 200"
    assert py == 400.0, "y should be y2 = 400 (bottom of box)"

    # Test dict format
    bbox_dict = {"x1": 50.0, "y1": 80.0, "x2": 150.0, "y2": 220.0}
    px2, py2 = debris_coordinate_service.get_ground_contact_point(bbox_dict)
    assert px2 == 100.0, "x should be (50+150)/2 = 100"
    assert py2 == 220.0, "y should be y2 = 220"

    # Test invalid / zero area fallback
    px_inv, py_inv = debris_coordinate_service.get_ground_contact_point([0, 0, 0, 0])
    assert px_inv == 0.0 and py_inv == 0.0


def test_raycast_nadir_camera_center_target():
    """
    FR-03 & FR-04: Test Nadir (top-down, pitch = -90 deg) camera raycasting.
    If debris ground contact point is at the exact principal center of the image,
    the ground raycast must point straight down: debris lat/lon == drone lat/lon.
    """
    telemetry = {
        "latitude": 12.971600,
        "longitude": 80.220600,
        "altitude": 20.0,
        "pitch": -90.0,
        "heading": 0.0,
        "roll": 0.0,
    }

    # Box centered horizontally at 960, touching bottom-center exactly at principal point (960, 540)
    bbox = [860, 440, 1060, 540]
    result = debris_coordinate_service.predict_coordinates(
        bbox=bbox,
        image_width=1920,
        image_height=1080,
        telemetry=telemetry,
    )

    assert result["status"] in ("estimated", "verified")
    assert result["latitude"] is not None
    assert result["longitude"] is not None
    # At exact optical center, predicted lat/lon must match drone GPS within ~0.000002 deg (~0.25m)
    dist = debris_coordinate_service.geodesic_distance_meters(
        result["latitude"], result["longitude"], telemetry["latitude"], telemetry["longitude"]
    )
    assert dist < 0.25, f"Debris at optical center should match drone position, got distance {dist}m"
    assert result["uncertainty_m"] is not None
    assert 0.1 <= result["uncertainty_m"] <= 5.0
    assert "WGS84" in result["crs"]


def test_raycast_oblique_heading_projection():
    """
    FR-04: Test forward oblique camera (pitch = -45 deg, heading = 90 deg East).
    When camera looks forward-down at 45 deg, an object at the vertical optical center (cy)
    should strike ground plane forward along the heading direction by altitude * tan(45°) = altitude meters.
    """
    altitude = 25.0
    telemetry = {
        "latitude": 13.000000,
        "longitude": 80.000000,
        "altitude": altitude,
        "pitch": -45.0,  # 45 degrees depressed from horizon
        "heading": 90.0,  # Heading due East
        "roll": 0.0,
    }

    # Object touching bottom-center at principal point (960, 540)
    bbox = [910, 490, 1010, 540]
    result = debris_coordinate_service.predict_coordinates(
        bbox=bbox,
        image_width=1920,
        image_height=1080,
        telemetry=telemetry,
    )

    assert result["status"] == "estimated"
    assert result["latitude"] is not None
    assert result["longitude"] is not None

    # Expected ground point: ~25m East of drone
    # Latitude should be almost unchanged (~13.000000)
    # Longitude should be East (> 80.000000)
    assert result["longitude"] > telemetry["longitude"], "Target should project East"
    assert abs(result["latitude"] - telemetry["latitude"]) < 0.00005, "Latitude offset should be near 0 for due East heading"

    dist = debris_coordinate_service.geodesic_distance_meters(
        telemetry["latitude"], telemetry["longitude"], result["latitude"], result["longitude"]
    )
    # At pitch=-45°, raycast distance should be ~25m (altitude / tan(45°) = 25m)
    assert abs(dist - 25.0) < 1.5, f"Expected ~25m forward ground strike, got {dist:.2f}m"


def test_missing_telemetry_returns_explicit_unavailable():
    """
    FR-03: Never invent fake coordinates or substitute camera GPS for debris location.
    If telemetry or altitude is missing, explicitly report status: 'unavailable'.
    """
    # Case 1: Telemetry is None
    res1 = debris_coordinate_service.predict_coordinates(
        bbox=[100, 100, 200, 200],
        telemetry=None,
    )
    assert res1["status"] == "unavailable"
    assert res1["latitude"] is None
    assert res1["longitude"] is None
    assert "Coordinates unavailable" in res1["formatted"]

    # Case 2: Altitude is 0 or negative
    bad_pose = {
        "latitude": 12.9716,
        "longitude": 80.2206,
        "altitude": 0.5,  # <= 1.0m AGL threshold
    }
    res2 = debris_coordinate_service.predict_coordinates(
        bbox=[100, 100, 200, 200],
        telemetry=bad_pose,
    )
    assert res2["status"] == "unavailable"
    assert res2["latitude"] is None

    # Case 3: GPS is missing (None)
    no_gps_pose = {
        "latitude": None,
        "longitude": None,
        "altitude": 15.0,
    }
    res3 = debris_coordinate_service.predict_coordinates(
        bbox=[100, 100, 200, 200],
        telemetry=no_gps_pose,
    )
    assert res3["status"] == "unavailable"


def test_skyward_or_invalid_geometry_rejection():
    """
    FR-04: Test non-intersecting geometry (e.g. camera pointing at sky, pitch >= 0).
    Raycast does not intersect ground plane and must be rejected gracefully.
    """
    telemetry = {
        "latitude": 12.9716,
        "longitude": 80.2206,
        "altitude": 30.0,
        "pitch": 15.0,  # Pointing 15 deg ABOVE horizon
    }
    res = debris_coordinate_service.predict_coordinates(
        bbox=[900, 100, 1000, 200],  # near top of sky image
        telemetry=telemetry,
    )
    assert res["status"] == "unavailable"


def test_spatial_uncertainty_decoupling():
    """
    FR-05: Spatial uncertainty (uncertainty_m) must reflect physical sensor noise
    (altitude, GSD, slant range, gimbal error) and NOT simply be the YOLO confidence.
    """
    # Low altitude (10m) nadir flight
    telemetry_low = {
        "latitude": 12.9716,
        "longitude": 80.2206,
        "altitude": 10.0,
        "pitch": -90.0,
    }
    res_low = debris_coordinate_service.predict_coordinates(
        bbox=[900, 500, 1020, 540],
        telemetry=telemetry_low,
    )

    # High altitude (80m) oblique flight (pitch = -30 deg)
    telemetry_high = {
        "latitude": 12.9716,
        "longitude": 80.2206,
        "altitude": 80.0,
        "pitch": -30.0,
    }
    res_high = debris_coordinate_service.predict_coordinates(
        bbox=[900, 500, 1020, 540],
        telemetry=telemetry_high,
    )

    assert res_low["uncertainty_m"] is not None
    assert res_high["uncertainty_m"] is not None
    assert res_high["uncertainty_m"] > res_low["uncertainty_m"], (
        f"Higher altitude and oblique slant range should yield greater spatial uncertainty: "
        f"{res_high['uncertainty_m']}m vs {res_low['uncertainty_m']}m"
    )


def test_geodesic_distance_and_ground_truth_accuracy():
    """
    Tests geodesic distance formula and benchmark evaluation against surveyed targets.
    """
    # 1 deg latitude is approximately 111,195 meters
    d_lat = debris_coordinate_service.geodesic_distance_meters(
        12.0, 80.0, 13.0, 80.0
    )
    assert 110000 < d_lat < 112000

    # Test benchmark accuracy evaluation with 10m offset test case
    test_cases = [
        {
            "bbox": [860, 440, 1060, 540],
            "image_width": 1920,
            "image_height": 1080,
            "telemetry": {
                "latitude": 12.971600,
                "longitude": 80.220600,
                "altitude": 20.0,
                "pitch": -90.0,
                "heading": 0.0,
            },
            "gt_latitude": 12.971600,
            "gt_longitude": 80.220600,
        }
    ]
    eval_res = debris_coordinate_service.evaluate_ground_truth_accuracy(
        test_cases=test_cases,
        tolerance_m=2.0,
    )
    assert eval_res["status"] == "VALIDATED"
    assert eval_res["valid_test_cases"] == 1
    assert eval_res["within_tolerance_pct"] == 100.0
    assert eval_res["median_error_m"] < 0.5


def test_database_persistence_of_debris_coordinates():
    """
    FR-09 & FR-10: Verifies that database_service stores and retrieves all coordinate columns.
    """
    test_session = f"test_coords_{int(time.time())}"
    debris_coords = {
        "latitude": 12.971650,
        "longitude": 80.220680,
        "uncertainty_m": 1.2,
        "status": "estimated",
        "method": "raycast_intrinsic_euler",
        "crs": "WGS 84 / EPSG:4326",
        "formatted": "12.971650° N, 80.220680° E (±1.2m)",
    }

    item = {
        "class_name": "FOD",
        "class_id": 0,
        "confidence": 0.88,
        "bbox": [150, 200, 250, 320],
        "track_id": 1,
        "model": "fod",
        "debris_coordinates": debris_coords,
    }

    # Save via save_detections
    database_service.save_detections(session_id=test_session, frame_id=1, detections=[item])

    with SessionLocal() as db:
        saved = db.query(Detection).filter(Detection.job_id == test_session).first()
        assert saved is not None
        assert saved.latitude == 12.971650
        assert saved.longitude == 80.220680
        assert saved.coordinate_uncertainty_m == 1.2
        assert saved.coordinate_status == "estimated"
        assert saved.coordinate_method == "raycast_intrinsic_euler"
        assert saved.coordinate_crs == "WGS 84 / EPSG:4326"
        assert "12.971650" in saved.coordinate_formatted

        # Clean up
        db.query(Detection).filter(Detection.job_id == test_session).delete()
        db.commit()


def test_central_results_sync_includes_debris_coordinates():
    """
    FR-06 & FR-09: Verifies that syncing to central database registers location_data for debris detections.
    """
    from backend.app.db.models import AnalysisJob, AnalysisResult

    test_job_id = f"test_central_fod_{int(time.time())}"

    with SessionLocal() as db:
        # Create test AnalysisJob
        job = AnalysisJob(
            id=test_job_id,
            filename="fod_test_flight.mp4",
            file_path="/tmp/fod_test_flight.mp4",
            analysis_type="FOD",
            media_type="VIDEO",
            status="COMPLETED",
            total_frames=100,
            processed_frames=100,
            unique_fod_count=1,
            fod_count=1,
            confidence_threshold=0.25,
        )
        db.add(job)

        # Create Detection with coordinates
        det = Detection(
            job_id=test_job_id,
            frame_number=42,
            class_name="FOD",
            confidence=0.85,
            x1=100.0,
            y1=150.0,
            x2=200.0,
            y2=250.0,
            analysis_type="FOD",
            latitude=12.971700,
            longitude=80.220750,
            coordinate_uncertainty_m=1.4,
            coordinate_status="estimated",
            coordinate_method="raycast_intrinsic_euler",
            coordinate_crs="WGS84",
            coordinate_formatted="12.971700° N, 80.220750° E (±1.4m)",
        )
        db.add(det)
        db.commit()

    # Synchronize job to central results
    res_dict = central_results_service.sync_analysis_job_to_central_result(job_id=test_job_id)
    assert res_dict is not None
    assert res_dict["module_type"] == "offline_surveillance"

    # Query events from database
    with SessionLocal() as db:
        events = db.query(DetectionEvent).filter(DetectionEvent.analysis_result_id == res_dict["id"]).all()
        assert len(events) >= 1
        ev = events[0]
        assert ev.class_name == "FOD"
        assert ev.location_data is not None
        assert ev.location_data.get("latitude") == 12.971700
        assert ev.location_data.get("longitude") == 80.220750
        assert ev.location_data.get("uncertainty_m") == 1.4
        assert ev.location_data.get("status") == "estimated"

        # Clean up
        db.query(DetectionEvent).filter(DetectionEvent.analysis_result_id == res_dict["id"]).delete()
        db.query(AnalysisResult).filter(AnalysisResult.id == res_dict["id"]).delete()
        db.query(Detection).filter(Detection.job_id == test_job_id).delete()
        db.query(AnalysisJob).filter(AnalysisJob.id == test_job_id).delete()
        db.commit()
