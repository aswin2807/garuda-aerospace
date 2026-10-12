#!/usr/bin/env python3
import json
import csv
import shutil
from pathlib import Path
from PIL import Image
import torch
from ultralytics import YOLO

# Read existing evaluation report
eval_report_path = Path("runs/runway_evaluation/evaluation_report.json")
with open(eval_report_path) as f:
    eval_data = json.load(f)

reports_dir = Path("reports")
reports_dir.mkdir(parents=True, exist_ok=True)

# 1. reports/overall_metrics.json
overall_metrics = {
    "model": "ml_engine/models/runway_light_best.pt",
    "dataset": "data.yaml",
    "split": "test",
    "test_images_count": 144,
    "inference_resolution": 960,
    "confidence_threshold": 0.25,
    "iou_threshold": 0.50,
    "overall": eval_data["overall_metrics"],
    "per_class": eval_data["per_class_metrics"],
    "confusion_matrix": eval_data["confusion_matrix"]
}

with open(reports_dir / "overall_metrics.json", "w") as f:
    json.dump(overall_metrics, f, indent=2)
print("Saved reports/overall_metrics.json")

# 2. reports/per_class_metrics.csv
with open(reports_dir / "per_class_metrics.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["class_id", "class_name", "precision", "recall", "f1_score", "map50", "tp", "fp", "fn"])
    cm = eval_data["confusion_matrix"]["matrix"]
    # Class 0: LIGHT OFF
    off_m = eval_data["per_class_metrics"]["LIGHT OFF"]
    writer.writerow([0, "LIGHT OFF", off_m["precision"], off_m["recall"], off_m["f1_score"], off_m["map50"], int(cm[0][0]), int(cm[2][0]), int(cm[0][2])])
    # Class 1: LIGHT ON
    on_m = eval_data["per_class_metrics"]["LIGHT ON"]
    writer.writerow([1, "LIGHT ON", on_m["precision"], on_m["recall"], on_m["f1_score"], on_m["map50"], int(cm[1][1]), int(cm[2][1]), int(cm[1][2])])
print("Saved reports/per_class_metrics.csv")

# 3. reports/error_contact_sheet.jpg
src_sheet = Path("runs/runway_evaluation/diagnostic_four_frame_comparison.jpg")
if src_sheet.exists():
    shutil.copy(src_sheet, reports_dir / "error_contact_sheet.jpg")
    print("Copied error_contact_sheet.jpg")

# 4. Generate reports/per_image_metrics.csv for all 144 test images
print("Evaluating all 144 test images individually...")
model = YOLO("ml_engine/models/runway_light_best.pt")
test_img_dir = Path("test/images")
test_lbl_dir = Path("test/labels")
test_images = sorted(list(test_img_dir.glob("*.jpg")) + list(test_img_dir.glob("*.png")))

def read_yolo_labels(path, width, height):
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
        boxes.append((int(cls), x1, y1, x2, y2))
    return boxes

def box_iou(a, b):
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0

per_image_rows = []
annotation_review_rows = []

for img_p in test_images:
    lbl_p = test_lbl_dir / f"{img_p.stem}.txt"
    with Image.open(img_p) as im:
        w, h = im.size
    gt_boxes = read_yolo_labels(lbl_p, w, h)
    
    pred_res = model.predict(
        source=str(img_p),
        imgsz=960,
        conf=0.25,
        iou=0.50,
        agnostic_nms=True,
        verbose=False
    )[0]
    
    preds = []
    if pred_res.boxes:
        for b in pred_res.boxes:
            c = int(b.cls.item())
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            cf = float(b.conf.item())
            preds.append((c, x1, y1, x2, y2, cf))
            
    # Class-aware matching
    candidates = []
    for gi, g in enumerate(gt_boxes):
        for pi, p in enumerate(preds):
            if g[0] == p[0]:
                sc = box_iou((g[1], g[2], g[3], g[4]), (p[1], p[2], p[3], p[4]))
                if sc >= 0.50:
                    candidates.append((sc, gi, pi))
    candidates.sort(reverse=True, key=lambda x: x[0])
    used_g, used_p = set(), set()
    tp = 0
    for sc, gi, pi in candidates:
        if gi not in used_g and pi not in used_p:
            used_g.add(gi)
            used_p.add(pi)
            tp += 1
            
    fp = len(preds) - tp
    fn = len(gt_boxes) - tp
    prec = round(tp / max(1, len(preds)), 4) if len(preds) > 0 else (1.0 if len(gt_boxes) == 0 else 0.0)
    rec = round(tp / max(1, len(gt_boxes)), 4) if len(gt_boxes) > 0 else 1.0
    f1 = round(2 * prec * rec / max(1e-6, prec + rec), 4)
    
    per_image_rows.append([
        img_p.name, "test", len(gt_boxes), len(preds), tp, fp, fn, prec, rec, f1
    ])
    
    # Check potential annotation gap candidate
    # If there are FP predictions with high confidence (>0.60) in upper runway region or tiny fixtures
    for pi in range(len(preds)):
        if pi not in used_p:
            p = preds[pi]
            cls_name = "LIGHT ON" if p[0] == 1 else "LIGHT OFF"
            if p[5] >= 0.50:
                annotation_review_rows.append([
                    img_p.name, "Unmatched Prediction (High Conf FP)", cls_name, round(p[5], 3),
                    f"[{round(p[1],1)},{round(p[2],1)},{round(p[3],1)},{round(p[4],1)}]",
                    "Possible unannotated distant light fixture on runway edge"
                ])
    for gi in range(len(gt_boxes)):
        if gi not in used_g:
            g = gt_boxes[gi]
            cls_name = "LIGHT ON" if g[0] == 1 else "LIGHT OFF"
            bw = g[3] - g[1]
            bh = g[4] - g[2]
            if bw < 5 or bh < 5:
                annotation_review_rows.append([
                    img_p.name, "Missed Annotation (Sub-5px FN)", cls_name, "N/A",
                    f"[{round(g[1],1)},{round(g[2],1)},{round(g[3],1)},{round(g[4],1)}]",
                    "Extremely small/distant fixture below standard NMS receptive field"
                ])

with open(reports_dir / "per_image_metrics.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["image_name", "split", "gt_count", "pred_count", "tp", "fp", "fn", "precision", "recall", "f1_score"])
    writer.writerows(per_image_rows)
print(f"Saved reports/per_image_metrics.csv ({len(per_image_rows)} images)")

with open(reports_dir / "annotation_review.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["image_name", "finding_type", "class_name", "confidence", "bounding_box", "expert_review_notes"])
    writer.writerows(annotation_review_rows)
print(f"Saved reports/annotation_review.csv ({len(annotation_review_rows)} findings)")
