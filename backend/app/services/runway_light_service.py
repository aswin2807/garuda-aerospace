import os
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import cv2
import numpy as np
import torch

from backend.app.core.config import settings
from backend.app.core.logging import logger

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    logger.warning("Ultralytics not installed. Falling back to PyTorch for Runway Light service.")

# Class Constants (PRD Section 3 & 7)
CLASS_NAMES = {0: "LIGHT OFF", 1: "LIGHT ON"}
CLASS_SHORT = {0: "OFF", 1: "ON"}
CLASS_COLORS = {0: (0, 0, 255), 1: (0, 0, 255)}


def get_optimal_device() -> torch.device:
    """Returns optimal torch device: CUDA, Apple Silicon MPS, or CPU."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def enhance_frame(frame: np.ndarray, mode: str) -> np.ndarray:
    """Enhance frame using adaptive CLAHE, brighten, or darken (PRD Section 9)."""
    if mode == "none":
        return frame

    if mode in {"clahe", "auto"}:
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced_l = clahe.apply(l_channel)
        return cv2.cvtColor(cv2.merge((enhanced_l, a_channel, b_channel)), cv2.COLOR_LAB2BGR)

    if mode == "brighten":
        gamma = 0.72
    elif mode == "darken":
        gamma = 1.35
    else:
        return frame

    table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(frame, table)


def choose_preprocess_mode(frame: np.ndarray, band: Tuple[int, int], requested_mode: str) -> str:
    """Dynamically choose preprocessing based on scan band brightness (PRD Section 9)."""
    if requested_mode != "auto":
        return requested_mode
    y1, y2 = band
    if y2 <= y1 or frame.size == 0:
        return "clahe"
    band_img = frame[y1:y2]
    if band_img.size == 0:
        return "clahe"
    gray = cv2.cvtColor(band_img, cv2.COLOR_BGR2GRAY)
    mean_v = float(np.mean(gray))
    if mean_v < 80:
        return "brighten"
    if mean_v > 165:
        return "darken"
    return "clahe"


def scan_window(height: int, start_ratio: float = 0.52, height_ratio: float = 0.20) -> Tuple[int, int]:
    """Calculates scan window bounds dynamically from image height (PRD Section 8)."""
    band_h = int(round(height * height_ratio))
    y1 = int(round(height * start_ratio))
    y2 = min(height, y1 + band_h)
    return y1, y2


def tile_origins(width: int, height: int, tile_size: int = 640, stride: int = 480, center_y: float = 0.0) -> List[Tuple[int, int]]:
    """Calculates origins for overlapping horizontal scan tiles (PRD Section 10)."""
    y0 = max(0, min(height - tile_size, int(round(center_y - tile_size / 2))))
    if width <= tile_size:
        return [(0, y0)]
    xs = list(range(0, max(1, width - tile_size + 1), stride))
    if xs[-1] != width - tile_size:
        xs.append(width - tile_size)
    return [(x, y0) for x in xs]


def overlap_ratio(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    """Calculates intersection over minimum area between two bounding boxes (PRD Section 11)."""
    xx1 = max(a[0], b[0])
    yy1 = max(a[1], b[1])
    xx2 = min(a[2], b[2])
    yy2 = min(a[3], b[3])
    inter = max(0.0, xx2 - xx1) * max(0.0, yy2 - yy1)
    area_a = max(1.0, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(1.0, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / min(area_a, area_b)


def box_iou(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    """Calculates standard IoU between two bounding boxes."""
    xx1 = max(a[0], b[0])
    yy1 = max(a[1], b[1])
    xx2 = min(a[2], b[2])
    yy2 = min(a[3], b[3])
    inter = max(0.0, xx2 - xx1) * max(0.0, yy2 - yy1)
    area_a = max(1.0, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(1.0, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / (area_a + area_b - inter + 1e-6)


def nms(detections: List[Dict[str, Any]], threshold: float = 0.35, min_center_dist: float = 8.0) -> List[Dict[str, Any]]:
    """
    Non-maximum suppression based on confidence, overlap ratio, IoU, and center proximity (PRD Section 11).
    Deduplicates overlapping sliding-window tiles and full-frame passes.
    """
    sorted_dets = sorted(detections, key=lambda d: d.get("conf", 0.0), reverse=True)
    kept: List[Dict[str, Any]] = []
    for det in sorted_dets:
        xyxy = det["xyxy"]
        cx = (xyxy[0] + xyxy[2]) / 2.0
        cy = (xyxy[1] + xyxy[3]) / 2.0
        is_dup = False
        for old in kept:
            old_xyxy = old["xyxy"]
            if overlap_ratio(xyxy, old_xyxy) >= threshold or box_iou(xyxy, old_xyxy) >= threshold:
                is_dup = True
                break
            old_cx = (old_xyxy[0] + old_xyxy[2]) / 2.0
            old_cy = (old_xyxy[1] + old_xyxy[3]) / 2.0
            if ((cx - old_cx) ** 2 + (cy - old_cy) ** 2) < (min_center_dist ** 2):
                is_dup = True
                break
        if not is_dup:
            kept.append(det)
    return kept


def detection_quality_ok(
    frame: np.ndarray,
    det: Dict[str, Any],
    post_filter: bool = True,
    paint_reject: bool = True,
    min_box_side: float = 1.0,
    max_box_side: float = 150.0,
    max_box_area: float = 15000.0,
    min_aspect: float = 0.25,
    max_aspect: float = 4.0,
    off_max_mean_v: float = 168.0,
    off_min_sat_for_bright: float = 45.0,
    off_min_contrast: float = 0.0,
    off_min_conf: float = 0.20,
    on_min_contrast: float = 5.0,
    on_min_conf: float = 0.20,
) -> bool:
    """
    Quality filtering and false-positive / paint rejection (PRD Section 12, 13 & 34).
    Validates bounding box dimensions, aspect ratio, HSV brightness/contrast,
    and rejects runway white paint markings.
    """
    if not post_filter:
        return True

    x1, y1, x2, y2 = [int(round(v)) for v in det["xyxy"]]
    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)
    area = bw * bh
    aspect = bw / float(bh)

    # 1. Box geometry validation (PRD Section 12 & 34)
    if min(bw, bh) < min_box_side:
        return False
    if max(bw, bh) > max_box_side:
        return False
    if area > max_box_area:
        return False
    if aspect < min_aspect or aspect > max_aspect:
        return False

    # 2. Local patch extraction
    h, w = frame.shape[:2]
    pad = max(4, int(max(bw, bh) * 1.4))
    px1 = max(0, x1 - pad)
    py1 = max(0, y1 - pad)
    px2 = min(w, x2 + pad)
    py2 = min(h, y2 + pad)
    patch = frame[py1:py2, px1:px2]
    box_crop = frame[y1:y2, x1:x2]
    if patch.size == 0 or box_crop.size == 0:
        return False

    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    sat = float(np.mean(hsv[:, :, 1]))
    val = hsv[:, :, 2].astype(np.float32)
    mean_v = float(np.mean(val))
    contrast = float(np.percentile(val, 95) - np.percentile(val, 20))
    conf = float(det.get("conf", 0.0))

    # 3. Paint rejection logic (PRD Section 13 & 34)
    # White paint pixels: very high value, very low saturation
    if paint_reject and det.get("class_id") == 0:
        box_hsv = cv2.cvtColor(box_crop, cv2.COLOR_BGR2HSV)
        box_sat = float(np.mean(box_hsv[:, :, 1]))
        box_v = float(np.mean(box_hsv[:, :, 2]))
        box_white_fraction = float(np.mean((box_hsv[:, :, 2] > 190) & (box_hsv[:, :, 1] < 45)))
        if box_white_fraction > 0.40 or (box_v > off_max_mean_v and box_sat < off_min_sat_for_bright):
            # Rejection: likely painted runway markings or threshold stripes
            return False

    # 4. Class-specific rules
    if det.get("class_id") == 0:  # LIGHT OFF
        if mean_v > off_max_mean_v and sat < off_min_sat_for_bright:
            return False
        if off_min_contrast > 0 and contrast < off_min_contrast and conf < 0.45:
            return False
        if conf < off_min_conf:
            return False

    elif det.get("class_id") == 1:  # LIGHT ON
        if contrast < on_min_contrast and conf < 0.45:
            return False
        if conf < on_min_conf:
            return False

    return True


def refine_detection_box(
    frame: np.ndarray,
    det: Dict[str, Any],
    refine_boxes: bool = False,
    refine_only_on: bool = True,
    refine_margin: int = 2,
    min_display_box: int = 8,
) -> Dict[str, Any]:
    """
    Safely clips bounding box to image bounds and optionally tightens around bright light beacon (PRD Section 12).
    Keeps model's original calibrated bounding box by default to avoid box bloating or centroid drift.
    """
    x1, y1, x2, y2 = [float(v) for v in det["xyxy"]]
    h, w = frame.shape[:2]
    # Always clamp to valid frame boundaries
    x1 = max(0.0, min(x1, float(w - 1)))
    y1 = max(0.0, min(y1, float(h - 1)))
    x2 = max(x1 + 1.0, min(x2, float(w)))
    y2 = max(y1 + 1.0, min(y2, float(h)))

    if not refine_boxes:
        det_copy = det.copy()
        det_copy["xyxy"] = (x1, y1, x2, y2)
        return det_copy

    if det.get("class_id") == 0 and refine_only_on:
        det_copy = det.copy()
        det_copy["xyxy"] = (x1, y1, x2, y2)
        return det_copy

    bw = max(1.0, x2 - x1)
    bh = max(1.0, y2 - y1)
    pad = max(4, int(max(bw, bh) * 1.2))
    px1 = max(0, int(round(x1)) - pad)
    py1 = max(0, int(round(y1)) - pad)
    px2 = min(w, int(round(x2)) + pad)
    py2 = min(h, int(round(y2)) + pad)
    patch = frame[py1:py2, px1:px2]
    if patch.size == 0:
        det_copy = det.copy()
        det_copy["xyxy"] = (x1, y1, x2, y2)
        return det_copy

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    thresh_val = max(float(np.percentile(blur, 90)), float(np.mean(blur) + np.std(blur) * 1.2))
    mask = (blur >= thresh_val).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        det_copy = det.copy()
        det_copy["xyxy"] = (x1, y1, x2, y2)
        return det_copy

    old_cx = (x1 + x2) / 2.0 - px1
    old_cy = (y1 + y2) / 2.0 - py1
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 2:
            continue
        rx, ry, rw, rh = cv2.boundingRect(contour)
        cx = rx + rw / 2.0
        cy = ry + rh / 2.0
        dist = ((cx - old_cx) ** 2 + (cy - old_cy) ** 2) ** 0.5
        if dist > max(pad, 8):
            continue
        candidates.append((area / (1.0 + dist), rx, ry, rw, rh))
    if not candidates:
        det_copy = det.copy()
        det_copy["xyxy"] = (x1, y1, x2, y2)
        return det_copy

    _, rx, ry, rw, rh = max(candidates, key=lambda item: item[0])
    nx1 = max(0.0, float(px1 + rx - refine_margin))
    ny1 = max(0.0, float(py1 + ry - refine_margin))
    nx2 = min(float(w), float(px1 + rx + rw + refine_margin))
    ny2 = min(float(h), float(py1 + ry + rh + refine_margin))

    # Reject refinement if it drifted excessively from original box
    ref_iou = box_iou((x1, y1, x2, y2), (nx1, ny1, nx2, ny2))
    if ref_iou < 0.40:
        det_copy = det.copy()
        det_copy["xyxy"] = (x1, y1, x2, y2)
        return det_copy

    refined = det.copy()
    refined["xyxy"] = (nx1, ny1, nx2, ny2)
    return refined


def validate_neighboring_lights(
    detections: List[Dict[str, Any]],
    max_dx: float = 300.0,
    max_dy: float = 60.0,
    require_neighbor_for_off: bool = False,
) -> List[Dict[str, Any]]:
    """
    Validates detections against neighboring lights along runway patterns (PRD Section 14).
    Runway lights occur in structured rows:
    ● ON ● ON ● OFF ● ON ● ON
    Flags OFF detections surrounded by ON lights as high-confidence fault candidates.
    """
    on_lights = [d for d in detections if d.get("class_id") == 1]
    validated = []
    for det in detections:
        if det.get("class_id") == 0 and not det.get("inferred"):
            cx = (det["xyxy"][0] + det["xyxy"][2]) / 2
            cy = (det["xyxy"][1] + det["xyxy"][3]) / 2
            left_neighbors = [
                o for o in on_lights
                if 0 < (cx - (o["xyxy"][0] + o["xyxy"][2]) / 2) <= max_dx
                and abs(cy - (o["xyxy"][1] + o["xyxy"][3]) / 2) <= max_dy
            ]
            right_neighbors = [
                o for o in on_lights
                if 0 < ((o["xyxy"][0] + o["xyxy"][2]) / 2 - cx) <= max_dx
                and abs(cy - (o["xyxy"][1] + o["xyxy"][3]) / 2) <= max_dy
            ]
            if left_neighbors and right_neighbors:
                det["neighbor_context"] = "SURROUNDED_BY_ON"
                det["fault_candidate"] = True
            elif left_neighbors or right_neighbors:
                det["neighbor_context"] = "NEARBY_ON"
            else:
                det["neighbor_context"] = "ISOLATED"
                if require_neighbor_for_off:
                    continue  # Reject isolated OFF detections if strict pattern validation required
        validated.append(det)
    return validated


def infer_missing_off_from_rows(
    detections: List[Dict[str, Any]],
    frame_idx: int = 0,
    fps: float = 25.0,
    infer_missing_off: bool = False,
    infer_min_on_conf: float = 0.30,
    infer_min_row_lights: int = 4,
    infer_row_bin: int = 36,
    infer_min_spacing: float = 18.0,
    infer_max_spacing: float = 260.0,
    infer_gap_ratio: float = 1.65,
    infer_max_missing_per_gap: int = 3,
    infer_max_box: int = 34,
    min_display_box: int = 10,
    infer_off_conf: float = 0.80,
) -> List[Dict[str, Any]]:
    """
    Infers missing OFF lights from row spacing analysis (PRD Section 14 & 18).
    Creates state='OFF-GAP', inferred=True detections.
    """
    if not infer_missing_off:
        return []

    on_detections = [d for d in detections if d.get("class_id") == 1 and d.get("conf", 0.0) >= infer_min_on_conf]
    if len(on_detections) < infer_min_row_lights:
        return []

    rows: Dict[int, List[Dict[str, Any]]] = {}
    for det in on_detections:
        x1, y1, x2, y2 = det["xyxy"]
        cy = (y1 + y2) / 2
        rows.setdefault(int(cy // infer_row_bin), []).append(det)

    inferred: List[Dict[str, Any]] = []
    for row in rows.values():
        if len(row) < infer_min_row_lights:
            continue

        row = sorted(row, key=lambda d: (d["xyxy"][0] + d["xyxy"][2]) / 2)
        centers = [((d["xyxy"][0] + d["xyxy"][2]) / 2, (d["xyxy"][1] + d["xyxy"][3]) / 2) for d in row]
        gaps = [centers[i + 1][0] - centers[i][0] for i in range(len(centers) - 1)]
        useful_gaps = [g for g in gaps if infer_min_spacing <= g <= infer_max_spacing]
        if len(useful_gaps) < 2:
            continue

        spacing = float(np.median(useful_gaps))
        box_sizes = [max(d["xyxy"][2] - d["xyxy"][0], d["xyxy"][3] - d["xyxy"][1]) for d in row]
        box = int(max(min_display_box, min(infer_max_box, np.median(box_sizes) * 1.6)))

        for i, gap in enumerate(gaps):
            missing_count = int(round(gap / spacing)) - 1
            if missing_count <= 0 or missing_count > infer_max_missing_per_gap:
                continue
            if gap < spacing * infer_gap_ratio:
                continue

            lx, ly = centers[i]
            rx, ry = centers[i + 1]
            for step in range(1, missing_count + 1):
                ratio = step / (missing_count + 1)
                cx = lx + (rx - lx) * ratio
                cy = ly + (ry - ly) * ratio
                if any(((cx - ox) ** 2 + (cy - oy) ** 2) ** 0.5 < spacing * 0.35 for ox, oy in centers):
                    continue
                inferred.append({
                    "frame": frame_idx,
                    "time_sec": frame_idx / max(1.0, fps),
                    "class_id": 0,
                    "class_name": "LIGHT OFF",
                    "state": "OFF-GAP",
                    "conf": infer_off_conf,
                    "xyxy": (
                        float(cx - box / 2),
                        float(cy - box / 2),
                        float(cx + box / 2),
                        float(cy + box / 2),
                    ),
                    "inferred": True,
                })

    return nms(inferred, threshold=0.2)


def draw_corner_box(
    img: np.ndarray,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: Tuple[int, int, int],
    thickness: int = 2,
    corner: int = 14,
):
    """Draws tech HUD corner accents for bounding boxes (PRD Section 23)."""
    x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
    corner = max(6, min(corner, (x2 - x1) // 2, (y2 - y1) // 2))
    cv2.line(img, (x1, y1), (x1 + corner, y1), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1, y1), (x1, y1 + corner), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y1), (x2 - corner, y1), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y1), (x2, y1 + corner), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1, y2), (x1 + corner, y2), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1, y2), (x1, y2 - corner), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y2), (x2 - corner, y2), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y2), (x2, y2 - corner), color, thickness, cv2.LINE_AA)


def put_label(
    img: np.ndarray,
    text: str,
    x: int,
    y: int,
    color: Tuple[int, int, int],
    scale: float = 0.44,
    y2: Optional[int] = None,
):
    """
    Draws compact, crisp HUD label with solid background (PRD Section 2.2).
    Intelligently positions above or below the bounding box without obscuring the light fixture.
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    img_h, img_w = img.shape[:2]

    pad_x = 4
    pad_y = 3
    pill_w = tw + (pad_x * 2)
    pill_h = th + baseline + (pad_y * 2)

    # Position intelligently: above box by default; below box if near top of image
    if y2 is not None and (y - pill_h < 4):
        top_y = min(img_h - pill_h - 2, int(y2) + 2)
    else:
        top_y = max(2, int(y) - pill_h - 2)

    left_x = max(2, min(int(x), img_w - pill_w - 2))
    bottom_y = top_y + pill_h

    bg1 = (left_x, top_y)
    bg2 = (left_x + pill_w, bottom_y)

    # Solid colored badge matching bounding box
    cv2.rectangle(img, bg1, bg2, color, -1)
    # Subtle dark border around pill for crisp separation from bright/dark backgrounds
    cv2.rectangle(img, bg1, bg2, (18, 18, 18), 1, cv2.LINE_AA)
    # Crisp white typography
    text_origin = (left_x + pad_x, top_y + th + pad_y)
    cv2.putText(img, text, text_origin, font, scale, (255, 255, 255), thickness, cv2.LINE_AA)


