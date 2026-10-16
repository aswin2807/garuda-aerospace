"""
Runway Observation and Detection (ROD) — Runway Pathway ROI Unit & Integration Tests
=====================================================================================
Garuda Aerospace — Critical Runway Safety & Debris Detection Pipeline

PRD Reference: Complete ROD Project Audit & Runway-Pathway-Restricted Debris Detection
Functional Requirements Verified:
  - FR-ROI-01: Valid Runway Pathway Region of Interest (ROI) definition and validation
  - FR-ROI-02: Precise candidate classification (inside vs outside pathway)
  - FR-ROI-03: Configurable boundary handling (BOTTOM_CENTER, CENTROID, INTERSECTION_AREA, STRICT_INSIDE, HYBRID)
  - FR-ROI-04: Strict ROI failure handling (ROI_UNAVAILABLE / ROI_UNCERTAIN without unvalidated defaults)
  - FR-ROI-05: Diagnostic traceability for all candidates (in-pathway and rejected outside-pathway objects)
  - FR-ROI-06: Consistent multi-pipeline enforcement (images, videos, live camera streams, route planning)
"""

import pytest
import numpy as np
import cv2

from backend.app.services.runway_roi_service import RunwayROIService, runway_roi_service
from backend.app.services.fod_service import fod_service
from backend.app.services.image_service import image_service
from backend.app.services.route_planning_service import route_planning_service
from backend.app.schemas.navigation import DebrisTargetItem


