"""
Kaggle Notebook Training Script
================================
Copy-paste this into a Kaggle notebook cell to train YOLOv8-s.

Prerequisites:
  - Dataset: chanpark5537/solar-fault-merged (attached to notebook)
  - GPU: Enable P100 under Settings > Accelerator
  - Internet: Enable under Settings (needed for ultralytics download)
"""

# Cell 1: Install & imports
# !pip install ultralytics -q

from ultralytics import YOLO
from pathlib import Path
import shutil

# Cell 2: Verify dataset
DATASET_PATH = "/kaggle/input/solar-fault-merged"
print("Dataset contents:")
for p in sorted(Path(DATASET_PATH).rglob("*"))[:20]:
    print(f"  {p}")

# Check if data.yaml exists at top level or nested
data_yaml = None
for candidate in [
    Path(DATASET_PATH) / "data.yaml",
    *Path(DATASET_PATH).rglob("data.yaml"),
]:
    if candidate.exists():
        data_yaml = str(candidate)
        break

if data_yaml:
    print(f"\nFound data.yaml: {data_yaml}")
    with open(data_yaml) as f:
        print(f.read())
else:
    print("\nWARNING: data.yaml not found! Check dataset structure.")

# Cell 3: Fix data.yaml paths for Kaggle environment
# Kaggle datasets are read-only, so copy data.yaml to /kaggle/working
import yaml

with open(data_yaml) as f:
    config = yaml.safe_load(f)

# Update path to point to Kaggle input
config["path"] = DATASET_PATH
working_yaml = "/kaggle/working/data.yaml"
with open(working_yaml, "w") as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print(f"Updated data.yaml saved to: {working_yaml}")
print(f"  path: {config['path']}")

# Cell 4: Train
model = YOLO("yolov8s.pt")

results = model.train(
    data=working_yaml,
    epochs=30,          # Change to 2-3 for testing
    imgsz=640,
    batch=16,
    patience=10,
    save_period=10,
    device=0,
    workers=2,
    project="solar_fault",
    name="yolov8s_run1",
)

# Cell 5: Evaluate
metrics = model.val()
print(f"\nmAP@50:    {metrics.box.map50:.4f}")
print(f"mAP@50-95: {metrics.box.map:.4f}")

if hasattr(metrics.box, "ap_class_index") and metrics.box.ap_class_index is not None:
    print("\nPer-class AP@50:")
    for i, cls_idx in enumerate(metrics.box.ap_class_index):
        cls_name = model.names[int(cls_idx)]
        ap50 = metrics.box.ap50[i]
        print(f"  {cls_name}: {ap50:.4f}")

# Cell 6: Save best.pt for download
best_pt = Path("solar_fault/yolov8s_run1/weights/best.pt")
if best_pt.exists():
    shutil.copy2(best_pt, "/kaggle/working/best.pt")
    print(f"\nbest.pt copied to /kaggle/working/best.pt")
    print("Download it from the Output tab after the run completes.")
else:
    print(f"\nWARNING: best.pt not found at {best_pt}")
    # Try last.pt as fallback
    last_pt = Path("solar_fault/yolov8s_run1/weights/last.pt")
    if last_pt.exists():
        shutil.copy2(last_pt, "/kaggle/working/best.pt")
        print(f"Used last.pt instead: /kaggle/working/best.pt")

# Cell 7: Quick inference test on a few images
import glob
test_images = glob.glob(f"{DATASET_PATH}/test/images/*")[:5]
if test_images:
    print(f"\nRunning inference on {len(test_images)} test images...")
    for img_path in test_images:
        results = model(img_path, imgsz=640)
        for r in results:
            n_boxes = len(r.boxes) if r.boxes is not None else 0
            print(f"  {Path(img_path).name}: {n_boxes} detections")
            # Save annotated image
            annotated = r.plot()
            import cv2
            out_name = f"/kaggle/working/pred_{Path(img_path).name}"
            cv2.imwrite(out_name, annotated)
