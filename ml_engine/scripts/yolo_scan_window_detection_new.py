import argparse
import csv
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


CLASS_NAMES = {0: "LIGHT OFF", 1: "LIGHT ON"}
CLASS_SHORT = {0: "OFF", 1: "ON"}
CLASS_COLORS = {0: (0, 0, 255), 1: (0, 255, 0)}


def enhance_frame(frame, mode):
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
        raise ValueError(f"Unsupported preprocess mode: {mode}")

    table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(frame, table)


def choose_preprocess_mode(frame, band, requested_mode):
    if requested_mode != "auto":
        return requested_mode
    y1, y2 = band
    band_img = frame[y1:y2]
    gray = cv2.cvtColor(band_img, cv2.COLOR_BGR2GRAY)
    mean_v = float(np.mean(gray))
    if mean_v < 80:
        return "brighten"
    if mean_v > 165:
        return "darken"
    return "clahe"


def detection_quality_ok(frame, det, args):
    if not getattr(args, "post_filter", True):
        return True

    x1, y1, x2, y2 = [int(round(v)) for v in det["xyxy"]]
    h, w = frame.shape[:2]
    pad = max(4, int(max(x2 - x1, y2 - y1) * 1.4))
    px1 = max(0, x1 - pad)
    py1 = max(0, y1 - pad)
    px2 = min(w, x2 + pad)
    py2 = min(h, y2 + pad)
    patch = frame[py1:py2, px1:px2]
    if patch.size == 0:
        return False

    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    sat = float(np.mean(hsv[:, :, 1]))
    val = hsv[:, :, 2].astype(np.float32)
    mean_v = float(np.mean(val))
    contrast = float(np.percentile(val, 95) - np.percentile(val, 20))

    off_max_mean_v = getattr(args, "off_max_mean_v", 168.0)
    off_min_sat_for_bright = getattr(args, "off_min_sat_for_bright", 45.0)
    off_min_contrast = getattr(args, "off_min_contrast", 18.0)
    off_min_conf = getattr(args, "off_min_conf", 0.30)
    on_min_contrast = getattr(args, "on_min_contrast", 10.0)

    # OFF false positives often come from white threshold paint and runway stains.
    if det["class_id"] == 0:
        if mean_v > off_max_mean_v and sat < off_min_sat_for_bright:
            return False
        if contrast < off_min_contrast:
            return False
        if det["conf"] < off_min_conf:
            return False

    # ON lights should be compact, bright, or locally distinct.
    if det["class_id"] == 1 and contrast < on_min_contrast and det["conf"] < 0.45:
        return False

    return True


def scan_window(height, start_ratio, height_ratio):
    band_h = int(round(height * height_ratio))
    y1 = int(round(height * start_ratio))
    y2 = min(height, y1 + band_h)
    return y1, y2


def tile_origins(width, height, tile_size, stride, center_y):
    y0 = max(0, min(height - tile_size, int(round(center_y - tile_size / 2))))
    xs = list(range(0, max(1, width - tile_size + 1), stride))
    if xs[-1] != width - tile_size:
        xs.append(width - tile_size)
    return [(x, y0) for x in xs]


