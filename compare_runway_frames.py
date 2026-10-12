from pathlib import Path
from PIL import Image, ImageDraw
from ultralytics import YOLO
import math

ROOT = Path(".")
MODEL = ROOT / "ml_engine/models/runway_light_best.pt"
IMAGE_DIR = ROOT / "test/images"
LABEL_DIR = ROOT / "test/labels"
OUT_DIR = ROOT / "runs/runway_validation/frame_comparison"
FRAMES = ["0079", "0058", "0164", "0196"]
CONF = 0.45
IMGSZ = 960
MATCH_IOU = 0.50

OUT_DIR.mkdir(parents=True, exist_ok=True)
model = YOLO(str(MODEL))

def read_labels(path, width, height):
    boxes = []
    if not path.exists():
        return boxes, False
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cls, xc, yc, bw, bh = map(float, parts[:5])
        x1 = (xc - bw / 2) * width
        y1 = (yc - bh / 2) * height
        x2 = (xc + bw / 2) * width
        y2 = (yc + bh / 2) * height
        boxes.append((int(cls), x1, y1, x2, y2))
    return boxes, True

def iou(a, b):
    x1, y1 = max(a[1], b[1]), max(a[2], b[2])
    x2, y2 = min(a[3], b[3]), min(a[4], b[4])
    inter = max(0, x2-x1) * max(0, y2-y1)
    area_a = max(0, a[3]-a[1]) * max(0, a[4]-a[2])
    area_b = max(0, b[3]-b[1]) * max(0, b[4]-b[2])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0

def match_boxes(gt, pred):
    candidates = []
    for gi, g in enumerate(gt):
        for pi, p in enumerate(pred):
            if g[0] == p[0]:
                score = iou(g, p)
                if score >= MATCH_IOU:
                    candidates.append((score, gi, pi))
    candidates.sort(reverse=True)
    used_g, used_p = set(), set()
    for score, gi, pi in candidates:
        if gi not in used_g and pi not in used_p:
            used_g.add(gi)
            used_p.add(pi)
    return len(used_g), len(pred)-len(used_p), len(gt)-len(used_g)

tiles = []
summary = []

for frame in FRAMES:
    matches = list(IMAGE_DIR.glob(f"*-{frame}_jpg*"))
    if not matches:
        print(f"Frame {frame}: source image not found")
        continue

    image_path = matches[0]
    label_path = LABEL_DIR / f"{image_path.stem}.txt"
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    gt, label_exists = read_labels(label_path, width, height)

    result = model.predict(
        source=str(image_path), imgsz=IMGSZ, conf=CONF,
        iou=0.50, agnostic_nms=True, verbose=False
    )[0]

    pred = []
    if result.boxes is not None:
        for box in result.boxes:
            cls = int(box.cls.item())
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            pred.append((cls, x1, y1, x2, y2, float(box.conf.item())))

    tp, fp, fn = match_boxes(gt, pred)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0

    summary.append(
        (frame, len(gt), len(pred), tp, fp, fn, precision, recall, label_exists)
    )

    draw = ImageDraw.Draw(image)
    # Ground truth: green
    for cls, x1, y1, x2, y2 in gt:
        draw.rectangle((x1, y1, x2, y2), outline="#00FF00", width=3)
        draw.text((x1, max(0, y1-14)), f"GT {model.names.get(cls, cls)}",
                  fill="#00FF00", stroke_width=1, stroke_fill="black")

    # Predictions: red
    for cls, x1, y1, x2, y2, conf in pred:
        draw.rectangle((x1, y1, x2, y2), outline="#FF3030", width=3)
        draw.text((x1, min(height-15, y2+2)),
                  f"P {model.names.get(cls, cls)} {conf:.2f}",
                  fill="#FF3030", stroke_width=1, stroke_fill="black")

    image.thumbnail((640, 400))
    tile = Image.new("RGB", (660, 440), "white")
    tile.paste(image, ((660-image.width)//2, 30))
    d = ImageDraw.Draw(tile)
    d.text((8, 5), f"Frame {frame} | GT green | prediction red", fill="black")
    tiles.append(tile)

if tiles:
    sheet = Image.new("RGB", (1320, math.ceil(len(tiles)/2)*440), "#dddddd")
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % 2)*660, (i // 2)*440))
    sheet.save(OUT_DIR / "ground_truth_vs_predictions.jpg")

print("\nFrame comparison (class-aware matching, IoU >= 0.50)")
print("Frame | GT | Pred | TP | FP | FN | Precision | Recall | Label exists")
for row in summary:
    frame, ngt, npred, tp, fp, fn, precision, recall, exists = row
    print(f"{frame:>5} | {ngt:>2} | {npred:>4} | {tp:>2} | {fp:>2} | {fn:>2} | "
          f"{precision:.3f} | {recall:.3f} | {exists}")

print(f"\nImage saved to: {(OUT_DIR / 'ground_truth_vs_predictions.jpg').resolve()}")
print("Note: results apply only to these selected frames and the chosen thresholds.")
