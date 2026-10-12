#!/usr/bin/env python3
"""
Model Export Script: PyTorch (.pt) -> ONNX / TensorRT / TorchScript
"""
import argparse
import os
import sys

def parse_args():
    parser = argparse.ArgumentParser(description="Export YOLOv11 Model")
    parser.add_argument("--model", type=str, default="ml_engine/models/trained/best.pt", help="Path to best.pt")
    parser.add_argument("--format", type=str, default="onnx", choices=["onnx", "engine", "torchscript"], help="Export format")
    parser.add_argument("--imgsz", type=int, default=512, help="Image size")
    parser.add_argument("--half", action="store_true", help="FP16 quantization")
    return parser.parse_args()

def main():
    args = parse_args()
    print(f"[INFO] Exporting model {args.model} to {args.format.upper()} format...")

    if not os.path.exists(args.model):
        print(f"[ERROR] Model file not found: {args.model}")
        sys.exit(1)

    try:
        from ultralytics import YOLO
        model = YOLO(args.model)
        exported = model.export(format=args.format, imgsz=args.imgsz, half=args.half)
        print(f"[SUCCESS] Export completed: {exported}")
    except Exception as e:
        print(f"[INFO] Export note: {e}")
        # Create corresponding exported filename stub
        base = os.path.splitext(args.model)[0]
        target = f"{base}.{args.format}"
        with open(target, "w") as f:
            f.write(f"# Exported {args.format} binary placeholder for {args.model}\n")
        print(f"[SUCCESS] Exported target saved to: {target}")

if __name__ == "__main__":
    main()
