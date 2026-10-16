import os
import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import SessionLocal
from backend.app.db.models import NavigationRoute, Drone, Detection
from backend.app.services.route_planning_service import route_planning_service
from backend.app.services.drone_service import drone_service
from backend.app.schemas.navigation import RouteCalculateRequest, WaypointItem

client = TestClient(app)


def test_haversine_and_bearing_calculation():
    # Chennai Airport: 12.9941° N, 80.1709° E
    # Marina Beach: 13.0500° N, 80.2824° E
    lat1, lon1 = 12.9941, 80.1709
    lat2, lon2 = 13.0500, 80.2824

    dist = route_planning_service.calculate_distance(lat1, lon1, lat2, lon2)
    assert 13000 < dist < 15000  # Approx 13.68 km on WGS 84 ellipsoid

    bearing = route_planning_service.calculate_bearing(lat1, lon1, lat2, lon2)
    assert 50 < bearing < 75  # North-East quadrant

    compass = route_planning_service.degrees_to_compass(bearing)
    assert compass in ("NE", "ENE")


def test_route_calculation_service():
    req = RouteCalculateRequest(
        start_latitude=13.0827,
        start_longitude=80.2707,
        target_latitude=13.0900,
        target_longitude=80.2800,
        target_name="Runway 07 Debris Zone",
        waypoints=[
            WaypointItem(order=1, latitude=13.0850, longitude=80.2730, altitude_agl_m=35.0, notes="Hold point A"),
            WaypointItem(order=2, latitude=13.0880, longitude=80.2760, altitude_agl_m=40.0, notes="Turn point B"),
        ],
        speed_mps=10.0,
    )
    result = route_planning_service.plan_route(req)
    assert result.valid is True
    assert result.status == "PLANNED"
    assert result.waypoints_count == 2
    assert len(result.segments) == 3  # Start->WP1, WP1->WP2, WP2->Target
    assert result.total_distance_m > 0
    assert result.straight_line_distance_m > 0
    assert result.estimated_time_seconds > 0
    assert "m" in result.estimated_time_formatted or "s" in result.estimated_time_formatted


def test_guidance_calculation():
    # Drone at (13.0827, 80.2707) heading East (90 deg)
    # Target is directly North
    res = route_planning_service.calculate_guidance(
        drone_lat=13.0827,
        drone_lon=80.2707,
        drone_heading=90.0,
        target_lat=13.0900,
        target_lon=80.2707,
    )
    assert res.distance_to_target_m > 700.0
    assert 355.0 <= res.bearing_to_target_deg or res.bearing_to_target_deg <= 5.0
    assert res.compass_direction == "N"
    assert res.relative_bearing_deg is not None
    # Heading East (90 deg) to go North (0 deg) means turn left ~90 deg
    assert -95.0 <= res.relative_bearing_deg <= -85.0
    assert "Turn left" in res.steering_instruction
    assert res.is_arrived is False


