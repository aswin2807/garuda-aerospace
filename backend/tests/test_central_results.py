import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.central_results_service import central_results_service
from backend.app.schemas.results import AnalysisResultCreate, DetectionEventCreate, MediaAssetCreate

client = TestClient(app)


def test_create_results_all_five_modules():
    """
    FR-01, FR-02, FR-03, FR-04, FR-05, FR-06:
    Verify that all five modules can create and store results in the centralized database.
    """
    modules = [
        ("navigation", "Nav Corridor Survey", {"obstacles": 3}),
        ("rod_debris", "Runway Centerline FOD Sweep", {"debris_items": 1}),
        ("runway_lights", "Runway Inset Lights Inspection", {"lights_on": 10, "lights_off": 2}),
        ("live_surveillance", "Perimeter Camera Live Monitoring", {"camera_id": "CAM-01"}),
        ("offline_surveillance", "Sortie Post-Flight Media Analysis", {"frames": 500})
    ]

    for mod, title, rdata in modules:
        payload = {
            "module_type": mod,
            "title": title,
            "status": "completed",
            "summary": f"Automated test for {mod}",
            "result_data": rdata,
            "events": [
                {
                    "event_type": "TEST_EVENT",
                    "class_name": f"{mod}_class",
                    "confidence": 0.95
                }
            ],
            "media_assets": [
                {
                    "media_type": "image",
                    "storage_key": f"/static/{mod}_test.jpg",
                    "file_name": f"{mod}_test.jpg",
                    "file_size": 1024
                }
            ]
        }
        res = client.post("/api/results", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["id"].startswith("res_")
        assert data["module_type"] == mod
        assert data["title"] == title
        assert data["status"] == "completed"


def test_results_summary_endpoint():
    """
    FR-07: Verify dashboard summary statistics across all modules.
    """
    res = client.get("/api/results/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_results" in data
    assert data["total_results"] > 0
    assert "by_module" in data
    assert "navigation" in data["by_module"]
    assert "rod_debris" in data["by_module"]
    assert "runway_lights" in data["by_module"]
    assert "live_surveillance" in data["by_module"]
    assert "offline_surveillance" in data["by_module"]
    assert "by_status" in data
    assert "recent_results" in data


def test_results_filtering_and_pagination():
    """
    FR-07, FR-08: Verify filtering by module, status, search, and pagination.
    """
    # 1. Filter by navigation
    res_nav = client.get("/api/results?module_type=navigation&page=1&page_size=5")
    assert res_nav.status_code == 200
    nav_data = res_nav.json()
    assert nav_data["total"] >= 1
    for item in nav_data["items"]:
        assert item["module_type"] == "navigation"

    # 2. Filter by runway_lights
    res_rwy = client.get("/api/results?module_type=runway_lights&page=1&page_size=5")
    assert res_rwy.status_code == 200
    rwy_data = res_rwy.json()
    assert rwy_data["total"] >= 1
    for item in rwy_data["items"]:
        assert item["module_type"] == "runway_lights"

    # 3. Filter by search
    res_search = client.get("/api/results?search=Corridor")
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["total"] >= 1


def test_result_details_with_events_and_media():
    """
    FR-09: Verify retrieving complete result details with events and media assets.
    """
    # Create a result with known events
    payload = {
        "module_type": "rod_debris",
        "title": "FOD Detail Test",
        "status": "completed",
        "summary": "Detailed FOD detection test",
        "events": [
            {
                "event_type": "FOD_DETECTED",
                "class_name": "bolt",
                "confidence": 0.89,
                "location_data": {"bbox": [10, 20, 30, 40]}
            }
        ],
        "media_assets": [
            {
                "media_type": "image",
                "storage_key": "/data/test_fod.jpg",
                "file_name": "test_fod.jpg",
                "file_size": 2048
            }
        ]
    }
    create_res = client.post("/api/results", json=payload)
    assert create_res.status_code == 201
    res_id = create_res.json()["id"]

    # Fetch detail
    detail_res = client.get(f"/api/results/{res_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == res_id
    assert len(detail["events"]) == 1
    assert detail["events"][0]["class_name"] == "bolt"
    assert len(detail["media_assets"]) == 1
    assert detail["media_assets"][0]["file_name"] == "test_fod.jpg"

    # Fetch events endpoint
    ev_res = client.get(f"/api/results/{res_id}/events")
    assert ev_res.status_code == 200
    assert ev_res.json()["total"] == 1

    # Fetch media endpoint
    med_res = client.get(f"/api/results/{res_id}/media")
    assert med_res.status_code == 200
    assert len(med_res.json()["media_assets"]) == 1


def test_result_status_update():
    """
    FR-10: Verify PATCH status updates and error details preservation.
    """
    payload = {
        "module_type": "navigation",
        "title": "Status Update Test",
        "status": "processing"
    }
    create_res = client.post("/api/results", json=payload)
    res_id = create_res.json()["id"]

    # Update to failed with error message
    patch_res = client.patch(f"/api/results/{res_id}", json={
        "status": "failed",
        "error_message": "Camera stream dropped during navigation inference",
        "summary": "Failed due to hardware network disconnect"
    })
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "Camera stream dropped during navigation inference"


def test_surveillance_sessions_api():
    """
    FR-05, FR-06: Verify surveillance session recording and retrieval.
    """
    sess_payload = {
        "mode": "live",
        "camera_id": "CAM-TEST-99",
        "source_reference": "rtsp://192.168.144.108:554/live",
        "status": "active",
        "metadata_json": {"fps": 30, "model": "NAVIGATION"}
    }
    create_sess = client.post("/api/sessions", json=sess_payload)
    assert create_sess.status_code == 201
    sess_id = create_sess.json()["id"]

    # Get session details
    get_sess = client.get(f"/api/sessions/{sess_id}")
    assert get_sess.status_code == 200
    assert get_sess.json()["camera_id"] == "CAM-TEST-99"

    # List sessions
    list_sess = client.get("/api/sessions?mode=live")
    assert list_sess.status_code == 200
    assert list_sess.json()["total"] >= 1