def overlap_ratio(a, b):
    xx1 = max(a[0], b[0])
    yy1 = max(a[1], b[1])
    xx2 = min(a[2], b[2])
    yy2 = min(a[3], b[3])
    inter = max(0, xx2 - xx1) * max(0, yy2 - yy1)
    area_a = max(1, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(1, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / min(area_a, area_b)


def nms(detections, threshold=0.35):
    detections = sorted(detections, key=lambda d: d["conf"], reverse=True)
    kept = []
    for det in detections:
        if all(overlap_ratio(det["xyxy"], old["xyxy"]) < threshold for old in kept):
            kept.append(det)
    return kept


def box_iou(a, b):
    xx1 = max(a[0], b[0])
    yy1 = max(a[1], b[1])
    xx2 = min(a[2], b[2])
    yy2 = min(a[3], b[3])
    inter = max(0, xx2 - xx1) * max(0, yy2 - yy1)
    area_a = max(1, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(1, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / (area_a + area_b - inter + 1e-6)


class ByteTrackLite:
    def __init__(self, high_thresh=0.45, low_thresh=0.15, match_iou=0.20, max_age=30, smooth_alpha=0.65):
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.match_iou = match_iou
        self.max_age = max_age
        self.smooth_alpha = smooth_alpha
        self.tracks = []
        self.next_id = 1

    def _match(self, tracks, detections):
        matches = []
        used_tracks = set()
        used_dets = set()
        candidates = []
        for ti, track in enumerate(tracks):
            for di, det in enumerate(detections):
                if track["class_id"] != det["class_id"]:
                    continue
                iou = box_iou(track["xyxy"], det["xyxy"])
                if iou >= self.match_iou:
                    candidates.append((iou, ti, di))
        for _, ti, di in sorted(candidates, reverse=True):
            if ti in used_tracks or di in used_dets:
                continue
            used_tracks.add(ti)
            used_dets.add(di)
            matches.append((ti, di))
        return matches, used_tracks, used_dets

    def _update_track(self, track, det, frame_idx):
        old = np.array(track["xyxy"], dtype=np.float32)
        new = np.array(det["xyxy"], dtype=np.float32)
        smoothed = old * self.smooth_alpha + new * (1.0 - self.smooth_alpha)
        track.update(det)
        track["xyxy"] = tuple(float(v) for v in smoothed)
        track["track_id"] = track["track_id"]
        track["last_frame"] = frame_idx
        track["age"] = 0
        track["hits"] += 1

    def update(self, detections, frame_idx):
        for track in self.tracks:
            track["age"] += 1

        high = [d for d in detections if d["conf"] >= self.high_thresh]
        low = [d for d in detections if self.low_thresh <= d["conf"] < self.high_thresh]

        active_tracks = [t for t in self.tracks if t["age"] <= self.max_age]
        matches, used_tracks, used_high = self._match(active_tracks, high)
        for ti, di in matches:
            self._update_track(active_tracks[ti], high[di], frame_idx)

        unmatched_tracks = [t for i, t in enumerate(active_tracks) if i not in used_tracks]
        low_matches, used_low_tracks, used_low = self._match(unmatched_tracks, low)
        for ti, di in low_matches:
            self._update_track(unmatched_tracks[ti], low[di], frame_idx)

        for di, det in enumerate(high):
            if di in used_high:
                continue
            det = det.copy()
            det["track_id"] = self.next_id
            det["last_frame"] = frame_idx
            det["age"] = 0
            det["hits"] = 1
            self.next_id += 1
            self.tracks.append(det)

        self.tracks = [t for t in self.tracks if t["age"] <= self.max_age]
        return self.visible()

    def step(self):
        for track in self.tracks:
            track["age"] += 1
        self.tracks = [t for t in self.tracks if t["age"] <= self.max_age]
        return self.visible()

    def visible(self):
        visible_tracks = []
        for track in self.tracks:
            if track["hits"] < 1:
                continue
            det = track.copy()
            # Fade stale tracks from display confidence.
            det["display_conf"] = max(0.05, det["conf"] * (1.0 - min(det["age"], self.max_age) / (self.max_age + 1)))
            if det["age"] > 0 and det["display_conf"] < 0.20:
                continue
            visible_tracks.append(det)
        return visible_tracks


def refine_detection_box(frame, det, args):
    if not getattr(args, "refine_boxes", True):
        return det
    if det["class_id"] == 0 and getattr(args, "refine_only_on", True):
        return det

    x1, y1, x2, y2 = [int(round(v)) for v in det["xyxy"]]
    h, w = frame.shape[:2]
    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)
    pad = max(6, int(max(bw, bh) * 1.8))
    px1 = max(0, x1 - pad)
    py1 = max(0, y1 - pad)
    px2 = min(w, x2 + pad)
    py2 = min(h, y2 + pad)
    patch = frame[py1:py2, px1:px2]
    if patch.size == 0:
        return det

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    thresh_val = max(float(np.percentile(blur, 90)), float(np.mean(blur) + np.std(blur) * 1.2))
    mask = (blur >= thresh_val).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return det

    old_cx = (x1 + x2) / 2 - px1
    old_cy = (y1 + y2) / 2 - py1
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 2:
            continue
        rx, ry, rw, rh = cv2.boundingRect(contour)
        cx = rx + rw / 2
        cy = ry + rh / 2
        dist = ((cx - old_cx) ** 2 + (cy - old_cy) ** 2) ** 0.5
        if dist > max(pad, 10):
            continue
        candidates.append((area / (1 + dist), rx, ry, rw, rh))
    if not candidates:
        return det

    _, rx, ry, rw, rh = max(candidates, key=lambda item: item[0])
    margin = getattr(args, "refine_margin", 4)
    nx1 = max(0, px1 + rx - margin)
    ny1 = max(0, py1 + ry - margin)
    nx2 = min(w, px1 + rx + rw + margin)
    ny2 = min(h, py1 + ry + rh + margin)

    min_size = getattr(args, "min_display_box", 10)
    cx = (nx1 + nx2) / 2
    cy = (ny1 + ny2) / 2
    if nx2 - nx1 < min_size:
        nx1 = max(0, cx - min_size / 2)
        nx2 = min(w, cx + min_size / 2)
    if ny2 - ny1 < min_size:
        ny1 = max(0, cy - min_size / 2)
        ny2 = min(h, cy + min_size / 2)

    refined = det.copy()
    refined["xyxy"] = (float(nx1), float(ny1), float(nx2), float(ny2))
    return refined


def infer_missing_off_from_rows(detections, frame_idx, fps, args):
    if not getattr(args, "infer_missing_off", False):
        return []

    infer_min_on_conf = getattr(args, "infer_min_on_conf", 0.30)
    infer_min_row_lights = getattr(args, "infer_min_row_lights", 4)
    infer_row_bin = getattr(args, "infer_row_bin", 36)
    infer_min_spacing = getattr(args, "infer_min_spacing", 18.0)
    infer_max_spacing = getattr(args, "infer_max_spacing", 260.0)
    infer_gap_ratio = getattr(args, "infer_gap_ratio", 1.65)
    infer_max_missing_per_gap = getattr(args, "infer_max_missing_per_gap", 3)
    infer_max_box = getattr(args, "infer_max_box", 34)
    min_display_box = getattr(args, "min_display_box", 10)
    infer_off_conf = getattr(args, "infer_off_conf", 0.80)

    on_detections = [d for d in detections if d["class_id"] == 1 and d["conf"] >= infer_min_on_conf]
    if len(on_detections) < infer_min_row_lights:
        return []

    rows = {}
    for det in on_detections:
        x1, y1, x2, y2 = det["xyxy"]
        cy = (y1 + y2) / 2
        rows.setdefault(int(cy // infer_row_bin), []).append(det)

    inferred = []
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
                inferred.append(
                    {
                        "frame": frame_idx,
                        "time_sec": frame_idx / fps,
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
                    }
                )

    return nms(inferred, threshold=0.2)


def detect_scan_window(model, frame, frame_idx, fps, args):
    h, w = frame.shape[:2]
    scan_start = getattr(args, "scan_start", 0.52)
    scan_height = getattr(args, "scan_height", 0.20)
    tile_size = getattr(args, "tile_size", 640)
    tile_stride = getattr(args, "tile_stride", 480)
    conf = getattr(args, "conf", 0.25)
    iou = getattr(args, "iou", 0.45)
    imgsz = getattr(args, "imgsz", 640)
    device = getattr(args, "device", "0")
    tta = getattr(args, "tta", False)
    preprocess = getattr(args, "preprocess", "auto")

    y1, y2 = scan_window(h, scan_start, scan_height)
    preprocess_mode = choose_preprocess_mode(frame, (y1, y2), preprocess)
    model_frame = enhance_frame(frame, preprocess_mode)
    origins = tile_origins(w, h, tile_size, tile_stride, (y1 + y2) / 2)
    crops = [model_frame[y : y + tile_size, x : x + tile_size] for x, y in origins]
    
    results = model.predict(
        crops,
        imgsz=imgsz,
        conf=conf,
        iou=iou,
        device=device,
        augment=tta,
        verbose=False,
    )

    detections = []
    for (x0, y0), result in zip(origins, results):
        for box in result.boxes:
            cls = int(box.cls[0])
            bconf = float(box.conf[0])
            x1, by1, x2, by2 = box.xyxy[0].tolist()
            gx1 = x1 + x0
            gy1 = by1 + y0
            gx2 = x2 + x0
            gy2 = by2 + y0
            cy = (gy1 + gy2) / 2
            if y1 <= cy <= y2:
                detections.append(
                    {
                        "frame": frame_idx,
                        "time_sec": frame_idx / fps,
                        "class_id": cls,
                        "class_name": CLASS_NAMES.get(cls, str(cls)),
                        "state": CLASS_SHORT.get(cls, str(cls)),
                        "conf": bconf,
                        "xyxy": (gx1, gy1, gx2, gy2),
                    }
                )
    detections = nms(detections)
    detections = [refine_detection_box(frame, det, args) for det in detections]
    detections = [det for det in detections if detection_quality_ok(frame, det, args)]
    detections.extend(infer_missing_off_from_rows(detections, frame_idx, fps, args))
    return detections, (y1, y2)