def draw(
    frame: np.ndarray,
    detections: List[Dict[str, Any]],
    band: Tuple[int, int],
    frame_idx: int = 0,
    fps: float = 25.0,
    scale: float = 1.0,
    box_style: str = "full",
    box_thickness: int = 2,
    corner_length: int = 14,
    show_labels: bool = True,
    show_conf: bool = True,
    show_track_ids: bool = False,
    show_scan_window: bool = False,
    show_banner: bool = True,
    label_scale: float = 0.44,
) -> np.ndarray:
    """
    Renders clean annotated frame without unwanted row lines or cluttered labels (PRD Section 2.1 & 2.2).
    LIGHT ON: Emerald Green (34, 197, 94)
    LIGHT OFF: Crimson Red (239, 68, 68)
    Label format: 'LIGHT ON · 94%' / 'LIGHT OFF · 91%'
    """
    out_w = int(round(frame.shape[1] * scale))
    out_h = int(round(frame.shape[0] * scale))
    out = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA) if scale != 1.0 else frame.copy()
    y1, y2 = int(round(band[0] * scale)), int(round(band[1] * scale))

    # Scan window guideline indicators (only if explicitly enabled; disabled by default to remove row lines)
    if show_scan_window:
        cv2.line(out, (0, y1), (out.shape[1], y1), (0, 140, 255), 1, cv2.LINE_AA)
        cv2.line(out, (0, y2), (out.shape[1], y2), (0, 140, 255), 1, cv2.LINE_AA)

    counts = {0: 0, 1: 0}
    for det in detections:
        cls = det.get("class_id", 0)
        counts[cls] = counts.get(cls, 0) + 1

        # Clear, distinct visual representation (PRD Section 2.3)
        state_str = str(det.get("slot_status", det.get("state", "OFF" if cls == 0 else "ON"))).upper()
        if cls == 1 or "ON" in state_str:
            box_color = (94, 197, 34)   # Emerald Green in BGR (RGB: 34, 197, 94)
            display_class = "LIGHT ON"
        else:
            box_color = (68, 68, 239)   # Crimson Red in BGR (RGB: 239, 68, 68)
            display_class = "LIGHT OFF"

        box = det.get("xyxy")
        if box is None:
            box = det.get("bbox")
        if box is None and "bbox_dict" in det:
            bd = det["bbox_dict"]
            box = [bd.get("x1", 0), bd.get("y1", 0), bd.get("x2", 0), bd.get("y2", 0)]
        if box is None:
            continue
        x1, by1, x2, by2 = [int(round(v * scale)) for v in box[:4]]

        if box_style == "corner":
            draw_corner_box(out, x1, by1, x2, by2, box_color, max(2, box_thickness), corner_length)
        else:
            cv2.rectangle(out, (x1, by1), (x2, by2), box_color, max(2, box_thickness), cv2.LINE_AA)

        label_conf = float(det.get("display_conf", det.get("conf", 0.0)))
        conf_pct = int(round(label_conf * 100))
        track_suffix = f" #{det['track_id']}" if show_track_ids and "track_id" in det else ""

        # Clean, concise prediction label format (PRD Section 2.2): "LIGHT ON · 94%" or "LIGHT OFF · 91%"
        if show_conf:
            label = f"{display_class}{track_suffix} · {conf_pct}%"
        else:
            label = f"{display_class}{track_suffix}"

        if show_labels:
            put_label(out, label, x1, by1, box_color, label_scale, y2=by2)

    if show_banner:
        on_cnt = counts.get(1, 0)
        off_cnt = counts.get(0, 0)
        banner_text = f"RUNWAY LIGHT DETECTION  |  LIGHT ON: {on_cnt}  |  LIGHT OFF: {off_cnt}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.44
        thickness = 1
        (tw, th), bl = cv2.getTextSize(banner_text, font, font_scale, thickness)
        bx1, by1 = 12, 10
        bx2, by2 = 12 + tw + 20, 10 + th + 14

        # Semi-transparent sleek dark pill background
        overlay = out.copy()
        cv2.rectangle(overlay, (bx1, by1), (bx2, by2), (20, 24, 30), -1)
        cv2.addWeighted(overlay, 0.75, out, 0.25, 0, out)
        cv2.rectangle(out, (bx1, by1), (bx2, by2), (55, 65, 80), 1, cv2.LINE_AA)
        cv2.putText(out, banner_text, (bx1 + 10, by1 + th + 6), font, font_scale, (240, 243, 246), thickness, cv2.LINE_AA)

    return out


