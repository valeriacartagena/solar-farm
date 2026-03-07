"""
Demo runner for the hackathon presentation.

Processes demo images through the full pipeline and produces
annotated outputs with a summary table.

Usage:
    python -m ml.demo.run_demo --input ml/demo/demo_images
    python -m ml.demo.run_demo --input ml/demo/demo_images --no-gemini
    python -m ml.demo.run_demo --input path/to/single_image.jpg
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from ml.inference.pipeline import detect_faults
from ml.inference.visualize import draw_fault_overlay


def process_images(
    input_path: str,
    output_dir: str,
    model_path: str,
    use_gemini: bool,
    conf_threshold: float,
):
    """Process one or more images and save annotated results."""
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect image paths
    if input_path.is_file():
        image_files = [input_path]
    elif input_path.is_dir():
        image_files = sorted(
            p for p in input_path.iterdir()
            if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
        )
    else:
        print(f"Input path not found: {input_path}")
        sys.exit(1)

    if not image_files:
        print(f"No images found in {input_path}")
        sys.exit(1)

    print(f"Processing {len(image_files)} image(s)...")
    print(f"Gemini verification: {'ON' if use_gemini else 'OFF'}")
    print(f"Model: {model_path}")
    print()

    all_detections = {}
    fault_summary = defaultdict(lambda: defaultdict(int))

    for img_path in image_files:
        print(f"  {img_path.name}...", end=" ", flush=True)

        detections = detect_faults(
            str(img_path),
            model_path=model_path,
            use_gemini=use_gemini,
            conf_threshold=conf_threshold,
        )

        # Draw overlay
        out_path = str(output_dir / f"annotated_{img_path.name}")
        draw_fault_overlay(str(img_path), detections, out_path)

        # Count faults (exclude clean panels)
        faults = [d for d in detections if d["class"] != "panel"]
        print(f"{len(faults)} fault(s) detected")

        all_detections[img_path.name] = detections

        for d in faults:
            fault_summary[d["class"]][d.get("severity", "medium")] += 1

    # Save raw detections as JSON
    json_path = output_dir / "detections.json"
    with open(json_path, "w") as f:
        json.dump(all_detections, f, indent=2)

    # Print summary
    print("\n" + "=" * 50)
    print("FAULT DETECTION SUMMARY")
    print("=" * 50)

    if not fault_summary:
        print("  No faults detected.")
    else:
        print(f"  {'Fault Type':<15} {'Low':>6} {'Medium':>8} {'High':>6} {'Total':>7}")
        print(f"  {'-'*15} {'-'*6} {'-'*8} {'-'*6} {'-'*7}")
        grand_total = 0
        for fault_class in sorted(fault_summary.keys()):
            severities = fault_summary[fault_class]
            low = severities.get("low", 0)
            med = severities.get("medium", 0)
            high = severities.get("high", 0)
            total = low + med + high
            grand_total += total
            print(f"  {fault_class:<15} {low:>6} {med:>8} {high:>6} {total:>7}")
        print(f"  {'TOTAL':<15} {'':>6} {'':>8} {'':>6} {grand_total:>7}")

    print(f"\nAnnotated images: {output_dir}/")
    print(f"Raw detections:   {json_path}")


def main():
    parser = argparse.ArgumentParser(description="Run Radiant fault detection demo")
    parser.add_argument("--input", required=True, help="Path to image or directory of images")
    parser.add_argument("--output", default="ml/demo/output", help="Output directory (default: ml/demo/output)")
    parser.add_argument("--model", default="ml/weights/best.pt", help="Path to model weights")
    parser.add_argument("--no-gemini", action="store_true", help="Skip Gemini verification (offline mode)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (default: 0.25)")
    args = parser.parse_args()

    process_images(
        input_path=args.input,
        output_dir=args.output,
        model_path=args.model,
        use_gemini=not args.no_gemini,
        conf_threshold=args.conf,
    )


if __name__ == "__main__":
    main()
