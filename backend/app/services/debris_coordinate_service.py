import math
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from backend.app.core.logging import logger


class DebrisCoordinateService:
    """
    Runway Observation and Detection (ROD) — Debris Coordinate Estimation Service
    Implements PRD Functional Requirements FR-01 through FR-05:
      - FR-01: Coordinate formatting and uncertainty display
      - FR-02: Debris detection association and representative ground contact point
      - FR-03: Multi-method coordinate prediction (georeferenced, telemetry raycast, homography)
      - FR-04: Ground plane intersection and WGS 84 conversion
      - FR-05: Spatial uncertainty estimation distinct from YOLO detection confidence
    """

    # Earth radius in meters (WGS 84 equatorial radius)
    WGS84_A = 6378137.0
    WGS84_B = 6356752.3142
    WGS84_E2 = 0.00669437999014

    # Default operational runway center (Garuda Aerospace Runway Operations Datum)
    DEFAULT_RUNWAY_LAT = 12.901200
    DEFAULT_RUNWAY_LON = 80.227300
    DEFAULT_RUNWAY_HEADING = 184.0  # Runway 18 heading in degrees

    def __init__(self):
        # Default camera intrinsics (standard wide-angle drone inspection camera)
        self.default_hfov_deg = 84.0
        self.default_vfov_deg = 53.0

    @staticmethod
    def get_ground_contact_point(bbox: Any) -> Tuple[float, float]:
        """
        Calculates the representative point on the detected debris object (FR-04).
        For objects resting on the flat runway ground surface, the bottom-center
        of the bounding box represents the true ground contact point.
        """
        if isinstance(bbox, dict):
            x1 = float(bbox.get("x1", 0.0))
            y1 = float(bbox.get("y1", 0.0))
            x2 = float(bbox.get("x2", 0.0))
            y2 = float(bbox.get("y2", 0.0))
        elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        else:
            return 0.0, 0.0

        u = (x1 + x2) / 2.0
        v = y2  # Bottom edge on runway ground
        return u, v

    @staticmethod
    def format_coordinates(
        lat: Optional[float],
        lon: Optional[float],
        uncertainty_m: Optional[float] = None
    ) -> str:
        """
        Formats geographic coordinates into clean, standard notation (FR-01).
        Example: '12.9716° N, 80.2206° E (±1.2m)'
        """
        if lat is None or lon is None:
            return "Coordinates unavailable"

        lat_dir = "N" if lat >= 0 else "S"
        lon_dir = "E" if lon >= 0 else "W"
        unc_str = f" (±{uncertainty_m:.1f}m)" if uncertainty_m is not None else ""

        return f"{abs(lat):.6f}° {lat_dir}, {abs(lon):.6f}° {lon_dir}{unc_str}"

    @staticmethod
    def geodesic_distance_meters(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculates the precise great-circle geodesic distance in meters
        between two WGS 84 points using the Haversine formula.
        Used for ground-truth accuracy validation (Section 6).
        """
        r_earth = 6371000.0  # Mean radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlam / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
        return r_earth * c

    def predict_coordinates(
        self,
        bbox: Any,
        image_width: int = 1920,
        image_height: int = 1080,
        telemetry: Optional[Dict[str, Any]] = None,
        camera_calibration: Optional[Dict[str, Any]] = None,
        surveyed_gcp: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Estimates the geographical ground coordinates of a detected debris object (FR-03 & FR-04).
        Strictly prioritizes verified methods:
          1. Surveyed Ground Control Points / Homography
          2. Calibrated Camera & Drone Telemetry Raycasting
          3. Explicit Unavailable status if telemetry/calibration is absent.
        """
        u, v = self.get_ground_contact_point(bbox)
        w = max(1, image_width)
        h = max(1, image_height)

        # -------------------------------------------------------------
        # METHOD 1: Surveyed Homography / Planar Ground Control Points
        # -------------------------------------------------------------
        if surveyed_gcp and "homography_matrix" in surveyed_gcp:
            h_mat = surveyed_gcp["homography_matrix"]
            if len(h_mat) == 3 and len(h_mat[0]) == 3:
                # Apply 3x3 homography to [u, v, 1]
                p = [
                    h_mat[0][0] * u + h_mat[0][1] * v + h_mat[0][2],
                    h_mat[1][0] * u + h_mat[1][1] * v + h_mat[1][2],
                    h_mat[2][0] * u + h_mat[2][1] * v + h_mat[2][2],
                ]
                if abs(p[2]) > 1e-6:
                    pred_lat = p[0] / p[2]
                    pred_lon = p[1] / p[2]
                    unc_m = surveyed_gcp.get("uncertainty_m", 0.5)

                    return {
                        "latitude": round(pred_lat, 6),
                        "longitude": round(pred_lon, 6),
                        "crs": "WGS84",
                        "uncertainty_m": round(unc_m, 1),
                        "status": "verified",
                        "method": "surveyed_homography",
                        "formatted": self.format_coordinates(pred_lat, pred_lon, unc_m),
                        "ground_point_pixels": [round(u, 1), round(v, 1)],
                        "source_note": "Direct projection via surveyed runway calibration matrix"
                    }

        # -------------------------------------------------------------
        # METHOD 2: Calibrated Camera & Drone Telemetry Raycast
        # -------------------------------------------------------------
        if telemetry:
            drone_lat = telemetry.get("latitude")
            drone_lon = telemetry.get("longitude")
            drone_alt_m = telemetry.get("altitude")

            # Check if necessary telemetry coordinates exist and are physically valid
            if (
                drone_lat is not None
                and drone_lon is not None
                and drone_alt_m is not None
                and -90.0 <= drone_lat <= 90.0
                and -180.0 <= drone_lon <= 180.0
                and drone_alt_m > 1.0  # Above ground level (AGL)
            ):
                # Camera orientation
                heading_deg = float(telemetry.get("heading", telemetry.get("yaw", self.DEFAULT_RUNWAY_HEADING)))
                # Pitch: -90 is nadir (straight down), 0 is level horizon. Default to downward inspection tilt (-60 deg)
                pitch_deg = float(telemetry.get("pitch", -60.0))
                roll_deg = float(telemetry.get("roll", 0.0))

                # Camera intrinsics
                calib = camera_calibration or {}
                hfov_deg = float(calib.get("hfov_deg", self.default_hfov_deg))
                fx = float(calib.get("fx", (w / 2.0) / math.tan(math.radians(hfov_deg / 2.0))))
                fy = float(calib.get("fy", fx))
                cx = float(calib.get("cx", w / 2.0))
                cy = float(calib.get("cy", h / 2.0))

                # Ray in camera coordinates (X right, Y down, Z forward optical axis)
                rx_c = (u - cx) / fx
                ry_c = (v - cy) / fy
                rz_c = 1.0
                ray_cam_norm = math.sqrt(rx_c * rx_c + ry_c * ry_c + rz_c * rz_c)
                rx_c /= ray_cam_norm
                ry_c /= ray_cam_norm
                rz_c /= ray_cam_norm

                # Angles in radians
                pitch_rad = math.radians(pitch_deg)
                yaw_rad = math.radians(heading_deg)
                roll_rad = math.radians(roll_deg)

                # Rotate from camera frame to world North-East-Down (NED) frame
                # Camera pitch rotation around X axis (pitch down = negative angle)
                # In standard camera pose: Z is optical forward, Y is image down, X is image right.
                # When pitch = -90 (nadir), optical axis points Down (+Z in NED).
                # Pitch matrix:
                # [rx_p]   [ 1       0              0       ] [rx_c]
                # [ry_p] = [ 0   cos(pitch)    -sin(pitch)  ] [ry_c]
                # [rz_p]   [ 0   sin(pitch)     cos(pitch)  ] [rz_c]
                # Note: For pitch=-90, optical axis Z_c rotates to Down vector.
                sin_p, cos_p = math.sin(pitch_rad), math.cos(pitch_rad)
                rx_p = rx_c
                ry_p = cos_p * ry_c - sin_p * rz_c
                rz_p = sin_p * ry_c + cos_p * rz_c

                # Yaw rotation around Down (Z in NED)
                sin_y, cos_y = math.sin(yaw_rad), math.cos(yaw_rad)
                # Map to North (+X), East (+Y), Down (+Z)
                # Forward horizontal vector points in heading direction (yaw)
                ray_north = cos_y * rz_p - sin_y * rx_p
                ray_east = sin_y * rz_p + cos_y * rx_p
                ray_down = ry_p

                # Ensure ray points downwards towards the runway surface
                if ray_down > 0.08:
                    # Distance along ray to flat ground plane
                    slant_t = drone_alt_m / ray_down

                    # Ground offset in meters from drone
                    delta_north_m = slant_t * ray_north
                    delta_east_m = slant_t * ray_east

                    # Convert ground metric offset to WGS 84 latitude & longitude
                    lat_rad = math.radians(drone_lat)
                    meters_per_deg_lat = 111132.92 - 559.82 * math.cos(2.0 * lat_rad) + 1.175 * math.cos(4.0 * lat_rad)
                    meters_per_deg_lon = 111412.84 * math.cos(lat_rad) - 93.5 * math.cos(3.0 * lat_rad)

                    debris_lat = drone_lat + (delta_north_m / max(1000.0, meters_per_deg_lat))
                    debris_lon = drone_lon + (delta_east_m / max(1000.0, meters_per_deg_lon))

                    # Estimate spatial uncertainty (FR-05)
                    # Ground sampling distance (GSD) at slant distance
                    ground_dist = math.sqrt(delta_north_m ** 2 + delta_east_m ** 2)
                    slant_range = math.sqrt(ground_dist ** 2 + drone_alt_m ** 2)
                    gsd = (slant_range / fx)

                    # Bounding box localization variance + GPS receiver noise + 0.5 deg gimbal uncertainty
                    gimbal_err = slant_range * math.radians(0.5)
                    gps_err = 0.8  # RTK/WAAS enhanced drone GPS uncertainty in meters
                    total_unc_m = math.sqrt((4.0 * gsd) ** 2 + (gimbal_err) ** 2 + (gps_err) ** 2)

                    return {
                        "latitude": round(debris_lat, 6),
                        "longitude": round(debris_lon, 6),
                        "crs": "WGS84",
                        "uncertainty_m": round(total_unc_m, 1),
                        "status": "estimated",
                        "method": "calibrated_camera",
                        "formatted": self.format_coordinates(debris_lat, debris_lon, total_unc_m),
                        "ground_point_pixels": [round(u, 1), round(v, 1)],
                        "source_note": f"Estimated from drone altitude ({drone_alt_m:.1f}m) and camera geometry"
                    }

        # -------------------------------------------------------------
        # METHOD 3: Fallback when Location Data is Insufficient (FR-03)
        # -------------------------------------------------------------
        # "A detection bounding box alone cannot provide reliable latitude and longitude.
        # If the required calibration, telemetry, or mapping data is missing,
        # show 'Coordinates unavailable' rather than generating false coordinates."
        return {
            "latitude": None,
            "longitude": None,
            "crs": "WGS84",
            "uncertainty_m": None,
            "status": "unavailable",
            "method": "none",
            "formatted": "Coordinates unavailable",
            "ground_point_pixels": [round(u, 1), round(v, 1)],
            "source_note": "Camera telemetry or ground calibration not available"
        }

    def evaluate_ground_truth_accuracy(
        self,
        test_cases: List[Dict[str, Any]],
        tolerance_m: float = 3.0
    ) -> Dict[str, Any]:
        """
        Evaluates coordinate prediction accuracy against surveyed ground-truth positions (PRD Section 6).
        Calculates geodesic distance error across all valid test cases.
        Reports:
          - Valid test case count
          - Median location error (m)
          - 95th-percentile error (m)
          - Percentage within tolerance (%)
        """
        errors: List[float] = []

        for tc in test_cases:
            pred = self.predict_coordinates(
                bbox=tc.get("bbox"),
                image_width=tc.get("image_width", 1920),
                image_height=tc.get("image_height", 1080),
                telemetry=tc.get("telemetry"),
                camera_calibration=tc.get("calibration"),
                surveyed_gcp=tc.get("surveyed_gcp")
            )

            gt_lat = tc.get("gt_latitude")
            gt_lon = tc.get("gt_longitude")

            if pred["status"] != "unavailable" and gt_lat is not None and gt_lon is not None:
                err = self.geodesic_distance_meters(pred["latitude"], pred["longitude"], gt_lat, gt_lon)
                errors.append(err)

        if not errors:
            return {
                "valid_test_cases": 0,
                "median_error_m": 0.0,
                "p95_error_m": 0.0,
                "within_tolerance_pct": 0.0,
                "tolerance_threshold_m": tolerance_m,
                "status": "NO_VALID_DATA"
            }

        errors.sort()
        n = len(errors)
        med_idx = n // 2
        median_err = errors[med_idx] if n % 2 != 0 else (errors[med_idx - 1] + errors[med_idx]) / 2.0
        p95_idx = min(n - 1, int(math.ceil(0.95 * n)) - 1)
        p95_err = errors[p95_idx]

        within_tol = sum(1 for e in errors if e <= tolerance_m)
        within_pct = round((within_tol / n) * 100.0, 2)

        return {
            "valid_test_cases": n,
            "median_error_m": round(median_err, 3),
            "p95_error_m": round(p95_err, 3),
            "within_tolerance_pct": within_pct,
            "tolerance_threshold_m": tolerance_m,
            "min_error_m": round(errors[0], 3),
            "max_error_m": round(errors[-1], 3),
            "status": "VALIDATED"
        }


debris_coordinate_service = DebrisCoordinateService()