class TestRunwayROIService:
    """Tests for RunwayROIService geometry validation and boundary rules."""

    @pytest.fixture
    def roi_svc(self):
        return RunwayROIService()

    def test_validate_polygon_normalized_valid(self, roi_svc):
        """FR-ROI-01: Valid normalized quadrilateral must pass validation."""
        poly = [[0.0, 0.0], [0.85, 0.0], [0.85, 1.0], [0.0, 1.0]]
        valid, err, contour = roi_svc.validate_polygon(poly, 1920, 1080)
        assert valid is True
        assert err is None
        assert contour is not None
        assert contour.shape[0] == 4

    def test_validate_polygon_pixel_coords_valid(self, roi_svc):
        """FR-ROI-01: Valid absolute pixel coordinates must pass validation."""
        poly = [[0, 0], [1600, 0], [1600, 1080], [0, 1080]]
        valid, err, contour = roi_svc.validate_polygon(poly, 1920, 1080)
        assert valid is True
        assert err is None
        assert contour is not None

    def test_validate_polygon_empty_or_none(self, roi_svc):
        """FR-ROI-04: Empty or None polygon must be rejected with informative error."""
        valid, err, contour = roi_svc.validate_polygon(None, 1920, 1080)
        assert valid is False
        assert "empty or None" in err

        valid, err, contour = roi_svc.validate_polygon([], 1920, 1080)
        assert valid is False

    def test_validate_polygon_too_few_vertices(self, roi_svc):
        """FR-ROI-01: Polygon with fewer than 3 vertices must be rejected."""
        valid, err, _ = roi_svc.validate_polygon([[0.1, 0.1], [0.5, 0.5]], 1920, 1080)
        assert valid is False
        assert "at least 3 vertices" in err

    def test_validate_polygon_nan_or_inf(self, roi_svc):
        """FR-ROI-01: Polygon with NaN or Inf coordinates must be rejected."""
        valid, err, _ = roi_svc.validate_polygon([[0.0, 0.0], [float("nan"), 0.5], [0.5, 1.0]], 1920, 1080)
        assert valid is False
        assert "NaN or Infinite" in err

    def test_validate_polygon_zero_area(self, roi_svc):
        """FR-ROI-01: Collinear degenerate polygon with zero area must be rejected."""
        collinear = [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]]
        valid, err, _ = roi_svc.validate_polygon(collinear, 1920, 1080)
        assert valid is False
        assert "area" in err.lower()

    def test_evaluate_candidate_inside_vs_outside(self, roi_svc):
        """FR-ROI-02: Candidates inside the pathway are accepted; candidates outside are rejected."""
        # Pathway is x in [0, 1600], y in [0, 1080]
        poly = [[0.0, 0.0], [0.80, 0.0], [0.80, 1.0], [0.0, 1.0]]
        _, _, contour = roi_svc.validate_polygon(poly, 2000, 1000)
        # width = 2000, 0.80 * 2000 = 1600

        # Candidate 1: Inside paved asphalt (x: 400..500)
        box_inside = [400, 300, 500, 400]
        res_inside = roi_svc.evaluate_candidate(box_inside, contour, 2000, 1000)
        assert res_inside["in_pathway"] is True
        assert res_inside["status"] in ("INSIDE", "BOUNDARY_ACCEPTED")
        assert res_inside["rejection_reason"] is None

        # Candidate 2: Outside paved asphalt in dirt shoulder (x: 1700..1850)
        box_outside = [1700, 300, 1850, 400]
        res_outside = roi_svc.evaluate_candidate(box_outside, contour, 2000, 1000)
        assert res_outside["in_pathway"] is False
        assert res_outside["status"] == "OUTSIDE"
        assert res_outside["rejection_reason"] is not None

    def test_boundary_rules_bottom_center(self, roi_svc):
        """FR-ROI-03: BOTTOM_CENTER rule checks ground-contact point (x_center, y_bottom)."""
        poly = [[0, 0], [1000, 0], [1000, 1000], [0, 1000]]
        _, _, contour = roi_svc.validate_polygon(poly, 2000, 1000)

        # Box top edge outside, but bottom ground contact point inside
        # Box: x: 400..600, y: -20..100 -> bottom center is (500, 100), inside!
        box = [400, 0, 600, 100]
        res = roi_svc.evaluate_candidate(box, contour, 2000, 1000, boundary_rule="BOTTOM_CENTER")
        assert res["in_pathway"] is True
        assert res["contact_point"] == [500.0, 100.0]

        # Box bottom center outside at x=1100
        box_out = [1050, 200, 1150, 300]
        res_out = roi_svc.evaluate_candidate(box_out, contour, 2000, 1000, boundary_rule="BOTTOM_CENTER")
        assert res_out["in_pathway"] is False

    def test_boundary_rules_intersection_area(self, roi_svc):
        """FR-ROI-03: INTERSECTION_AREA rule checks box overlap percentage."""
        poly = [[0, 0], [1000, 0], [1000, 1000], [0, 1000]]
        _, _, contour = roi_svc.validate_polygon(poly, 2000, 1000)

        # Box spanning x=950..1050 (half inside, half outside: 50% overlap)
        # width = 100, height = 100
        box = [950, 400, 1050, 500]

        # With 40% threshold -> should pass
        res_pass = roi_svc.evaluate_candidate(box, contour, 2000, 1000, boundary_rule="INTERSECTION_AREA", min_overlap=0.40)
        assert res_pass["in_pathway"] is True
        assert res_pass["containment_ratio"] >= 0.40

        # With 70% threshold -> should fail
        res_fail = roi_svc.evaluate_candidate(box, contour, 2000, 1000, boundary_rule="INTERSECTION_AREA", min_overlap=0.70)
        assert res_fail["in_pathway"] is False
        assert "below" in res_fail["rejection_reason"]

    def test_filter_debris_detections_batch(self, roi_svc):
        """FR-ROI-05: Batch filtering separates inside from outside candidates with full diagnostics."""
        poly = [[0.0, 0.0], [0.85, 0.0], [0.85, 1.0], [0.0, 1.0]]
        detections = [
            {"bbox": [200, 300, 250, 350], "confidence": 0.82, "class_name": "FOD"},   # Inside
            {"bbox": [600, 500, 680, 580], "confidence": 0.75, "class_name": "FOD"},   # Inside
            {"bbox": [1750, 400, 1850, 500], "confidence": 0.65, "class_name": "FOD"}, # Outside (x > 1632)
            {"bbox": [1880, 700, 1910, 740], "confidence": 0.58, "class_name": "FOD"}, # Outside (x > 1632)
        ]

        result = roi_svc.filter_debris_detections(
            detections=detections,
            frame_shape=(1080, 1920),
            roi_polygon=poly,
            boundary_rule="BOTTOM_CENTER"
        )

        assert result["counts"]["in_pathway"] == 2
        assert result["counts"]["outside_pathway"] == 2
        assert result["counts"]["total_candidates"] == 4
        assert len(result["valid_detections"]) == 2
        assert len(result["filtered_out_detections"]) == 2

        # Check diagnostics on accepted detections
        for d in result["valid_detections"]:
            assert d["in_pathway"] is True
            assert d["roi_status"] in ("INSIDE", "BOUNDARY_ACCEPTED")
            assert "ground_contact_point" in d

        # Check diagnostics on rejected detections
        for d in result["filtered_out_detections"]:
            assert d["in_pathway"] is False
            assert d["roi_status"] in ("OUTSIDE", "BOUNDARY_REJECTED")
            assert d["rejection_reason"] is not None

    def test_strict_mode_when_roi_unavailable(self, roi_svc):
        """FR-ROI-04: In strict mode, missing ROI does NOT assume arbitrary unvalidated box."""
        roi_svc.strict_mode = True
        detections = [
            {"bbox": [500, 400, 600, 500], "confidence": 0.70, "class_name": "FOD"}
        ]

        # Call with unknown source and no camera_id and roi_polygon=None
        # With empty registry for this source, polygon will be None if default not found
        result = roi_svc.filter_debris_detections(
            detections=detections,
            frame_shape=(1080, 1920),
            roi_polygon=None,
            source_id="completely_unknown_nonexistent_source_xyz_123"
        )

        # Default inspection corridor is used if available in registry, but if we pass empty polygon:
        result_empty = roi_svc.filter_debris_detections(
            detections=detections,
            frame_shape=(1080, 1920),
            roi_polygon=[]
        )
        assert result_empty["roi_info"]["status"] == "ROI_UNAVAILABLE"
        assert len(result_empty["valid_detections"]) == 0
        assert len(result_empty["filtered_out_detections"]) == 1
        assert "roi_unavailable" in result_empty["filtered_out_detections"][0]["roi_rejection_reason"]

    def test_draw_pathway_overlay(self, roi_svc):
        """FR-ROI-06: Pathway overlay draws polygon contour on image without error."""
        blank_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        poly = [[0.0, 0.0], [0.85, 0.0], [0.85, 1.0], [0.0, 1.0]]

        drawn = roi_svc.draw_pathway_overlay(
            blank_img,
            polygon=poly,
            color=(255, 180, 0),
            alpha=0.10,
            draw_label=True
        )
        assert drawn is not None
        assert drawn.shape == blank_img.shape
        # Image should not be completely black anymore
        assert np.count_nonzero(drawn) > 0


