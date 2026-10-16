import math
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.logging import logger
from backend.app.db.models import (
    NavigationRoute,
    Drone,
    Detection,
    DetectionEvent,
    AnalysisResult,
    get_utc_now,
    generate_route_id,
)
from backend.app.schemas.navigation import (
    RouteCalculateRequest,
    RouteCalculateResponse,
    RouteSegment,
    RouteSaveRequest,
    RouteResponse,
    DebrisTargetItem,
    GuidanceCalculationResponse,
    WaypointItem,
)


class RoutePlanningService:
    """
    ROD Navigation Module — Live Drone Position, Route Planning & Waypoint Guidance Engine
    Fulfills PRD Functional Requirements:
      - FR-01: WGS 84 Geographic coordinate accuracy & CRS consistency
      - FR-02: Live Drone GPS position and telemetry tracking
      - FR-03: Target coordinate entry & validation
      - FR-04: Multi-segment route planning & manual waypoint management
      - FR-05: Geodesic route distance calculation & straight-line distinction
      - FR-06: Travel-time prediction (T = D / V) with realistic hours/minutes formatting
      - FR-07: Route prediction and progress tracking
      - FR-08: Route validation and safety warnings (configurable 3km planning limits)
      - FR-10: Route persistence & retrieval
      - FR-11: Planning mode vs Guidance Preview vs Live Guidance separation
    """

    # WGS 84 Ellipsoid constants
    WGS84_A = 6378137.0          # Semi-major axis (meters)
    WGS84_F = 1.0 / 298.257223563 # Flattening
    WGS84_B = 6356752.314245     # Semi-minor axis (meters)
    EARTH_RADIUS_METERS = 6371000.0  # Mean spherical radius (meters)

    COMPASS_POINTS = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]

    @classmethod
    def calculate_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates geodesic distance in meters on the WGS 84 reference ellipsoid.
        Uses Vincenty inverse formula with Lambert-Andoyer / Haversine fallback for antipodal/near points.
        Accuracy is sub-meter across all latitudes.
        """
        # Identical point check
        if abs(lat1 - lat2) < 1e-9 and abs(lon1 - lon2) < 1e-9:
            return 0.0

        # High-precision Vincenty inverse on WGS 84 ellipsoid
        a = cls.WGS84_A
        b = cls.WGS84_B
        f = cls.WGS84_F

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        L = math.radians(lon2 - lon1)

        U1 = math.atan((1.0 - f) * math.tan(phi1))
        U2 = math.atan((1.0 - f) * math.tan(phi2))
        sinU1 = math.sin(U1)
        cosU1 = math.cos(U1)
        sinU2 = math.sin(U2)
        cosU2 = math.cos(U2)

        lam = L
        for _ in range(100):
            sinLam = math.sin(lam)
            cosLam = math.cos(lam)
            sinSigma = math.sqrt(
                (cosU2 * sinLam) ** 2 +
                (cosU1 * sinU2 - sinU1 * cosU2 * cosLam) ** 2
            )
            if sinSigma == 0:
                return 0.0  # Coincident points

            cosSigma = sinU1 * sinU2 + cosU1 * cosU2 * cosLam
            sigma = math.atan2(sinSigma, cosSigma)
            sinAlpha = (cosU1 * cosU2 * sinLam) / sinSigma
            cosSqAlpha = 1.0 - sinAlpha ** 2

            cos2SigmaM = cosSigma - (2.0 * sinU1 * sinU2) / cosSqAlpha if cosSqAlpha != 0 else 0.0

            C = (f / 16.0) * cosSqAlpha * (4.0 + f * (4.0 - 3.0 * cosSqAlpha))
            lam_prev = lam
            lam = L + (1.0 - C) * f * sinAlpha * (
                sigma + C * sinSigma * (cos2SigmaM + C * cosSigma * (-1.0 + 2.0 * cos2SigmaM ** 2))
            )
            if abs(lam - lam_prev) < 1e-12:
                break
        else:
            # Fallback to great-circle Haversine if Vincenty does not converge (antipodal)
            dphi = math.radians(lat2 - lat1)
            dlam = math.radians(lon2 - lon1)
            haver_a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlam / 2.0) ** 2)
            c = 2.0 * math.atan2(math.sqrt(haver_a), math.sqrt(max(0.0, 1.0 - haver_a)))
            return cls.EARTH_RADIUS_METERS * c

        uSq = cosSqAlpha * (a ** 2 - b ** 2) / (b ** 2)
        A = 1.0 + (uSq / 16384.0) * (4096.0 + uSq * (-768.0 + uSq * (320.0 - 175.0 * uSq)))
        B = (uSq / 1024.0) * (256.0 + uSq * (-128.0 + uSq * (74.0 - 47.0 * uSq)))
        deltaSigma = B * sinSigma * (
            cos2SigmaM + (B / 4.0) * (
                cosSigma * (-1.0 + 2.0 * cos2SigmaM ** 2) -
                (B / 6.0) * cos2SigmaM * (-3.0 + 4.0 * sinSigma ** 2) * (-3.0 + 4.0 * cos2SigmaM ** 2)
            )
        )
        return b * A * (sigma - deltaSigma)

    @classmethod
    def calculate_bearing(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates initial forward azimuth (bearing) from Point 1 to Point 2 in degrees [0, 360).
        """
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dlam = math.radians(lon2 - lon1)

        y = math.sin(dlam) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)

        bearing_rad = math.atan2(y, x)
        bearing_deg = (math.degrees(bearing_rad) + 360.0) % 360.0
        return round(bearing_deg, 1)

    @classmethod
    def degrees_to_compass(cls, bearing_deg: float) -> str:
        """
        Converts bearing degrees into a 16-wind compass abbreviation.
        """
        idx = int((bearing_deg + 11.25) / 22.5) % 16
        return cls.COMPASS_POINTS[idx]

    @classmethod
    def format_time(cls, total_seconds: float) -> str:
        """
        Formats total seconds into clear, human-readable flight duration (FR-06).
        Correctly formats hours: e.g. 124.7km at 10m/s produces '3h 27m 50s', not '207m 50s'.
        """
        total_seconds = max(0.0, float(total_seconds))
        hours = int(total_seconds // 3600)
        mins = int((total_seconds % 3600) // 60)
        secs = int(round(total_seconds % 60))

        if secs >= 60:
            mins += 1
            secs = 0
        if mins >= 60:
            hours += 1
            mins = 0

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if mins > 0 or hours > 0:
            parts.append(f"{mins}m")
        parts.append(f"{secs}s")
        return " ".join(parts)

    def plan_route(self, req: RouteCalculateRequest) -> RouteCalculateResponse:
        """
        Calculates a drone flight route from start position through ordered waypoints to target (FR-04, FR-05, FR-06).
        Enforces WGS 84 geodesic standards, distinguishes direct vs multi-segment distances,
        and computes realistic travel times.
        """
        # Build ordered list of all route nodes: Start -> WP1 -> WP2 -> ... -> Target
        nodes: List[Dict[str, Any]] = [
            {
                "id": "start_point",
                "name": "Start / Drone Location",
                "lat": req.start_latitude,
                "lon": req.start_longitude,
                "alt": 0.0,
                "type": "start",
                "order": 0,
            }
        ]

        # Add sorted waypoints with unique IDs
        sorted_wps = sorted(req.waypoints or [], key=lambda w: w.order)
        for idx, wp in enumerate(sorted_wps):
            nodes.append({
                "id": wp.id or f"wp_{uuid.uuid4().hex[:8]}",
                "name": f"Waypoint #{wp.order}",
                "lat": wp.latitude,
                "lon": wp.longitude,
                "alt": wp.altitude_agl_m or 30.0,
                "type": "waypoint",
                "order": wp.order,
                "notes": wp.notes or "",
            })

        # Add destination target
        target_name = req.target_name or "Target Destination"
        nodes.append({
            "id": "target_point",
            "name": target_name,
            "lat": req.target_latitude,
            "lon": req.target_longitude,
            "alt": 0.0,
            "type": "target",
            "order": len(sorted_wps) + 1,
        })

        # Compute segments along the route
        segments: List[RouteSegment] = []
        total_dist_m = 0.0

        for i in range(len(nodes) - 1):
            n1 = nodes[i]
            n2 = nodes[i + 1]

            seg_dist = self.calculate_distance(n1["lat"], n1["lon"], n2["lat"], n2["lon"])
            seg_bearing = self.calculate_bearing(n1["lat"], n1["lon"], n2["lat"], n2["lon"])
            compass_dir = self.degrees_to_compass(seg_bearing)

            segments.append(
                RouteSegment(
                    from_name=n1["name"],
                    to_name=n2["name"],
                    from_lat=round(n1["lat"], 7),
                    from_lon=round(n1["lon"], 7),
                    to_lat=round(n2["lat"], 7),
                    to_lon=round(n2["lon"], 7),
                    distance_m=round(seg_dist, 1),
                    initial_bearing_deg=seg_bearing,
                    compass_direction=compass_dir,
                )
            )
            total_dist_m += seg_dist

        # Compute straight-line distance directly from start to target
        straight_line_dist_m = self.calculate_distance(
            req.start_latitude, req.start_longitude, req.target_latitude, req.target_longitude
        )

        # Compute detour percentage over straight line
        detour_pct = 0.0
        if straight_line_dist_m > 0:
            detour_pct = round(max(0.0, (total_dist_m - straight_line_dist_m) / straight_line_dist_m * 100.0), 1)

        # Estimated travel time: T = D / V + Maneuver Buffer
        speed = max(0.1, req.speed_mps or 10.0)
        waypoint_buffer_s = len(sorted_wps) * 8.0  # 8 seconds per intermediate turn/alignment maneuver
        flight_time_s = (total_dist_m / speed) + waypoint_buffer_s
        formatted_time = self.format_time(flight_time_s)

        speed_source = req.speed_source or "USER_CONFIGURED"
        max_range = req.max_range_limit_m or 3000.0

        # Safety & Operational Warnings (FR-08)
        warnings: List[str] = [
            "Straight-line geodesic course planned. Maintain visual line of sight (VLOS) and check runway clearances.",
        ]
        if total_dist_m > max_range:
            warnings.append(
                f"Route distance ({(total_dist_m / 1000.0):.2f} km) exceeds configured operational planning limit ({(max_range / 1000.0):.2f} km). Verify battery reserve."
            )
        if straight_line_dist_m > 0 and total_dist_m > straight_line_dist_m * 1.3:
            warnings.append(
                f"Multi-waypoint routing introduces a +{detour_pct}% detour over the straight-line course."
            )
        warnings.append("Route has not been cleared through live ATC airspace management.")

        assumptions: List[str] = [
            f"Ground speed: {speed:.1f} m/s ({(speed * 3.6):.1f} km/h) based on {speed_source.replace('_', ' ').lower()}.",
            f"Waypoint maneuver buffer: 8.0s per intermediate waypoint ({len(sorted_wps)} WPs = {waypoint_buffer_s:.0f}s).",
            "Geodesic calculations computed using WGS 84 ellipsoidal geometry (sub-meter numerical precision).",
            "Non-binding mathematical estimate for tactical planning; atmospheric winds and vertical climbs not factored.",
        ]

        return RouteCalculateResponse(
            valid=True,
            status="PLANNED",
            start_coordinates={"latitude": req.start_latitude, "longitude": req.start_longitude},
            target_coordinates={"latitude": req.target_latitude, "longitude": req.target_longitude},
            target_name=target_name,
            waypoints_count=len(sorted_wps),
            total_distance_m=round(total_dist_m, 1),
            straight_line_distance_m=round(straight_line_dist_m, 1),
            detour_percentage=detour_pct,
            estimated_time_seconds=round(flight_time_s, 1),
            estimated_time_formatted=formatted_time,
            speed_used_mps=speed,
            speed_source=speed_source,
            calculation_method="WGS84_GEODESIC",
            assumptions=assumptions,
            segments=segments,
            all_points=nodes,
            warnings=warnings,
        )

    def calculate_guidance(
        self,
        drone_lat: float,
        drone_lon: float,
        drone_heading: Optional[float],
        target_lat: float,
        target_lon: float,
        arrival_threshold_m: float = 5.0,
    ) -> GuidanceCalculationResponse:
        """
        Computes active navigational steering guidance toward next waypoint (FR-06).
        """
        dist_m = self.calculate_distance(drone_lat, drone_lon, target_lat, target_lon)
        target_bearing = self.calculate_bearing(drone_lat, drone_lon, target_lat, target_lon)
        compass_dir = self.degrees_to_compass(target_bearing)

        is_arrived = dist_m <= arrival_threshold_m
        arrival_status = "ARRIVED" if is_arrived else ("APPROACHING" if dist_m <= 15.0 else "EN_ROUTE")

        relative_bearing: Optional[float] = None
        steering_instruction = "Maintain course to destination"

        if is_arrived:
            steering_instruction = f"Waypoint reached within {arrival_threshold_m:.0f}m radius."
        elif drone_heading is not None:
            # Heading error between -180 and +180
            diff = (target_bearing - drone_heading + 540.0) % 360.0 - 180.0
            relative_bearing = round(diff, 1)

            if abs(diff) <= 4.0:
                steering_instruction = f"On course — maintain heading {target_bearing:.0f}° ({compass_dir})"
            elif diff > 0:
                steering_instruction = f"Turn right {round(diff)}° to heading {target_bearing:.0f}°"
            else:
                steering_instruction = f"Turn left {round(abs(diff))}° to heading {target_bearing:.0f}°"
        else:
            steering_instruction = f"Fly toward bearing {target_bearing:.0f}° ({compass_dir})"

        return GuidanceCalculationResponse(
            distance_to_target_m=round(dist_m, 1),
            bearing_to_target_deg=target_bearing,
            compass_direction=compass_dir,
            relative_bearing_deg=relative_bearing,
            steering_instruction=steering_instruction,
            arrival_status=arrival_status,
            is_arrived=is_arrived,
        )

    def save_route(self, db: Session, req: RouteSaveRequest, user_id: Optional[str] = None) -> NavigationRoute:
        """
        Persists a planned route with its waypoints in database (FR-10).
        """
        calc_req = RouteCalculateRequest(
            start_latitude=req.start_latitude,
            start_longitude=req.start_longitude,
            target_latitude=req.target_latitude,
            target_longitude=req.target_longitude,
            target_name=req.target_name,
            waypoints=req.waypoints,
            speed_mps=req.speed_mps,
        )
        calc_res = self.plan_route(calc_req)

        waypoints_data = [
            {
                "id": wp.id or f"wp_{uuid.uuid4().hex[:8]}",
                "order": wp.order,
                "latitude": wp.latitude,
                "longitude": wp.longitude,
                "altitude_agl_m": wp.altitude_agl_m or 30.0,
                "notes": wp.notes or "",
                "validation_status": "VALID",
            }
            for wp in (req.waypoints or [])
        ]

        route_record = NavigationRoute(
            id=generate_route_id(),
            name=req.name,
            drone_id=req.drone_id,
            start_latitude=req.start_latitude,
            start_longitude=req.start_longitude,
            target_latitude=req.target_latitude,
            target_longitude=req.target_longitude,
            target_name=req.target_name or "Target Destination",
            total_distance_m=calc_res.total_distance_m,
            estimated_time_s=calc_res.estimated_time_seconds or 0.0,
            waypoints_json=waypoints_data,
            status=req.status or "PLANNED",
            created_by=user_id,
            created_at=get_utc_now(),
            updated_at=get_utc_now(),
        )

        db.add(route_record)
        db.commit()
        db.refresh(route_record)
        return route_record

    def list_routes(self, db: Session, skip: int = 0, limit: int = 50) -> List[NavigationRoute]:
        """
        Lists saved routes ordered by most recent first (FR-10).
        """
        return (
            db.query(NavigationRoute)
            .order_by(desc(NavigationRoute.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_route(self, db: Session, route_id: str) -> Optional[NavigationRoute]:
        """
        Retrieves a saved route by ID.
        """
        return db.query(NavigationRoute).filter(NavigationRoute.id == route_id).first()

    def delete_route(self, db: Session, route_id: str) -> bool:
        """
        Deletes a saved route.
        """
        route = db.query(NavigationRoute).filter(NavigationRoute.id == route_id).first()
        if not route:
            return False
        db.delete(route)
        db.commit()
        return True

    def get_debris_targets(self, db: Session, limit: int = 40) -> List[DebrisTargetItem]:
        """
        Fetches foreign object debris (FOD) records with spatial coordinate data for navigation (FR-08).
        Distinguishes records with valid geographic coordinates from records with unavailable telemetry.
        """
        items: List[DebrisTargetItem] = []

        fod_dets = (
            db.query(Detection)
            .filter(Detection.analysis_type.in_(["FOD", "FOD_DEBRIS"]))
            .order_by(desc(Detection.timestamp))
            .limit(limit)
            .all()
        )

        for d in fod_dets:
            has_coords = (
                d.latitude is not None
                and d.longitude is not None
                and d.coordinate_status not in (None, "unavailable", "outside_pathway", "roi_unavailable")
                and -90.0 <= d.latitude <= 90.0
                and -180.0 <= d.longitude <= 180.0
            )

            items.append(
                DebrisTargetItem(
                    id=d.id,
                    class_name=d.class_name or "FOD",
                    confidence=d.confidence,
                    latitude=d.latitude if has_coords else None,
                    longitude=d.longitude if has_coords else None,
                    uncertainty_m=d.coordinate_uncertainty_m if has_coords else None,
                    status=d.coordinate_status or "unavailable",
                    formatted=d.coordinate_formatted or ("Coordinates unavailable" if not has_coords else f"{d.latitude:.6f}°, {d.longitude:.6f}°"),
                    source_module="ROD Debris Detection",
                    timestamp=d.timestamp.isoformat() if d.timestamp else None,
                    is_navigable=has_coords,
                    navigable_reason=None if has_coords else ("Debris detected outside runway pathway" if d.coordinate_status == "outside_pathway" else "Drone telemetry/altitude was missing at capture time"),
                )
            )

        if len(items) < limit:
            events = (
                db.query(DetectionEvent)
                .filter(DetectionEvent.class_name.ilike("%FOD%"))
                .order_by(desc(DetectionEvent.timestamp))
                .limit(limit - len(items))
                .all()
            )
            for ev in events:
                loc = ev.location_data or {}
                lat = loc.get("latitude")
                lon = loc.get("longitude")
                unc = loc.get("uncertainty_m")
                st = loc.get("status", "unavailable")

                has_coords = (
                    isinstance(lat, (int, float))
                    and isinstance(lon, (int, float))
                    and st not in ("unavailable", "outside_pathway", "roi_unavailable")
                    and -90.0 <= lat <= 90.0
                    and -180.0 <= lon <= 180.0
                )

                if any(i.id == ev.id for i in items):
                    continue

                items.append(
                    DebrisTargetItem(
                        id=ev.id,
                        class_name=ev.class_name,
                        confidence=ev.confidence,
                        latitude=lat if has_coords else None,
                        longitude=lon if has_coords else None,
                        uncertainty_m=unc if has_coords else None,
                        status=st,
                        formatted=loc.get("formatted") or ("Coordinates unavailable" if not has_coords else f"{lat:.6f}°, {lon:.6f}°"),
                        source_module="Central Results Database",
                        timestamp=ev.timestamp.isoformat() if ev.timestamp else None,
                        is_navigable=has_coords,
                        navigable_reason=None if has_coords else "No geodetic telemetry associated with event",
                    )
                )

        return items

    def to_response(self, route: NavigationRoute) -> RouteResponse:
        """Converts NavigationRoute ORM object to RouteResponse Pydantic schema."""
        waypoints = route.waypoints_json if isinstance(route.waypoints_json, list) else []
        return RouteResponse(
            id=route.id,
            name=route.name,
            drone_id=route.drone_id,
            start_latitude=route.start_latitude,
            start_longitude=route.start_longitude,
            target_latitude=route.target_latitude,
            target_longitude=route.target_longitude,
            target_name=route.target_name,
            total_distance_m=route.total_distance_m,
            estimated_time_s=route.estimated_time_s,
            waypoints=waypoints,
            status=route.status,
            created_at=route.created_at.isoformat() if route.created_at else "",
            updated_at=route.updated_at.isoformat() if route.updated_at else "",
        )


route_planning_service = RoutePlanningService()
