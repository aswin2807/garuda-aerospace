# ML Engine — Drone Navigation AI (YOLOv11)

This module manages dataset preparation, training, validation, inference, and model deployment for the **Drone Navigation AI** system.

## Dataset Structure
* `datasets/data.yaml` — Dataset metadata and classes (`0: off`, `1: on`).
* `datasets/images/` — Train (3,033), Val (285), and Test (144) image splits.
* `datasets/labels/` — YOLO-format bounding box annotations (`class_id cx cy w h`).

## Commands

### 1. Training
```bash
python scripts/train.py --config configs/training.yaml
```
or with custom parameters:
```bash
python scripts/train.py --model yolo11n.pt --epochs 100 --imgsz 512 --batch 16
```
Trained checkpoints are automatically saved to `models/trained/best.pt`.

### 2. Validation
```bash
python scripts/validate.py --model models/trained/best.pt --split val
```
Reports Precision, Recall, mAP@50, mAP@50-95, F1 Score, and inference FPS.

### 3. Inference
```bash
python scripts/predict.py --model models/trained/best.pt --source sample.jpg --conf 0.50
```

### 4. Export
```bash
python scripts/export.py --model models/trained/best.pt --format onnx
```