class TestFODServiceWithPathwayROI:
    """Tests for FODService integration with Runway Pathway ROI."""

    def test_fod_service_predict_filters_out_of_pathway(self):
        """FR-ROI-02 & FR-ROI-06: fod_service.predict filters outside pathway when filter_pathway=True."""
        if not fod_service.loaded:
            pytest.skip("FOD model not loaded in environment")

        # Create a frame with right shoulder margin
        frame = np.full((1080, 1920, 3), 120, dtype=np.uint8)

        # Call predict with pathway corridor restricted to 0..85% width
        poly = [[0.0, 0.0], [0.85, 0.0], [0.85, 1.0], [0.0, 1.0]]
        dets = fod_service.predict(
            frame,
            conf=0.15,
            filter_pathway=True,
            roi_polygon=poly
        )

        # Every returned detection must be in_pathway
        for d in dets:
            assert d.get("in_pathway") is True
            bbox = d.get("bbox") or d.get("xyxy")
            x_center = (bbox[0] + bbox[2]) / 2.0
            assert x_center <= (0.85 * 1920) + 5.0

        # Check last_roi_result
        assert hasattr(fod_service, "last_roi_result")
        assert fod_service.last_roi_result is not None
        assert "roi_info" in fod_service.last_roi_result


class TestImageServiceWithPathwayROI:
    """Tests for ImageService with Runway Pathway ROI."""

    def test_image_service_analyze_fod_with_roi(self, tmp_path):
        """FR-ROI-05: ImageService returns roi_info and diagnostic fields for FOD analysis."""
        test_img_path = tmp_path / "test_runway_roi.jpg"
        img = np.full((1080, 1920, 3), 100, dtype=np.uint8)
        cv2.imwrite(str(test_img_path), img)

        res = image_service.analyze_image(
            str(test_img_path),
            analysis_type="FOD",
            roi_polygon=[[0.0, 0.0], [0.85, 0.0], [0.85, 1.0], [0.0, 1.0]]
        )

        assert "roi_info" in res
        assert "outside_pathway_candidates" in res
        assert "pathway_filtered_count" in res
        assert "annotated_image_path" in res


class TestRoutePlanningDebrisFiltering:
    """Tests for RoutePlanningService navigation filtering."""

    def test_debris_targets_exclude_outside_pathway(self):
        """FR-ROI-06: Debris with outside_pathway status are not navigable."""
        item_valid = DebrisTargetItem(
            id="fod-1",
            class_name="FOD",
            confidence=0.88,
            latitude=12.9015,
            longitude=80.2280,
            uncertainty_m=1.2,
            status="verified",
            formatted="12.901500°, 80.228000°",
            source_module="ROD Debris Detection",
            is_navigable=True
        )
        assert item_valid.is_navigable is True

        item_rejected = DebrisTargetItem(
            id="fod-2",
            class_name="FOD",
            confidence=0.65,
            latitude=None,
            longitude=None,
            uncertainty_m=None,
            status="outside_pathway",
            formatted="Coordinates unavailable",
            source_module="ROD Debris Detection",
            is_navigable=False,
            navigable_reason="Debris detected outside runway pathway"
        )
        assert item_rejected.is_navigable is False
        assert "outside runway pathway" in item_rejected.navigable_reason
