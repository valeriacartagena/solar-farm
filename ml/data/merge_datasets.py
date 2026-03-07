"""
Merge two Roboflow YOLOv8-format datasets into a unified training set.

Dataset 1 (panel-solar): bird_drop, cracked, dusty, panel
Dataset 2 (hotspot detection): hotspot

Unified schema:
  0: bird_drop
  1: cracked
  2: dusty
  3: hotspot
  4: panel
"""

import argparse
import shutil
import yaml
from pathlib import Path
from collections import defaultdict


# Unified class mapping
UNIFIED_CLASSES = {
    0: "bird_drop",
    1: "cracked",
    2: "dusty",
    3: "hotspot",
    4: "panel",
}

SPLITS = ["train", "valid", "test"]


def load_class_names(dataset_dir: Path) -> dict[int, str]:
    """Load class names from a dataset's data.yaml."""
    yaml_path = dataset_dir / "data.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"No data.yaml found in {dataset_dir}")
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    names = data.get("names", {})
    # Handle both list and dict formats
    if isinstance(names, list):
        return {i: name for i, name in enumerate(names)}
    return {int(k): v for k, v in names.items()}


def build_class_remap(source_names: dict[int, str]) -> dict[int, int]:
    """Build a mapping from source class IDs to unified class IDs."""
    # Reverse lookup: unified name -> unified ID
    name_to_unified_id = {v: k for k, v in UNIFIED_CLASSES.items()}

    remap = {}
    for src_id, src_name in source_names.items():
        # Normalize name for matching
        normalized = src_name.lower().strip().replace("-", "_").replace(" ", "_")
        # Handle common aliases
        if normalized in ("birddrop", "bird_drop"):
            normalized = "bird_drop"
        if normalized in ("hotspots",):
            normalized = "hotspot"
        if normalized in ("panel", "clean", "no_fault"):
            normalized = "panel"

        if normalized in name_to_unified_id:
            remap[src_id] = name_to_unified_id[normalized]
        else:
            print(f"  WARNING: Unknown class '{src_name}' (id={src_id}), skipping")
    return remap


def remap_label_file(src_label: Path, dst_label: Path, remap: dict[int, int]):
    """Read a YOLO label file, remap class IDs, and write to destination."""
    lines = []
    with open(src_label) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            old_cls = int(parts[0])
            if old_cls not in remap:
                continue  # Skip unknown classes
            parts[0] = str(remap[old_cls])
            lines.append(" ".join(parts))

    with open(dst_label, "w") as f:
        f.write("\n".join(lines) + "\n" if lines else "")


def merge_dataset(src_dir: Path, dst_dir: Path, remap: dict[int, int], stats: dict):
    """Merge one source dataset into the destination directory."""
    for split in SPLITS:
        img_dir = src_dir / split / "images"
        lbl_dir = src_dir / split / "labels"

        if not img_dir.exists():
            print(f"  Split '{split}' not found in {src_dir}, skipping")
            continue

        dst_img_dir = dst_dir / split / "images"
        dst_lbl_dir = dst_dir / split / "labels"
        dst_img_dir.mkdir(parents=True, exist_ok=True)
        dst_lbl_dir.mkdir(parents=True, exist_ok=True)

        for img_file in sorted(img_dir.iterdir()):
            if img_file.suffix.lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
                continue

            # Handle filename collisions by prefixing with dataset name
            dst_name = img_file.name
            if (dst_img_dir / dst_name).exists():
                dst_name = f"{src_dir.name}_{dst_name}"

            shutil.copy2(img_file, dst_img_dir / dst_name)

            # Copy and remap corresponding label
            label_file = lbl_dir / (img_file.stem + ".txt")
            dst_label = dst_lbl_dir / (Path(dst_name).stem + ".txt")
            if label_file.exists():
                remap_label_file(label_file, dst_label, remap)
            else:
                # Create empty label (no annotations)
                dst_label.touch()

            stats[split] += 1


def generate_data_yaml(dst_dir: Path, dataset_path: str):
    """Generate the unified data.yaml config."""
    config = {
        "path": dataset_path,
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": len(UNIFIED_CLASSES),
        "names": UNIFIED_CLASSES,
    }
    with open(dst_dir / "data.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def count_class_distribution(dst_dir: Path) -> dict[str, int]:
    """Count annotations per class across all splits."""
    counts = defaultdict(int)
    id_to_name = UNIFIED_CLASSES
    for split in SPLITS:
        lbl_dir = dst_dir / split / "labels"
        if not lbl_dir.exists():
            continue
        for lbl_file in lbl_dir.iterdir():
            if lbl_file.suffix != ".txt":
                continue
            with open(lbl_file) as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        cls_id = int(parts[0])
                        counts[id_to_name.get(cls_id, f"unknown_{cls_id}")] += 1
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description="Merge Roboflow YOLOv8 datasets")
    parser.add_argument("--ds1", required=True, help="Path to panel-solar dataset directory")
    parser.add_argument("--ds2", required=True, help="Path to hotspot detection dataset directory")
    parser.add_argument("--output", required=True, help="Path to merged output directory")
    parser.add_argument(
        "--dataset-path",
        default="/kaggle/input/solar-fault-merged",
        help="Value for 'path' in data.yaml (default: Kaggle input path)",
    )
    args = parser.parse_args()

    ds1 = Path(args.ds1)
    ds2 = Path(args.ds2)
    dst = Path(args.output)

    if dst.exists():
        print(f"Output directory {dst} already exists. Remove it first or choose a different path.")
        return

    dst.mkdir(parents=True)

    # Dataset 1: panel-solar
    print(f"Loading dataset 1: {ds1}")
    names1 = load_class_names(ds1)
    print(f"  Classes: {names1}")
    remap1 = build_class_remap(names1)
    print(f"  Remap: {remap1}")

    stats1 = defaultdict(int)
    merge_dataset(ds1, dst, remap1, stats1)
    print(f"  Images copied: {dict(stats1)}")

    # Dataset 2: hotspot detection
    print(f"\nLoading dataset 2: {ds2}")
    names2 = load_class_names(ds2)
    print(f"  Classes: {names2}")
    remap2 = build_class_remap(names2)
    print(f"  Remap: {remap2}")

    stats2 = defaultdict(int)
    merge_dataset(ds2, dst, remap2, stats2)
    print(f"  Images copied: {dict(stats2)}")

    # Generate unified data.yaml
    generate_data_yaml(dst, args.dataset_path)

    # Summary
    print("\n=== Merge Summary ===")
    total = defaultdict(int)
    for s in [stats1, stats2]:
        for k, v in s.items():
            total[k] += v
    for split in SPLITS:
        print(f"  {split}: {total[split]} images")
    print(f"  Total: {sum(total.values())} images")

    dist = count_class_distribution(dst)
    print("\n  Class distribution (annotations):")
    for cls_name, count in sorted(dist.items()):
        print(f"    {cls_name}: {count}")

    print(f"\n  Output: {dst}")
    print(f"  data.yaml: {dst / 'data.yaml'}")


if __name__ == "__main__":
    main()