LIGHT_FAULT_CONFIRM_FRAMES = 5


class RunwayLightSlot:
    """Represents a single persistent physical runway light slot in the row/column grid."""
    def __init__(
        self,
        light_id: str,
        row_id: int,
        column_id: int,
        track_id: Optional[int] = None,
        bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
        initial_state: str = "ON",
        initial_conf: float = 0.50,
    ):
        self.light_id = light_id  # e.g., "R1-C1"
        self.row_id = row_id
        self.column_id = column_id
        self.track_id = track_id
        self.bbox = bbox
        self.cx = (bbox[0] + bbox[2]) / 2.0
        self.cy = (bbox[1] + bbox[3]) / 2.0
        self.last_seen_frame: int = 0
        self.first_seen_frame: int = 0
        self.observations: List[Tuple[int, str, float]] = []
        self.consecutive_off: int = 0
        self.consecutive_on: int = 0

        # Eliminate "UNKNOWN" - Slot status strictly aligns with model classes: "ON" or "OFF"
        is_init_off = (initial_state in ("OFF", "OFF-GAP") or "OFF" in str(initial_state).upper() or str(initial_state) == "0")
        self.confirmed_state: str = "OFF" if is_init_off else "ON"
        if is_init_off:
            self.consecutive_off = 1
            self.consecutive_on = 0
            self.is_confirmed_fault = (initial_conf >= 0.60)
        else:
            self.consecutive_on = 1
            self.consecutive_off = 0
            self.is_confirmed_fault = False

        self.confidence: float = float(initial_conf)
        self.total_observations: int = 0

    def update(
        self,
        frame_idx: int,
        state: str,
        conf: float,
        bbox: Tuple[float, float, float, float]
    ):
        if self.first_seen_frame == 0:
            self.first_seen_frame = frame_idx
        self.last_seen_frame = frame_idx
        self.total_observations += 1
        self.bbox = bbox
        self.cx = (bbox[0] + bbox[2]) / 2.0
        self.cy = (bbox[1] + bbox[3]) / 2.0
        self.confidence = float(conf)
        self.observations.append((frame_idx, state, conf))

        # Multi-frame temporal validation (LIGHT_FAULT_CONFIRM_FRAMES = 5)
        is_off_obs = (state in ("OFF", "OFF-GAP") or "OFF" in str(state).upper() or str(state) == "0")
        is_on_obs = (state == "ON" or "ON" in str(state).upper() or str(state) == "1")

        if is_off_obs:
            self.consecutive_off += 1
            self.consecutive_on = 0
            if self.consecutive_off >= LIGHT_FAULT_CONFIRM_FRAMES:
                self.confirmed_state = "OFF"
                self.is_confirmed_fault = True
            elif conf >= 0.35:
                self.confirmed_state = "OFF"
        elif is_on_obs:
            self.consecutive_on += 1
            self.consecutive_off = 0
            self.confirmed_state = "ON"
            self.is_confirmed_fault = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "light_id": self.light_id,
            "row_id": self.row_id,
            "column_id": self.column_id,
            "status": self.confirmed_state,
            "confidence": round(self.confidence, 3),
            "is_confirmed": self.is_confirmed_fault,
            "track_id": self.track_id,
            "consecutive_off": self.consecutive_off,
            "total_observations": self.total_observations,
            "bbox": [
                round(self.bbox[0], 1),
                round(self.bbox[1], 1),
                round(self.bbox[2], 1),
                round(self.bbox[3], 1),
            ],
        }


