#!/usr/bin/env python3
"""
GARUDA AEROSPACE — Runway Light Detection & Classification Evaluation System (PRD v1.0)
Full Dataset Evaluation, Confusion Matrix Analysis, Diagnostic Frame Audit, and Uncertainty Reporting.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
from PIL import Image, ImageDraw
import torch
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate Runway Light YOLO11 Detection & Classification Model")
    parser.add_argument("--model", type=str, default="ml_engine/models/runway_light_best.pt", help="Path to model weights (.pt)")
    parser.add_argument("--data", type=str, default="data.yaml", help="Path to data.yaml")
    parser.add_argument("--split", type=str, default="test", choices=["val", "test", "train"], help="Dataset split to evaluate")
    parser.add_argument("--imgsz", type=int, default=960, help="Inference image resolution (640, 960, 1280)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.50, help="IoU threshold for NMS and matching")
    parser.add_argument("--out-dir", type=str, default="runs/runway_evaluation", help="Output directory for reports and artifacts")
    parser.add_argument("--audit-diagnostic-frames", action="store_true", default=True, help="Run deep audit on frames 0079, 0058, 0164, 0196")
    return parser.parse_args()


def read_yolo_labels(path: Path, width: int, height: int) -> List[Tuple[int, float, float, float, float, float, float]]:
    boxes = []
    if not path.exists():
        return boxes
    for line in path.read_text().splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        cls, xc, yc, bw, bh = map(float, parts[:5])
        x1 = (xc - bw / 2.0) * width
        y1 = (yc - bh / 2.0) * height
        x2 = (xc + bw / 2.0) * width
        y2 = (yc + bh / 2.0) * height
        boxes.append((int(cls), x1, y1, x2, y2, bw * width, bh * height))
    return boxes


def box_iou(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def match_gt_predictions(gt: List[Tuple], preds: List[Tuple], iou_thresh: float = 0.50):
    candidates = []
    for gi, g in enumerate(gt):
        for pi, p in enumerate(preds):
            if g[0] == p[0]:  # class-aware match
                score = box_iou((g[1], g[2], g[3], g[4]), (p[1], p[2], p[3], p[4]))
                if score >= iou_thresh:
                    candidates.append((score, gi, pi))
    candidates.sort(reverse=True, key=lambda x: x[0])
    used_g, used_p = set(), set()
    matched = []
    for score, gi, pi in candidates:
        if gi not in used_g and pi not in used_p:
            used_g.add(gi)
            used_p.add(pi)
            matched.append((gi, pi, score))

    unmatched_preds = [pi for pi in range(len(preds)) if pi not in used_p]
    missed_gt = [gi for gi in range(len(gt)) if gi not in used_g]
    return matched, unmatched_preds, missed_gt


def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(" GARUDA AEROSPACE — RUNWAY LIGHT DETECTION & CLASSIFICATION EVALUATION")
    print("=" * 80)
    print(f"Model       : {args.model}")
    print(f"Data config : {args.data}")
    print(f"Split       : {args.split}")
    print(f"Resolution  : {args.imgsz}x{args.imgsz}")
    print(f"Confidence  : {args.conf}")
    print(f"IoU thresh  : {args.iou}")
    print(f"Output dir  : {out_dir.resolve()}")
    print("-" * 80)

    model = YOLO(args.model)

    # 1. Run Ultralytics benchmark validation
    print("\n[STEP 1/3] Running Ultralytics benchmark validation...")
    val_res = model.val(
        data=args.data,
        split=args.split,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        verbose=False,
    )

    p_overall = float(val_res.box.mp)
    r_overall = float(val_res.box.mr)
    map50_overall = float(val_res.box.map50)
    map_overall = float(val_res.box.map)
    f1_overall = 2 * (p_overall * r_overall) / (p_overall + r_overall + 1e-6)

    class_names = [model.names[i] for i in sorted(model.names.keys())]
    per_class_metrics = {}
    for i, name in enumerate(class_names):
        p_c = float(val_res.box.p[i])
        r_c = float(val_res.box.r[i])
        f1_c = 2 * (p_c * r_c) / (p_c + r_c + 1e-6)
        map50_c = float(val_res.box.maps[i])
        per_class_metrics[name] = {
            "precision": round(p_c, 4),
            "recall": round(r_c, 4),
            "f1_score": round(f1_c, 4),
            "map50": round(map50_c, 4),
        }

    # Confusion matrix extraction
    cm_matrix = val_res.confusion_matrix.matrix.tolist()

    # 2. Audit Diagnostic Frames (0079, 0058, 0164, 0196)
    print("\n[STEP 2/3] Performing deep audit on diagnostic frames...")
    diag_frames = ["0079", "0058", "0164", "0196"]
    diag_audit_results = {}

    split_img_dir = Path(f"{args.split}/images")
    split_lbl_dir = Path(f"{args.split}/labels")

    for frame_id in diag_frames:
        matches = list(split_img_dir.glob(f"*-{frame_id}_jpg*"))
        if not matches:
            # Check test split if evaluating another split
            matches = list(Path("test/images").glob(f"*-{frame_id}_jpg*"))
        if not matches:
            print(f"Warning: Frame {frame_id} not found.")
            continue

        img_path = matches[0]
        lbl_path = split_lbl_dir / f"{img_path.stem}.txt"
        if not lbl_path.exists():
            lbl_path = Path("test/labels") / f"{img_path.stem}.txt"

        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        gt_boxes = read_yolo_labels(lbl_path, w, h)

        pred_res = model.predict(
            source=str(img_path),
            imgsz=args.imgsz,
            conf=args.conf,
            iou=args.iou,
            agnostic_nms=True,
            verbose=False,
        )[0]

        preds = []
        if pred_res.boxes:
            for b in pred_res.boxes:
                c = int(b.cls.item())
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                cf = float(b.conf.item())
                preds.append((c, x1, y1, x2, y2, cf))

        matched, unmatched_p_indices, missed_gt_indices = match_gt_predictions(gt_boxes, preds, args.iou)

        # Categorize root causes
        missed_details = []
        for gi in missed_gt_indices:
            g = gt_boxes[gi]
            # Check if predicted at low confidence (< args.conf)
            low_conf_pred = model.predict(source=str(img_path), imgsz=args.imgsz, conf=0.10, iou=args.iou, verbose=False)[0]
            detected_at_low_conf = False
            low_conf_val = 0.0
            if low_conf_pred.boxes:
                for b in low_conf_pred.boxes:
                    iou_sc = box_iou((g[1], g[2], g[3], g[4]), b.xyxy[0].tolist())
                    if iou_sc >= 0.40:
                        detected_at_low_conf = True
                        low_conf_val = float(b.conf.item())
                        break

            cause = (
                f"Confidence below threshold ({low_conf_val:.2f} < {args.conf})"
                if detected_at_low_conf
                else ("Extreme image boundary clipping" if (g[1] < 10 or g[3] > w - 10) else "Tiny/distant fixture")
            )
            missed_details.append({
                "gt_index": gi,
                "class": model.names[g[0]],
                "bbox": [round(x, 1) for x in g[1:5]],
                "size_px": [round(g[5], 1), round(g[6], 1)],
                "diagnosed_cause": cause,
            })

        unmatched_details = []
        for pi in unmatched_p_indices:
            p = preds[pi]
            # Check if borderline IoU with any GT
            best_sc, best_gi = 0.0, -1
            for gi, g in enumerate(gt_boxes):
                sc = box_iou((g[1], g[2], g[3], g[4]), (p[1], p[2], p[3], p[4]))
                if sc > best_sc:
                    best_sc = sc
                    best_gi = gi

            cause = (
                f"Borderline localization (IoU {best_sc:.2f} < {args.iou})"
                if 0.40 <= best_sc < args.iou
                else ("Omitted distant light in GT" if p[4] < 0.35 * h else "Pavement/background artifact")
            )
            unmatched_details.append({
                "pred_index": pi,
                "class": model.names[p[0]],
                "confidence": round(p[5], 3),
                "bbox": [round(x, 1) for x in p[1:5]],
                "diagnosed_cause": cause,
            })

        diag_audit_results[frame_id] = {
            "image_filename": img_path.name,
            "dimensions": [w, h],
            "total_gt": len(gt_boxes),
            "total_predictions": len(preds),
            "matched_tp": len(matched),
            "unmatched_fp": len(unmatched_p_indices),
            "missed_fn": len(missed_gt_indices),
            "precision": round(len(matched) / max(1, len(preds)), 4),
            "recall": round(len(matched) / max(1, len(gt_boxes)), 4) if gt_boxes else (1.0 if not preds else 0.0),
            "missed_details": missed_details,
            "unmatched_details": unmatched_details,
        }

    # 3. Save Summary Artifacts & Print Report
    print("\n[STEP 3/3] Generating audit reports...")
    report_data = {
        "evaluation_config": {
            "model_path": args.model,
            "data_yaml": args.data,
            "split": args.split,
            "imgsz": args.imgsz,
            "confidence_threshold": args.conf,
            "iou_threshold": args.iou,
        },
        "overall_metrics": {
            "precision": round(p_overall, 4),
            "recall": round(r_overall, 4),
            "f1_score": round(f1_overall, 4),
            "map50": round(map50_overall, 4),
            "map50_95": round(map_overall, 4),
        },
        "per_class_metrics": per_class_metrics,
        "confusion_matrix": {
            "classes": class_names + ["background"],
            "matrix": cm_matrix,
        },
        "diagnostic_frame_audit": diag_audit_results,
    }

    json_path = out_dir / "evaluation_report.json"
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2)

    # Markdown Summary
    md_path = out_dir / "EVALUATION_REPORT.md"
    with open(md_path, "w") as f:
        f.write("# Runway Light Detection & Classification Evaluation Report\n\n")
        f.write(f"**Split:** `{args.split}` | **Resolution:** `{args.imgsz}x{args.imgsz}` | **Confidence Threshold:** `{args.conf}` | **IoU:** `{args.iou}`\n\n")
        f.write("## 1. Overall Benchmark Metrics\n\n")
        f.write("| Metric | Value |\n| :--- | :--- |\n")
        f.write(f"| **Overall Precision** | **{p_overall * 100:.2f}%** |\n")
        f.write(f"| **Overall Recall** | **{r_overall * 100:.2f}%** |\n")
        f.write(f"| **Overall F1-Score** | **{f1_overall * 100:.2f}%** |\n")
        f.write(f"| **mAP@0.50** | **{map50_overall * 100:.2f}%** |\n")
        f.write(f"| **mAP@0.50:0.95** | **{map_overall * 100:.2f}%** |\n\n")

        f.write("## 2. Per-Class Performance\n\n")
        f.write("| Class | Precision | Recall | F1-Score | mAP@0.50 |\n| :--- | :--- | :--- | :--- | :--- |\n")
        for name, m in per_class_metrics.items():
            f.write(f"| **{name}** | {m['precision'] * 100:.1f}% | {m['recall'] * 100:.1f}% | {m['f1_score'] * 100:.1f}% | {m['map50'] * 100:.1f}% |\n")

        f.write("\n## 3. Confusion Matrix\n\n")
        f.write("Rows: Ground Truth, Columns: Prediction\n\n")
        f.write(f"| True \\ Pred | {class_names[0]} | {class_names[1]} | Background |\n| :--- | :--- | :--- | :--- |\n")
        if len(cm_matrix) >= 3:
            f.write(f"| **{class_names[0]}** | {cm_matrix[0][0]:.0f} | {cm_matrix[0][1]:.0f} | {cm_matrix[0][2]:.0f} |\n")
            f.write(f"| **{class_names[1]}** | {cm_matrix[1][0]:.0f} | {cm_matrix[1][1]:.0f} | {cm_matrix[1][2]:.0f} |\n")
            f.write(f"| **Background** | {cm_matrix[2][0]:.0f} | {cm_matrix[2][1]:.0f} | - |\n")

        f.write("\n## 4. Diagnostic Four-Frame Audit (Section 2 & 6)\n\n")
        f.write("| Frame | GT | Preds | Matched (TP) | Unmatched (FP) | Missed (FN) | Precision | Recall |\n| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for fid, res in diag_audit_results.items():
            f.write(f"| **{fid}** | {res['total_gt']} | {res['total_predictions']} | {res['matched_tp']} | {res['unmatched_fp']} | {res['missed_fn']} | {res['precision'] * 100:.1f}% | {res['recall'] * 100:.1f}% |\n")

        f.write("\n### Root Cause Breakdown:\n")
        for fid, res in diag_audit_results.items():
            f.write(f"\n#### Frame {fid}:\n")
            if res["missed_details"]:
                f.write("**Missed Labels (FN):**\n")
                for md in res["missed_details"]:
                    f.write(f"- GT #{md['gt_index']} ({md['class']}, size {md['size_px'][0]}x{md['size_px'][1]}px): {md['diagnosed_cause']}\n")
            if res["unmatched_details"]:
                f.write("**Unmatched Predictions (FP):**\n")
                for ud in res["unmatched_details"]:
                    f.write(f"- Pred #{ud['pred_index']} ({ud['class']}, conf {ud['confidence']:.2f}): {ud['diagnosed_cause']}\n")
            if not res["missed_details"] and not res["unmatched_details"]:
                f.write("- Perfect alignment or true negative background frame.\n")

    print("\n" + "=" * 80)
    print(" EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Overall Precision : {p_overall * 100:.2f}%")
    print(f"Overall Recall    : {r_overall * 100:.2f}%")
    print(f"Overall F1-Score  : {f1_overall * 100:.2f}%")
    print(f"mAP@0.50          : {map50_overall * 100:.2f}%")
    print(f"mAP@0.50:0.95     : {map_overall * 100:.2f}%")
    print("-" * 80)
    for name, m in per_class_metrics.items():
        print(f"[{name:<10}] P: {m['precision']*100:.1f}% | R: {m['recall']*100:.1f}% | F1: {m['f1_score']*100:.1f}% | mAP50: {m['map50']*100:.1f}%")
    print("-" * 80)
    print(f"JSON Report saved to : {json_path.resolve()}")
    print(f"Markdown Report saved: {md_path.resolve()}")
    print("=" * 80)


if __name__ == "__main__":
    main()