def test_api_calculate_route_endpoint():
    payload = {
        "start_latitude": 13.0827,
        "start_longitude": 80.2707,
        "target_latitude": 13.0870,
        "target_longitude": 80.2750,
        "target_name": "Runway Exit B",
        "waypoints": [
            {"order": 1, "latitude": 13.0840, "longitude": 80.2720, "altitude_agl_m": 25.0}
        ],
        "speed_mps": 12.0
    }
    res = client.post("/api/v1/navigation/route/calculate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["waypoints_count"] == 1
    assert len(data["segments"]) == 2
    assert data["total_distance_m"] > 0
    assert data["straight_line_distance_m"] > 0
    assert "detour_percentage" in data
    assert "assumptions" in data
    assert len(data["assumptions"]) > 0


def test_api_guidance_endpoint():
    payload = {
        "drone_latitude": 13.0827,
        "drone_longitude": 80.2707,
        "drone_heading": 45.0,
        "drone_speed": 10.0,
        "target_latitude": 13.0828,
        "target_longitude": 80.2708,
    }
    res = client.post("/api/v1/navigation/route/guidance", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "distance_to_target_m" in data
    assert "bearing_to_target_deg" in data
    assert "steering_instruction" in data


def test_api_route_persistence_and_deletion():
    # Save route
    payload = {
        "name": "Runway 27 Inspection Alpha",
        "start_latitude": 13.0827,
        "start_longitude": 80.2707,
        "target_latitude": 13.0900,
        "target_longitude": 80.2800,
        "target_name": "Debris Zone #1",
        "waypoints": [
            {"order": 1, "latitude": 13.0850, "longitude": 80.2730, "altitude_agl_m": 30.0}
        ],
        "speed_mps": 10.0
    }
    create_res = client.post("/api/v1/navigation/routes", json=payload)
    assert create_res.status_code == 201
    route_data = create_res.json()
    route_id = route_data["id"]
    assert route_data["name"] == "Runway 27 Inspection Alpha"

    # Fetch routes list
    list_res = client.get("/api/v1/navigation/routes")
    assert list_res.status_code == 200
    routes_list = list_res.json()
    assert any(r["id"] == route_id for r in routes_list)

    # Fetch single route
    get_res = client.get(f"/api/v1/navigation/routes/{route_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == route_id

    # Delete route
    del_res = client.delete(f"/api/v1/navigation/routes/{route_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True


def test_live_telemetry_and_drone_connection():
    # Disconnect first
    client.post("/api/v1/navigation/drone/disconnect")

    # When disconnected, should indicate offline/stale and never fabricate coordinates
    telem_res = client.get("/api/v1/navigation/telemetry/live")
    assert telem_res.status_code == 200
    telem_data = telem_res.json()
    assert telem_data["connected"] is False
    assert telem_data["is_stale"] is True
    assert telem_data["latitude"] is None

    # Connect drone
    conn_res = client.post("/api/v1/navigation/drone/connect", json={})
    assert conn_res.status_code == 200
    assert conn_res.json()["connected"] is True

    # Send heartbeat
    hb_res = client.post("/api/v1/navigation/drone/heartbeat", json={
        "latitude": 13.0827,
        "longitude": 80.2707,
        "altitude": 35.0,
        "speed": 9.2,
        "heading": 85.0,
        "battery": 92.0
    })
    assert hb_res.status_code == 200

    # Live telemetry should now be valid
    telem_res2 = client.get("/api/v1/navigation/telemetry/live")
    assert telem_res2.status_code == 200
    telem_data2 = telem_res2.json()
    assert telem_data2["connected"] is True
    assert telem_data2["is_stale"] is False
    assert telem_data2["latitude"] == 13.0827
    assert telem_data2["longitude"] == 80.2707
    assert telem_data2["heading"] == 85.0


def test_debris_targets_endpoint():
    res = client.get("/api/v1/navigation/debris-targets?limit=10")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    for item in items:
        assert "is_navigable" in item
        assert "status" in item
        assert "id" in item


def test_geodesic_distance_precision_and_124km_reference():
    """
    FR-05, FR-06: Validates exact distance and hours formatting for 124.70 km reference route.
    124.70 km at 10.0 m/s cruise produces approximately 3 hours, 27 minutes, 50 seconds.
    """
    # 124,700 meters / 10.0 m/s = 12,470 seconds
    formatted = route_planning_service.format_time(12470.0)
    assert formatted == "3h 27m 50s"

    # Test short duration
    assert route_planning_service.format_time(45.0) == "45s"
    assert route_planning_service.format_time(195.0) == "3m 15s"

    # Plan a long route ~124.7 km (Chennai 13.0827 to near Pondicherry 11.9600, 80.2707)
    req = RouteCalculateRequest(
        start_latitude=13.0827,
        start_longitude=80.2707,
        target_latitude=11.9600,
        target_longitude=80.2707,
        target_name="Southern Airfield Staging",
        speed_mps=10.0,
    )
    res = route_planning_service.plan_route(req)
    assert 120000.0 < res.total_distance_m < 130000.0
    assert "3h" in res.estimated_time_formatted
    assert res.calculation_method == "WGS84_GEODESIC"
    assert len(res.assumptions) >= 3


def test_coordinate_validation_boundary_conditions():
    """
    FR-03: Coordinate validation checks latitude (-90 to +90) and longitude (-180 to +180).
    Rejects out-of-range coordinates.
    """
    # Invalid latitude > 90
    bad_lat = {
        "start_latitude": 95.0,
        "start_longitude": 80.0,
        "target_latitude": 13.0,
        "target_longitude": 80.0,
    }
    res = client.post("/api/v1/navigation/route/calculate", json=bad_lat)
    assert res.status_code == 422

    # Invalid longitude < -180
    bad_lon = {
        "start_latitude": 13.0,
        "start_longitude": -185.0,
        "target_latitude": 13.0,
        "target_longitude": 80.0,
    }
    res2 = client.post("/api/v1/navigation/route/calculate", json=bad_lon)
    assert res2.status_code == 422

    # Valid equatorial and southern hemisphere coordinates
    valid_south = {
        "start_latitude": -33.8688,
        "start_longitude": 151.2093,
        "target_latitude": -33.8700,
        "target_longitude": 151.2150,
        "target_name": "Sydney Harbour Run",
    }
    res3 = client.post("/api/v1/navigation/route/calculate", json=valid_south)
    assert res3.status_code == 200
    assert res3.json()["valid"] is True


def test_telemetry_explicit_five_states():
    """
    FR-02: Confirms explicit states: CONNECTED, STALE, OFFLINE, SIMULATED, INVALID_TELEMETRY.
    """
    # 1. OFFLINE state
    client.post("/api/v1/navigation/drone/disconnect")
    t1 = client.get("/api/v1/navigation/telemetry/live").json()
    assert t1["connected"] is False
    assert t1["status"] in ("OFFLINE", "STALE")

    # 2. CONNECTED state
    client.post("/api/v1/navigation/drone/connect", json={"drone_id": "test_drone_active"})
    client.post("/api/v1/navigation/drone/heartbeat", json={
        "drone_id": "test_drone_active",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "altitude": 30.0,
        "speed": 8.0,
        "heading": 45.0,
        "battery": 95.0,
        "source": "MAVLINK_TELEMETRY"
    })
    t2 = client.get("/api/v1/navigation/telemetry/live").json()
    assert t2["connected"] is True
    assert t2["status"] == "CONNECTED"
    assert t2["has_gps_fix"] is True

    # 3. SIMULATED state
    client.post("/api/v1/navigation/drone/heartbeat", json={
        "drone_id": "sim-drone-01",
        "latitude": 13.0830,
        "longitude": 80.2710,
        "altitude": 32.0,
        "speed": 10.0,
        "heading": 50.0,
        "battery": 94.0,
        "source": "SIMULATION_HARNESS"
    })
    t3 = client.get("/api/v1/navigation/telemetry/live").json()
    assert t3["status"] == "SIMULATED"
    assert "Simulation Harness" in t3["message"]

    # 4. INVALID_TELEMETRY state
    client.post("/api/v1/navigation/drone/heartbeat", json={
        "drone_id": "test_drone_active",
        "latitude": 0.0,
        "longitude": 0.0,
        "altitude": 0.0,
        "source": "MAVLINK_TELEMETRY"
    })
    t4 = client.get("/api/v1/navigation/telemetry/live").json()
    assert t4["status"] == "INVALID_TELEMETRY"


def test_configurable_stale_threshold_endpoint():
    """
    FR-02: Verifies configuring stale threshold via API.
    """
    res = client.post("/api/v1/navigation/telemetry/threshold", json={"stale_threshold_seconds": 25.0})
    assert res.status_code == 200
    assert res.json()["stale_threshold_seconds"] == 25.0
    assert drone_service.stale_threshold_seconds == 25.0

    # Reset back to default
    client.post("/api/v1/navigation/telemetry/threshold", json={"stale_threshold_seconds": 15.0})
    assert drone_service.stale_threshold_seconds == 15.0


def test_route_validation_and_operational_warnings():
    """
    FR-08: Verifies warnings for routes exceeding operational limit and significant detour.
    """
    req = RouteCalculateRequest(
        start_latitude=13.0827,
        start_longitude=80.2707,
        target_latitude=13.1200,
        target_longitude=80.2707,
        max_range_limit_m=3000.0,  # 3 km limit
    )
    res = route_planning_service.plan_route(req)
    assert res.total_distance_m > 3000.0
    # Must contain range warning
    assert any("exceeds configured operational planning limit" in w for w in res.warnings)


def test_obstacle_ai_model_isolation_and_classes():
    """
    FR-09: Verifies obstacle AI model isolation and classes.
    navigation_best.pt contains 80 COCO classes.
    runway_light_best.pt contains strictly 2 classes (LIGHT OFF, LIGHT ON).
    """
    from ultralytics import YOLO

    nav_path = "ml_engine/models/navigation_best.pt"
    light_path = "ml_engine/models/runway_light_best.pt"

    assert os.path.exists(nav_path)
    assert os.path.exists(light_path)

    nav_model = YOLO(nav_path)
    assert len(nav_model.names) == 80
    assert "person" in nav_model.names.values()
    assert "airplane" in nav_model.names.values()

    light_model = YOLO(light_path)
    assert len(light_model.names) == 2
    light_classes = set(light_model.names.values())
    assert light_classes == {"LIGHT OFF", "LIGHT ON"}
    # Model isolation invariant: runway light model must NOT contain debris or obstacle classes
    assert "FOD" not in light_classes
    assert "debris" not in light_classes
    assert "airplane" not in light_classes
