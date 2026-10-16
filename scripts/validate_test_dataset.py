"""
Validation of runway_light_best.pt on the authentic labelled test dataset.
"""

from pathlib import Path
import json
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
data_yaml = ROOT / "data_test_eval.yaml"

with open(data_yaml, "w") as f:
    f.write(f"""
path: '{str(ROOT)}'
train: test/images
val: test/images
test: test/images
nc: 2
names: ['LIGHT OFF', 'LIGHT ON']
""")

model_path = ROOT / "ml_engine" / "models" / "runway_light_best.pt"
print(f"Loading {model_path}...")
model = YOLO(str(model_path))

print("Running validation on authentic test split...")
metrics = model.val(data=str(data_yaml), split="test", device="mps", verbose=True)

results = {
    "precision": float(metrics.box.mp),
    "recall": float(metrics.box.mr),
    "map50": float(metrics.box.map50),
    "map50_95": float(metrics.box.map),
    "speed": metrics.speed,
}

print("\n" + "=" * 50)
print("TEST SPLIT BENCHMARK RESULTS")
print("=" * 50)
print(f"Precision: {results['precision']:.4f}")
print(f"Recall:    {results['recall']:.4f}")
print(f"mAP@50:    {results['map50']:.4f}")
print(f"mAP@50-95: {results['map50_95']:.4f}")
print(f"Inference Speed: {results['speed']}")
print("=" * 50)

out_file = ROOT / "data" / "results" / "runway_test_split_metrics.json"
out_file.parent.mkdir(parents=True, exist_ok=True)
with open(out_file, "w") as f:
    json.dump(results, f, indent=2)

if data_yaml.exists():
    data_yaml.unlink()
