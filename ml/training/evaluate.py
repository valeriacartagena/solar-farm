"""
Evaluate a trained YOLOv8 model on the test set and optionally run
inference on sample images.

Usage:
    python evaluate.py --weights weights/best.pt --data data/data.yaml
    python evaluate.py --weights weights/best.pt --data data/data.yaml --sample-dir demo/demo_images --output demo/output
"""

import argparse
from pathlib import Path

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained YOLOv8 model")
    parser.add_argument("--weights", required=True, help="Path to trained weights (best.pt)")
    parser.add_argument("--data", required=True, help="Path to data.yaml")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size (default: 640)")
    parser.add_argument("--device", default="0", help="Device (default: 0)")
    parser.add_argument("--sample-dir", help="Directory of sample images to run inference on")
    parser.add_argument("--output", default="eval_output", help="Output directory for sample predictions")
    args = parser.parse_args()

    print(f"Loading model: {args.weights}")
    model = YOLO(args.weights)

    # Run validation on test set
    print("\n=== Validation Metrics ===")
    metrics = model.val(data=args.data, imgsz=args.imgsz, device=args.device, split="test")

    print(f"mAP@50:    {metrics.box.map50:.4f}")
    print(f"mAP@50-95: {metrics.box.map:.4f}")

    if hasattr(metrics.box, "ap_class_index") and metrics.box.ap_class_index is not None:
        print("\nPer-class metrics:")
        print(f"  {'Class':<12} {'P':>8} {'R':>8} {'AP@50':>8}")
        print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*8}")
        for i, cls_idx in enumerate(metrics.box.ap_class_index):
            cls_name = model.names[int(cls_idx)]
            p = metrics.box.p[i]
            r = metrics.box.r[i]
            ap50 = metrics.box.ap50[i]
            print(f"  {cls_name:<12} {p:>8.4f} {r:>8.4f} {ap50:>8.4f}")

    # Optionally run inference on sample images
    if args.sample_dir:
        sample_dir = Path(args.sample_dir)
        if not sample_dir.exists():
            print(f"\nSample directory not found: {sample_dir}")
            return

        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        image_files = sorted(
            p for p in sample_dir.iterdir()
            if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
        )

        if not image_files:
            print(f"\nNo images found in {sample_dir}")
            return

        print(f"\n=== Sample Inference ({len(image_files)} images) ===")
        for img_path in image_files:
            results = model(str(img_path), imgsz=args.imgsz, device=args.device)
            for r in results:
                annotated = r.plot()
                import cv2
                out_path = output_dir / f"pred_{img_path.name}"
                cv2.imwrite(str(out_path), annotated)
                n_boxes = len(r.boxes) if r.boxes is not None else 0
                print(f"  {img_path.name}: {n_boxes} detections -> {out_path}")

        print(f"\nAnnotated images saved to: {output_dir}")


if __name__ == "__main__":
    main()
