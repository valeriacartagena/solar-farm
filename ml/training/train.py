"""
YOLOv8-s training script for solar panel fault detection.
Designed to run on Kaggle (P100 GPU, free tier).

Usage:
    python train.py --data /kaggle/input/solar-fault-merged/data.yaml
    python train.py --data /kaggle/input/solar-fault-merged/data.yaml --epochs 50 --batch 8
"""

import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8-s on solar fault dataset")
    parser.add_argument("--data", required=True, help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs (default: 30)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size (default: 640)")
    parser.add_argument("--device", default="0", help="Device: 0 for GPU, cpu for CPU (default: 0)")
    parser.add_argument("--weights", default="yolov8s.pt", help="Pretrained weights (default: yolov8s.pt)")
    parser.add_argument("--project", default="solar_fault", help="Project save directory")
    parser.add_argument("--name", default="yolov8s_run1", help="Run name")
    args = parser.parse_args()

    print(f"Loading model: {args.weights}")
    model = YOLO(args.weights)

    print(f"Starting training: {args.epochs} epochs, batch={args.batch}, imgsz={args.imgsz}")
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=10,
        save_period=10,
        device=args.device,
        workers=2,
        project=args.project,
        name=args.name,
    )

    # Print final metrics
    print("\n=== Training Complete ===")
    metrics = model.val()
    print(f"mAP@50:    {metrics.box.map50:.4f}")
    print(f"mAP@50-95: {metrics.box.map:.4f}")

    if hasattr(metrics.box, "ap_class_index") and metrics.box.ap_class_index is not None:
        print("\nPer-class AP@50:")
        for i, cls_idx in enumerate(metrics.box.ap_class_index):
            cls_name = model.names[int(cls_idx)]
            ap50 = metrics.box.ap50[i]
            print(f"  {cls_name}: {ap50:.4f}")

    # Copy best.pt to a known location
    best_pt = Path(args.project) / args.name / "weights" / "best.pt"
    if best_pt.exists():
        output_dir = Path("weights")
        output_dir.mkdir(exist_ok=True)
        dst = output_dir / "best.pt"
        shutil.copy2(best_pt, dst)
        print(f"\nBest weights copied to: {dst}")
    else:
        print(f"\nWARNING: best.pt not found at {best_pt}")


if __name__ == "__main__":
    main()
