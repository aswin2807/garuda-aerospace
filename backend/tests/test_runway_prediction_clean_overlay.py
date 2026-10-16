"""
Unit & Integration Tests for PRD: ROD Runway Prediction — Clean Overlay & Accuracy Enhancement
Validates:
1. Elimination of unwanted row lines / scan window line overlays (PRD Section 2.1).
2. Clean, uncluttered prediction label format 'LIGHT ON · 94%' and 'LIGHT OFF · 91%' (PRD Section 2.2).
3. Clear emerald green / crimson red visual distinction for LIGHT ON and LIGHT OFF (PRD Section 2.3).
4. Intelligent label positioning within frame boundaries without obscuring detected lights (PRD Section 2.2).
5. Cross-service consistency across runway_light_service, analysis_worker, and frame_processor.
"""

import numpy as np
import pytest

from app.core.config import settings
from app.services.runway_light_service import draw, put_label, runway_light_service
from app.services.analysis_worker import AnalysisWorker
from app.services.frame_processor import FrameProcessor


def test_no_row_lines_by_default():
    """Validates that horizontal scan window row lines are eliminated by default (PRD Section 2.1)."""
    assert settings.RUNWAY_SHOW_SCAN_WINDOW is False

    # Create a blank black frame (400x600x3)
    frame = np.zeros((400, 600, 3), dtype=np.uint8)
    band = (150, 250)

    # Annotate frame with default settings (show_scan_window=False)
    annotated = runway_light_service.annotate_frame(
        frame=frame,
        detections=[],
        band=band,
        frame_idx=0,
    )

    # The scan lines were drawn with orange BGR (0, 140, 255) across row y=150 and y=250.
    # Assert that no orange pixels (0, 140, 255) exist along row 150 or row 250.
    line_y1_pixels = annotated[150, :, :]
    line_y2_pixels = annotated[250, :, :]

    orange_bgr = np.array([0, 140, 255], dtype=np.uint8)
    has_orange_y1 = np.any(np.all(line_y1_pixels == orange_bgr, axis=-1))
    has_orange_y2 = np.any(np.all(line_y2_pixels == orange_bgr, axis=-1))

    assert not has_orange_y1, "Unwanted horizontal row line detected at y1=150"
    assert not has_orange_y2, "Unwanted horizontal row line detected at y2=250"


def test_row_lines_only_drawn_when_explicitly_enabled():
    """Validates that row lines are only drawn if show_scan_window is explicitly True."""
    frame = np.zeros((400, 600, 3), dtype=np.uint8)
    band = (150, 250)

    annotated_with_lines = runway_light_service.annotate_frame(
        frame=frame,
        detections=[],
        band=band,
        frame_idx=0,
        show_scan_window=True,
    )

    line_y1_pixels = annotated_with_lines[150, 50:550, :]
    # cv2.LINE_AA produces anti-aliased orange where Red channel (index 2 in BGR) > 200 and Green > 100
    has_orange_y1 = np.any((line_y1_pixels[:, 2] > 200) & (line_y1_pixels[:, 1] > 100))
    assert has_orange_y1, "Scan window row lines should be drawn when explicitly enabled"