class RunwayGridTracker:
    """
    Maintains persistent row/column grid slots, multi-frame state validation,
    perspective tilt-compensated row clustering, and deduplicated physical light counts across video frames.
    """
    def __init__(self):
        self.slots: Dict[str, RunwayLightSlot] = {}
        self.track_to_slot: Dict[int, str] = {}
        self.row_anchors: Dict[int, float] = {}  # row_id -> smoothed y_comp
        self.track_to_row: Dict[int, int] = {}   # track_id -> row_id
        self.next_row_id: int = 1

    def reset(self):
        self.slots.clear()
        self.track_to_slot.clear()
        self.row_anchors.clear()
        self.track_to_row.clear()
        self.next_row_id = 1

    def _estimate_perspective_slope(self, detections: List[Dict[str, Any]]) -> float:
        """
        Estimates the runway transversal tilt slope dy/dx from horizontal neighbor pairs.
        Prevents tilted runway rows from being split into vertical fragments.
        """
        if len(detections) < 2:
            return 0.0

        centers = []
        for d in detections:
            box = d.get("xyxy") or d.get("bbox")
            if box is not None and len(box) >= 4:
                centers.append(((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0))

        slopes = []
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                xi, yi = centers[i]
                xj, yj = centers[j]
                dx = abs(xj - xi)
                dy = yj - yi if xj > xi else yi - yj
                # Neighbor pairs along the same row are typically separated horizontally
                # by 30 to 450 px with small vertical deviation <= 60 px
                if 30.0 <= dx <= 450.0 and abs(dy) <= 60.0:
                    slopes.append(dy / dx)

        if len(slopes) >= 3:
            med_slope = float(np.median(slopes))
            # Clamp to plausible tilt range [-0.25, 0.25] (~14 degrees)
            return max(-0.25, min(0.25, med_slope))
        return 0.0

    def update(self, detections: List[Dict[str, Any]], frame_idx: int) -> List[Dict[str, Any]]:
        if not detections:
            return detections

        slope = self._estimate_perspective_slope(detections)

        # Compute tilt-compensated y coordinate for all detections
        for det in detections:
            box = det.get("xyxy") or det.get("bbox")
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            det["_cx"] = cx
            det["_cy"] = cy
            det["_y_comp"] = cy - slope * cx

        # Sort detections by y_comp (top-to-bottom: Row 1 farthest/top to nearest/bottom)
        dets_sorted_y = sorted(detections, key=lambda d: d["_y_comp"])
        heights = [d["xyxy"][3] - d["xyxy"][1] for d in detections]
        med_h = float(np.median(heights)) if heights else 20.0
        row_thresh = max(35.0, med_h * 1.5)

        # Cluster detections into rows along y_comp
        clusters: List[List[Dict[str, Any]]] = []
        current_cluster = [dets_sorted_y[0]]
        current_y_comp = dets_sorted_y[0]["_y_comp"]

        for d in dets_sorted_y[1:]:
            d_y = d["_y_comp"]
            if abs(d_y - current_y_comp) <= row_thresh:
                current_cluster.append(d)
                current_y_comp = sum(x["_y_comp"] for x in current_cluster) / len(current_cluster)
            else:
                clusters.append(current_cluster)
                current_cluster = [d]
                current_y_comp = d_y
        if current_cluster:
            clusters.append(current_cluster)

        # Persistent Row Matching across frames
        # Sort clusters top-to-bottom by average y_comp
        clusters_with_mean = [
            (sum(d["_y_comp"] for d in c) / len(c), c)
            for c in clusters
        ]
        clusters_with_mean.sort(key=lambda item: item[0])

        assigned_row_clusters: List[Tuple[int, List[Dict[str, Any]]]] = []
        used_row_ids = set()

        for y_mean, cluster in clusters_with_mean:
            # 1. Match row by track votes
            track_votes: Dict[int, int] = {}
            for d in cluster:
                tid = d.get("track_id")
                if tid is not None and tid in self.track_to_row:
                    r = self.track_to_row[tid]
                    track_votes[r] = track_votes.get(r, 0) + 1

            matched_row = None
            if track_votes:
                best_r = max(track_votes, key=track_votes.get)
                if best_r not in used_row_ids:
                    matched_row = best_r

            # 2. Match row by spatial proximity to existing row anchors
            if matched_row is None:
                best_dist = float("inf")
                for r, r_y in self.row_anchors.items():
                    if r in used_row_ids:
                        continue
                    dist = abs(r_y - y_mean)
                    if dist <= row_thresh * 1.5 and dist < best_dist:
                        best_dist = dist
                        matched_row = r

            # 3. If unmatched, allocate row number
            if matched_row is None:
                matched_row = self.next_row_id
                while matched_row in self.row_anchors:
                    matched_row += 1
                self.next_row_id = max(self.next_row_id, matched_row + 1)

            used_row_ids.add(matched_row)

            # Update smoothed row anchor
            if matched_row in self.row_anchors:
                self.row_anchors[matched_row] = self.row_anchors[matched_row] * 0.7 + y_mean * 0.3
            else:
                self.row_anchors[matched_row] = y_mean

            # Map tracks to row
            for d in cluster:
                tid = d.get("track_id")
                if tid is not None:
                    self.track_to_row[tid] = matched_row

            assigned_row_clusters.append((matched_row, cluster))

        # Re-sort assigned rows so row indices correspond cleanly top-to-bottom
        assigned_row_clusters.sort(key=lambda item: self.row_anchors.get(item[0], 0.0))

        updated_slot_ids = set()

        for row_num, group in assigned_row_clusters:
            # Geometric horizontal sort within row: Left to Right
            group_sorted_x = sorted(group, key=lambda d: d["_cx"])

            for c_idx, det in enumerate(group_sorted_x):
                track_id = det.get("track_id")
                slot: Optional[RunwayLightSlot] = None

                # 1. Match by persistent track_id
                if track_id is not None and track_id in self.track_to_slot:
                    assigned_id = self.track_to_slot[track_id]
                    if assigned_id in self.slots and assigned_id not in updated_slot_ids:
                        slot = self.slots[assigned_id]

                # 2. Match by spatial proximity to existing slot in this row
                if slot is None:
                    det_box = det["xyxy"]
                    det_cx = det["_cx"]
                    det_cy = det["_cy"]
                    best_slot = None
                    best_dist = float("inf")

                    for s_id, s in self.slots.items():
                        if s_id in updated_slot_ids or s.row_id != row_num:
                            continue
                        dist = ((s.cx - det_cx) ** 2 + (s.cy - det_cy) ** 2) ** 0.5
                        iou = box_iou(s.bbox, det_box)
                        if (iou >= 0.20 or dist <= row_thresh * 1.5) and dist < best_dist:
                            best_dist = dist
                            best_slot = s

                    if best_slot is not None:
                        slot = best_slot
                        if track_id is not None:
                            self.track_to_slot[track_id] = slot.light_id

                # 3. New slot allocation if unmatched
                if slot is None:
                    col_num = c_idx + 1
                    light_id = f"R{row_num}-C{col_num}"
                    while light_id in self.slots and light_id in updated_slot_ids:
                        col_num += 1
                        light_id = f"R{row_num}-C{col_num}"

                    if light_id not in self.slots:
                        init_state = det.get("state", "OFF" if det.get("class_id") == 0 else "ON")
                        init_conf = float(det.get("display_conf", det.get("conf", 0.50)))
                        self.slots[light_id] = RunwayLightSlot(
                            light_id=light_id,
                            row_id=row_num,
                            column_id=col_num,
                            track_id=track_id,
                            bbox=det["xyxy"],
                            initial_state=init_state,
                            initial_conf=init_conf,
                        )
                    slot = self.slots[light_id]
                    if track_id is not None:
                        self.track_to_slot[track_id] = slot.light_id

                # Update slot state
                updated_slot_ids.add(slot.light_id)
                state_str = det.get("state", "OFF" if det.get("class_id") == 0 else "ON").upper()
                conf_val = float(det.get("display_conf", det.get("conf", 0.0)))
                slot.update(frame_idx, state_str, conf_val, det["xyxy"])

                # Tag detection dict
                det["light_id"] = slot.light_id
                det["row_id"] = slot.row_id
                det["column_id"] = slot.column_id
                det["slot_status"] = slot.confirmed_state
                det["is_confirmed"] = slot.is_confirmed_fault
                det["status"] = slot.confirmed_state

        return detections

    def get_grid_matrix(self) -> List[Dict[str, Any]]:
        sorted_slots = sorted(self.slots.values(), key=lambda s: (s.row_id, s.column_id))
        return [s.to_dict() for s in sorted_slots]

    def get_summary_stats(self) -> Dict[str, Any]:
        slots_list = list(self.slots.values())
        total_lights = len(slots_list)
        lights_on = sum(1 for s in slots_list if s.confirmed_state == "ON")
        lights_off = sum(1 for s in slots_list if s.confirmed_state == "OFF")
        lights_unknown = sum(1 for s in slots_list if s.confirmed_state == "UNKNOWN")
        confirmed_faults = sum(1 for s in slots_list if s.is_confirmed_fault and s.confirmed_state == "OFF")

        rows = set(s.row_id for s in slots_list)
        cols = set(s.column_id for s in slots_list)
        total_rows = len(rows)
        total_columns = max(cols) if cols else 0

        confs = [s.confidence for s in slots_list if s.confidence > 0 and s.confirmed_state != "UNKNOWN"]
        avg_conf = float(np.mean(confs)) if confs else 0.0

        # Row results
        row_results = []
        for r in sorted(rows):
            r_slots = [s for s in slots_list if s.row_id == r]
            r_on = sum(1 for s in r_slots if s.confirmed_state == "ON")
            r_off = sum(1 for s in r_slots if s.confirmed_state == "OFF")
            r_unk = sum(1 for s in r_slots if s.confirmed_state == "UNKNOWN")
            r_faults = sum(1 for s in r_slots if s.is_confirmed_fault and s.confirmed_state == "OFF")
            row_results.append({
                "row": f"Row {r}",
                "total": len(r_slots),
                "on": r_on,
                "off": r_off,
                "unknown": r_unk,
                "faults": r_faults
            })

        # Faults list
        faults = []
        for s in sorted(slots_list, key=lambda x: (x.row_id, x.column_id)):
            if s.is_confirmed_fault and s.confirmed_state == "OFF":
                faults.append({
                    "light_id": s.light_id,
                    "row_id": s.row_id,
                    "column_id": s.column_id,
                    "status": "OFF",
                    "confidence": round(s.confidence, 3),
                    "consecutive_off": s.consecutive_off,
                    "total_observations": s.total_observations,
                    "bbox": [round(v, 1) for v in s.bbox]
                })

        return {
            "total_lights": total_lights,
            "lights_on": lights_on,
            "lights_off": lights_off,
            "lights_unknown": lights_unknown,
            "confirmed_faults": confirmed_faults,
            "total_rows": total_rows,
            "total_columns": total_columns,
            "average_confidence": round(avg_conf, 3),
            "matrix": [s.to_dict() for s in sorted(slots_list, key=lambda x: (x.row_id, x.column_id))],
            "row_results": row_results,
            "faults": faults
        }


class ByteTrackLite:
    """Lightweight IoU-based multi-object tracker for runway lights (PRD Section 17)."""
    def __init__(
        self,
        high_thresh: float = 0.20,
        low_thresh: float = 0.10,
        match_iou: float = 0.20,
        max_age: int = 30,
        smooth_alpha: float = 0.65,
    ):
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.match_iou = match_iou
        self.max_age = max_age
        self.smooth_alpha = smooth_alpha
        self.tracks: List[Dict[str, Any]] = []
        self.next_id = 1

    def _match(self, tracks: List[Dict[str, Any]], detections: List[Dict[str, Any]]):
        matches = []
        used_tracks = set()
        used_dets = set()
        candidates = []
        for ti, track in enumerate(tracks):
            for di, det in enumerate(detections):
                iou = box_iou(track["xyxy"], det["xyxy"])
                if iou >= self.match_iou:
                    candidates.append((iou, ti, di))
                else:
                    # Spatial proximity fallback for small runway light fixtures (PRD Section 17 & 21)
                    tx1, ty1, tx2, ty2 = track["xyxy"]
                    dx1, dy1, dx2, dy2 = det["xyxy"]
                    tcx, tcy = (tx1 + tx2) / 2.0, (ty1 + ty2) / 2.0
                    dcx, dcy = (dx1 + dx2) / 2.0, (dy1 + dy2) / 2.0
                    dist = ((tcx - dcx) ** 2 + (tcy - dcy) ** 2) ** 0.5
                    if dist <= 12.0:
                        synth_iou = max(0.20, 1.0 - (dist / 16.0))
                        candidates.append((synth_iou, ti, di))
        for _, ti, di in sorted(candidates, reverse=True):
            if ti in used_tracks or di in used_dets:
                continue
            used_tracks.add(ti)
            used_dets.add(di)
            matches.append((ti, di))
        return matches, used_tracks, used_dets

    def _update_track(self, track: Dict[str, Any], det: Dict[str, Any], frame_idx: int):
        old = np.array(track["xyxy"], dtype=np.float32)
        new = np.array(det["xyxy"], dtype=np.float32)
        smoothed = old * self.smooth_alpha + new * (1.0 - self.smooth_alpha)
        track.update(det)
        track["xyxy"] = tuple(float(v) for v in smoothed)
        track["last_frame"] = frame_idx
        track["age"] = 0
        track["hits"] = track.get("hits", 0) + 1

    def update(self, detections: List[Dict[str, Any]], frame_idx: int) -> List[Dict[str, Any]]:
        for track in self.tracks:
            track["age"] = track.get("age", 0) + 1

        high = [d for d in detections if d.get("conf", 0.0) >= self.high_thresh]
        low = [d for d in detections if self.low_thresh <= d.get("conf", 0.0) < self.high_thresh]

        active_tracks = [t for t in self.tracks if t.get("age", 0) <= self.max_age]
        matches, used_tracks, used_high = self._match(active_tracks, high)
        for ti, di in matches:
            self._update_track(active_tracks[ti], high[di], frame_idx)

        unmatched_tracks = [t for i, t in enumerate(active_tracks) if i not in used_tracks]
        low_matches, used_low_tracks, _ = self._match(unmatched_tracks, low)
        for ti, di in low_matches:
            self._update_track(unmatched_tracks[ti], low[di], frame_idx)

        for di, det in enumerate(high):
            if di in used_high:
                continue
            det_copy = det.copy()
            det_copy["track_id"] = self.next_id
            det_copy["last_frame"] = frame_idx
            det_copy["age"] = 0
            det_copy["hits"] = 1
            self.next_id += 1
            self.tracks.append(det_copy)

        self.tracks = [t for t in self.tracks if t.get("age", 0) <= self.max_age]
        return self.visible()

    def step(self) -> List[Dict[str, Any]]:
        for track in self.tracks:
            track["age"] = track.get("age", 0) + 1
        self.tracks = [t for t in self.tracks if t.get("age", 0) <= self.max_age]
        return self.visible()

    def visible(self) -> List[Dict[str, Any]]:
        visible_tracks = []
        for track in self.tracks:
            if track.get("hits", 0) < 1:
                continue
            det = track.copy()
            age = det.get("age", 0)
            det["display_conf"] = max(0.05, det.get("conf", 0.0) * (1.0 - min(age, self.max_age) / (self.max_age + 1)))
            if age > 0 and det["display_conf"] < 0.20:
                continue
            visible_tracks.append(det)
        return visible_tracks


class RunwayLightService:
    """
    Production Runway Light Detection & Tracking Service (PRD Section 3, 7, 8, 15, 34).
    Integrates the uploaded Jetson navigation light detection algorithms into the
    FastAPI / WebSocket runtime pipeline.
    """
    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence: Optional[float] = None,
        iou: Optional[float] = None,
        scan_start: Optional[float] = None,
        scan_height: Optional[float] = None,
        tile_size: Optional[int] = None,
        tile_stride: Optional[int] = None,
        detect_stride: Optional[int] = None,
        preprocess: Optional[str] = None,
        tracking: Optional[bool] = None,
        paint_reject: Optional[bool] = None,
        refine_boxes: Optional[bool] = None,
        infer_missing_off: Optional[bool] = None,
    ):
        self.model_path = model_path or settings.RUNWAY_LIGHT_MODEL_PATH
        self.confidence = confidence if confidence is not None else settings.RUNWAY_LIGHT_CONFIDENCE
        self.iou = iou if iou is not None else settings.IOU_THRESHOLD
        self.scan_start = scan_start if scan_start is not None else settings.RUNWAY_SCAN_START
        self.scan_height = scan_height if scan_height is not None else settings.RUNWAY_SCAN_HEIGHT
        self.tile_size = tile_size if tile_size is not None else settings.RUNWAY_TILE_SIZE
        self.tile_stride = tile_stride if tile_stride is not None else settings.RUNWAY_TILE_STRIDE
        self.detect_stride = detect_stride if detect_stride is not None else settings.RUNWAY_DETECT_STRIDE
        self.preprocess = preprocess if preprocess is not None else settings.RUNWAY_PREPROCESS
        self.tracking = tracking if tracking is not None else settings.RUNWAY_TRACKING
        self.paint_reject = paint_reject if paint_reject is not None else settings.RUNWAY_PAINT_REJECT
        self.refine_boxes = refine_boxes if refine_boxes is not None else settings.RUNWAY_REFINE_BOXES
        self.infer_missing_off = infer_missing_off if infer_missing_off is not None else settings.RUNWAY_INFER_MISSING_OFF

        self.device = get_optimal_device()
        self.model = None
        self.classes: Dict[int, str] = {0: "LIGHT OFF", 1: "LIGHT ON"}
        self.loaded: bool = False
        self.status: str = "INITIALIZING"
        self.error: Optional[str] = None

        self.tracker = ByteTrackLite(
            high_thresh=self.confidence,
            low_thresh=max(0.05, self.confidence * 0.5),
            match_iou=self.iou
        )
        self.grid_tracker = RunwayGridTracker()
        self.frame_counter: int = 0
        self.last_detections: List[Dict[str, Any]] = []
        self.last_band: Tuple[int, int] = (0, 0)

        self.load_model()

    def load_model(self) -> bool:
        self.status = "LOADING"
        resolved_path = Path(self.model_path)
        if not resolved_path.is_absolute():
            resolved_path = Path(os.getcwd()) / resolved_path

        if not resolved_path.exists():
            fallback = Path(os.getcwd()) / "ml_engine" / "models" / "runway_light_best.pt"
            if fallback.exists():
                resolved_path = fallback

        if not resolved_path.exists():
            self.status = "ERROR"
            self.error = f"Runway Light model file not found at: {resolved_path}"
            logger.error(self.error)
            return False

        logger.info(f"[RUNWAY_LIGHT_SERVICE] Loading Runway Light model from {resolved_path} onto {self.device}")
        try:
            if ULTRALYTICS_AVAILABLE:
                try:
                    self.model = YOLO(str(resolved_path))
                    if hasattr(self.model, "names") and self.model.names:
                        raw_names = self.model.names
                        normalized = {}
                        for k, v in raw_names.items():
                            v_str = str(v).strip()
                            if v_str.lower() == "off":
                                normalized[int(k)] = "LIGHT OFF"
                            elif v_str.lower() == "on":
                                normalized[int(k)] = "LIGHT ON"
                            else:
                                normalized[int(k)] = v_str
                        self.classes = normalized
                    self.loaded = True
                    self.status = "READY"
                    self.model_path = str(resolved_path)
                    logger.info(f"[RUNWAY_LIGHT_SERVICE] Runway Light model loaded via Ultralytics with classes {self.classes}")
                    return True
                except Exception as ex_ultra:
                    logger.warning(f"[RUNWAY_LIGHT_SERVICE] Ultralytics loading failed: {ex_ultra}. Trying PyTorch...")

            checkpoint = torch.load(str(resolved_path), map_location=self.device, weights_only=False)
            if isinstance(checkpoint, dict):
                raw_names = checkpoint.get("classes") or checkpoint.get("names") or {}
                normalized = {}
                for k, v in raw_names.items():
                    v_str = str(v).strip()
                    if v_str.lower() == "off":
                        normalized[int(k)] = "LIGHT OFF"
                    elif v_str.lower() == "on":
                        normalized[int(k)] = "LIGHT ON"
                    else:
                        normalized[int(k)] = v_str
                if normalized:
                    self.classes = normalized
            self.model = checkpoint
            self.loaded = True
            self.status = "READY"
            self.model_path = str(resolved_path)
            logger.info(f"[RUNWAY_LIGHT_SERVICE] Runway Light checkpoint loaded via PyTorch with classes {self.classes}")
            return True
        except Exception as e:
            self.status = "ERROR"
            self.error = str(e)
            logger.error(f"[RUNWAY_LIGHT_SERVICE] Failed to load Runway Light model: {e}")
            return False

    def detect_scan_window(
        self,
        frame: np.ndarray,
        frame_idx: int = 0,
        fps: float = 25.0,
        conf_override: Optional[float] = None
    ) -> Tuple[List[Dict[str, Any]], Tuple[int, int]]:
        """
        Executes the scan-window detection pipeline (PRD Section 8-15).
        """
        h, w = frame.shape[:2]
        conf = conf_override if conf_override is not None else self.confidence
        y1, y2 = scan_window(h, self.scan_start, self.scan_height)
        self.last_band = (y1, y2)

        preprocess_mode = choose_preprocess_mode(frame, (y1, y2), self.preprocess)
        model_frame = enhance_frame(frame, preprocess_mode)
        origins = tile_origins(w, h, self.tile_size, self.tile_stride, (y1 + y2) / 2)

        crops = [model_frame[y : y + self.tile_size, x : x + self.tile_size] for x, y in origins]
        detections: List[Dict[str, Any]] = []

        if ULTRALYTICS_AVAILABLE and isinstance(self.model, YOLO):
            # 1. Full-frame inference pass across the entire image
            try:
                full_results = self.model.predict(
                    model_frame,
                    imgsz=min(1280, max(640, max(w, h))),
                    conf=conf,
                    iou=self.iou,
                    device=str(self.device),
                    verbose=False,
                )
                if full_results and len(full_results) > 0:
                    for box in full_results[0].boxes:
                        cls = int(box.cls[0].item())
                        bconf = float(box.conf[0].item())
                        bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                        detections.append({
                            "frame": frame_idx,
                            "time_sec": frame_idx / max(1.0, fps),
                            "class_id": cls,
                            "class_name": self.classes.get(cls, CLASS_NAMES.get(cls, str(cls))),
                            "state": CLASS_SHORT.get(cls, str(cls)),
                            "conf": bconf,
                            "xyxy": (bx1, by1, bx2, by2),
                        })
            except Exception as e_full:
                logger.debug(f"[RUNWAY_LIGHT_SERVICE] Full-frame pass error: {e_full}")

            # 2. Tiled crops for ultra-high-resolution detail
            if crops and len(crops) > 1:
                try:
                    results = self.model.predict(
                        crops,
                        imgsz=min(640, self.tile_size),
                        conf=conf,
                        iou=self.iou,
                        device=str(self.device),
                        verbose=False,
                    )
                    for (x0, y0), result in zip(origins, results):
                        for box in result.boxes:
                            cls = int(box.cls[0].item())
                            bconf = float(box.conf[0].item())
                            x1, by1, x2, by2 = box.xyxy[0].tolist()
                            gx1 = x1 + x0
                            gy1 = by1 + y0
                            gx2 = x2 + x0
                            gy2 = by2 + y0
                            detections.append({
                                "frame": frame_idx,
                                "time_sec": frame_idx / max(1.0, fps),
                                "class_id": cls,
                                "class_name": self.classes.get(cls, CLASS_NAMES.get(cls, str(cls))),
                                "state": CLASS_SHORT.get(cls, str(cls)),
                                "conf": bconf,
                                "xyxy": (gx1, gy1, gx2, gy2),
                            })
                except Exception as e:
                    logger.error(f"[RUNWAY_LIGHT_SERVICE] Scan window prediction error: {e}")

        # Post-processing steps: NMS, box refinement, quality filtering, paint rejection, neighbor validation, gap inference
        detections = nms(detections, threshold=self.iou)
        detections = [refine_detection_box(frame, det, refine_boxes=self.refine_boxes) for det in detections]
        detections = [
            det for det in detections
            if detection_quality_ok(
                frame,
                det,
                post_filter=True,
                paint_reject=self.paint_reject,
                min_box_side=settings.RUNWAY_MIN_BOX_SIDE,
                max_box_side=settings.RUNWAY_MAX_BOX_SIDE,
                max_box_area=settings.RUNWAY_MAX_BOX_AREA,
                min_aspect=settings.RUNWAY_MIN_ASPECT,
                max_aspect=settings.RUNWAY_MAX_ASPECT,
                off_min_conf=settings.RUNWAY_OFF_MIN_CONF,
                on_min_conf=settings.RUNWAY_ON_MIN_CONF,
            )
        ]
        detections = validate_neighboring_lights(detections)
        detections.extend(infer_missing_off_from_rows(
            detections,
            frame_idx=frame_idx,
            fps=fps,
            infer_missing_off=self.infer_missing_off
        ))

        return detections, (y1, y2)

    def predict(
        self,
        frame: np.ndarray,
        conf: Optional[float] = None,
        iou: Optional[float] = None,
        frame_idx: Optional[int] = None,
        fps: float = 25.0,
        force_detect: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Unified prediction entry point for live video stream frames.
        Supports detect_stride optimization and ByteTrackLite tracking (PRD Section 16 & 17).
        """
        if not self.loaded or self.model is None:
            return []

        if conf is not None:
            self.tracker.high_thresh = float(conf)
            self.tracker.low_thresh = max(0.05, float(conf) * 0.5)

        idx = frame_idx if frame_idx is not None else self.frame_counter
        self.frame_counter += 1

        is_detect_frame = force_detect or (idx % max(1, self.detect_stride) == 0)

        if is_detect_frame or not self.tracking or not self.last_detections:
            raw_dets, band = self.detect_scan_window(frame, frame_idx=idx, fps=fps, conf_override=conf)
            self.last_band = band
            if self.tracking:
                tracked = self.tracker.update(raw_dets, idx)
                if not tracked and raw_dets:
                    for di, d in enumerate(raw_dets):
                        if "track_id" not in d:
                            d["track_id"] = di + 1
                    tracked = raw_dets
                self.last_detections = tracked
            else:
                for di, d in enumerate(raw_dets):
                    if "track_id" not in d:
                        d["track_id"] = di + 1
                self.last_detections = raw_dets
        else:
            if self.tracking:
                self.last_detections = self.tracker.step()

        # Update persistent row/column grid slots
        self.grid_tracker.update(self.last_detections, idx)

        # Format into Unified Detection JSON (PRD Section 19 & 26)
        formatted: List[Dict[str, Any]] = []
        for det in self.last_detections:
            gx1, gy1, gx2, gy2 = det["xyxy"]
            x1, y1, x2, y2 = [int(round(coord)) for coord in (gx1, gy1, gx2, gy2)]
            cls_id = det.get("class_id", 0)
            cls_name = det.get("class_name", self.classes.get(cls_id, "LIGHT OFF" if cls_id == 0 else "LIGHT ON"))
            state = det.get("state", "OFF" if cls_id == 0 else "ON")
            score = float(det.get("display_conf", det.get("conf", 0.0)))

            item: Dict[str, Any] = {
                "model": "runway_light",
                "class_id": cls_id,
                "class_name": cls_name,
                "state": state,
                "confidence": round(score, 3),
                "bbox": [x1, y1, x2, y2],
                "xyxy": [x1, y1, x2, y2],
                "bbox_dict": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "bbox_xywh": [x1, y1, max(0, x2 - x1), max(0, y2 - y1)],
                "inferred": det.get("inferred", False),
            }
            if "track_id" in det:
                item["track_id"] = det["track_id"]
            if "light_id" in det:
                item["light_id"] = det["light_id"]
            if "row_id" in det:
                item["row_id"] = det["row_id"]
            if "column_id" in det:
                item["column_id"] = det["column_id"]
            if "slot_status" in det:
                item["slot_status"] = det["slot_status"]
                item["status"] = det["slot_status"]
            if "is_confirmed" in det:
                item["is_confirmed"] = det["is_confirmed"]
            if "fault_candidate" in det:
                item["fault_candidate"] = det["fault_candidate"]
            if "neighbor_context" in det:
                item["neighbor_context"] = det["neighbor_context"]

            formatted.append(item)

        return formatted

    def reset_grid(self):
        """Resets tracker and grid slot state for a new session or video."""
        self.tracker = ByteTrackLite()
        self.grid_tracker.reset()
        self.frame_counter = 0
        self.last_detections = []
        self.last_band = (0, 0)

    def get_summary_stats(self) -> Dict[str, Any]:
        """Returns deduplicated summary statistics, grid matrix, and fault records."""
        return self.grid_tracker.get_summary_stats()

    def get_grid_matrix(self) -> List[Dict[str, Any]]:
        """Returns persistent row/column matrix slots."""
        return self.grid_tracker.get_grid_matrix()

    def annotate_frame(
        self,
        frame: np.ndarray,
        detections: Optional[List[Dict[str, Any]]] = None,
        band: Optional[Tuple[int, int]] = None,
        frame_idx: int = 0,
        fps: float = 25.0,
        scale: float = 1.0,
        show_scan_window: Optional[bool] = None,
        show_banner: Optional[bool] = None,
    ) -> np.ndarray:
        """Draws clean visual overlay on frame (PRD Section 2)."""
        dets = detections if detections is not None else self.last_detections
        b = band if band is not None else self.last_band
        if b == (0, 0):
            b = scan_window(frame.shape[0], self.scan_start, self.scan_height)
        return draw(
            frame=frame,
            detections=dets,
            band=b,
            frame_idx=frame_idx,
            fps=fps,
            scale=scale,
            box_style=settings.RUNWAY_BOX_STYLE,
            box_thickness=settings.RUNWAY_BOX_THICKNESS,
            corner_length=settings.RUNWAY_CORNER_LENGTH,
            show_labels=settings.RUNWAY_SHOW_LABELS,
            show_conf=settings.RUNWAY_SHOW_CONF,
            show_track_ids=settings.RUNWAY_SHOW_TRACK_IDS,
            show_scan_window=show_scan_window if show_scan_window is not None else settings.RUNWAY_SHOW_SCAN_WINDOW,
            show_banner=show_banner if show_banner is not None else settings.RUNWAY_SHOW_BANNER,
        )


runway_light_service = RunwayLightService()
