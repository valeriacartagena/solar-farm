"""
Download the two Roboflow datasets for solar panel fault detection.

Usage:
    export ROBOFLOW_API_KEY=your_key_here
    python data/download_datasets.py
"""

import os
import sys

from roboflow import Roboflow


def main():
    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        print("ERROR: Set ROBOFLOW_API_KEY environment variable first.")
        print("  export ROBOFLOW_API_KEY=your_key_here")
        sys.exit(1)

    rf = Roboflow(api_key=api_key)
    output_base = os.path.join(os.path.dirname(__file__), "raw")

    # Dataset 1: panel-solar (bird_drop, cracked, dusty, panel)
    print("Downloading Dataset 1: panel-solar (6,493 images)...")
    project1 = rf.workspace("susan-ifblr").project("panel-solar-bw945")
    dataset1 = project1.version(1).download("yolov8", location=os.path.join(output_base, "panel-solar"))
    print(f"  Saved to: {dataset1.location}")

    # Dataset 2: hotspot detection (hotspot)
    print("\nDownloading Dataset 2: hotspot detection (1,000 images)...")
    project2 = rf.workspace("american-university-of-sharjah").project("hotspot-detection-in-solar-panel")
    dataset2 = project2.version(1).download("yolov8", location=os.path.join(output_base, "hotspot-detection"))
    print(f"  Saved to: {dataset2.location}")

    print("\n=== Downloads Complete ===")
    print(f"Panel-solar:      {dataset1.location}")
    print(f"Hotspot detection: {dataset2.location}")
    print("\nNext step: merge the datasets:")
    print(f"  python data/merge_datasets.py --ds1 {dataset1.location} --ds2 {dataset2.location} --output data/merged")


if __name__ == "__main__":
    main()