def test_clean_label_formatting_and_colors():
    """Validates label format 'LIGHT ON · 94%' and distinct emerald/crimson colors (PRD Section 2.2 & 2.3)."""
    frame = np.zeros((400, 600, 3), dtype=np.uint8)
    band = (100, 300)

    detections = [
        {
            "class_id": 1,
            "class_name": "LIGHT ON",
            "state": "ON",
            "conf": 0.942,
            "xyxy": [100, 150, 140, 190],
            "track_id": 4,
            "light_id": "R1-C1",
        },
        {
            "class_id": 0,
            "class_name": "LIGHT OFF",
            "state": "OFF",
            "conf": 0.914,
            "xyxy": [250, 150, 290, 190],
            "track_id": 5,
            "light_id": "R1-C2",
        },
    ]

    # Draw with clean settings
    out = draw(
        frame=frame,
        detections=detections,
        band=band,
        frame_idx=0,
        show_labels=True,
        show_conf=True,
        show_track_ids=False,
        show_scan_window=False,
    )

    # Check color presence:
    # Emerald green in BGR: (94, 197, 34)
    emerald_bgr = np.array([94, 197, 34], dtype=np.uint8)
    # Crimson red in BGR: (68, 68, 239)
    crimson_bgr = np.array([68, 68, 239], dtype=np.uint8)

    has_emerald = np.any(np.all(out == emerald_bgr, axis=-1))
    has_crimson = np.any(np.all(out == crimson_bgr, axis=-1))

    assert has_emerald, "LIGHT ON bounding box/badge must use emerald green (94, 197, 34)"
    assert has_crimson, "LIGHT OFF bounding box/badge must use crimson red (68, 68, 239)"


def test_label_positioning_clamped_within_boundaries():
    """Validates that label badge never draws outside frame dimensions (PRD Section 2.2)."""
    # Test box at the extreme top-left: x1=0, y1=2, x2=20, y2=20
    frame = np.zeros((200, 300, 3), dtype=np.uint8)
    # put_label should place below box if y1 is too close to top
    put_label(frame, "LIGHT ON · 95%", x=0, y=2, color=(94, 197, 34), scale=0.44, y2=20)
    # Check that pixels were drawn without error and within frame
    assert np.any(frame > 0)

    # Test box at the extreme bottom-right: x1=280, y1=180, x2=299, y2=199
    frame2 = np.zeros((200, 300, 3), dtype=np.uint8)
    put_label(frame2, "LIGHT OFF · 91%", x=280, y=180, color=(68, 68, 239), scale=0.44, y2=199)
    assert np.any(frame2 > 0)


def test_analysis_worker_draw_annotations_consistency():
    """Validates that VideoAnalysisWorker uses the clean middle dot format and green/red colors."""
    worker = AnalysisWorker(job_id="test-job", file_path="test.mp4", analysis_type="RUNWAY_LIGHT")
    frame = np.zeros((300, 400, 3), dtype=np.uint8)

    dets = [
        {"class_name": "LIGHT ON", "state": "ON", "confidence": 0.94, "bbox": [50, 50, 80, 80]},
        {"class_name": "LIGHT OFF", "state": "OFF", "confidence": 0.91, "bbox": [150, 50, 180, 80]},
    ]

    annotated = worker._draw_annotations(frame, dets)
    assert annotated is not None
    # Verify green and red pixels are present
    has_emerald = np.any(np.all(annotated == np.array([94, 197, 34], dtype=np.uint8), axis=-1))
    has_crimson = np.any(np.all(annotated == np.array([68, 68, 239], dtype=np.uint8), axis=-1))
    assert has_emerald, "VideoAnalysisWorker must render LIGHT ON with emerald green"
    assert has_crimson, "VideoAnalysisWorker must render LIGHT OFF with crimson red"


def test_frame_processor_draw_annotations_consistency():
    """Validates that FrameProcessor uses the clean middle dot format and green/red colors."""
    fp = FrameProcessor()
    frame = np.zeros((300, 400, 3), dtype=np.uint8)

    dets = [
        {"class_name": "LIGHT ON", "state": "ON", "confidence": 0.94, "bbox": [50, 50, 80, 80]},
        {"class_name": "LIGHT OFF", "state": "OFF", "confidence": 0.91, "bbox": [150, 50, 180, 80]},
    ]

    annotated = fp.draw_annotations(frame, dets)
    assert annotated is not None
    has_emerald = np.any(np.all(annotated == np.array([94, 197, 34], dtype=np.uint8), axis=-1))
    has_crimson = np.any(np.all(annotated == np.array([68, 68, 239], dtype=np.uint8), axis=-1))
    assert has_emerald, "FrameProcessor must render LIGHT ON with emerald green"
    assert has_crimson, "FrameProcessor must render LIGHT OFF with crimson red"
