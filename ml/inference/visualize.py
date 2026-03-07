"""
Stage 3: Bounding box overlay visualization.

Draws severity-colored bounding boxes on images with class labels.
"""

import cv2
import numpy as np

# BGR colors for severity levels
SEVERITY_COLORS = {
    "low": (0, 255, 255),       # Yellow
    "medium": (0, 165, 255),    # Orange
    "high": (0, 0, 255),        # Red
    "none": (0, 255, 0),        # Green (clean panels)
}


def draw_fault_overlay(
    image_path: str,
    detections: list[dict],
    output_path: str,
    skip_clean: bool = True,
) -> str:
    """
    Draw bounding boxes color-coded by severity with class labels.

    Args:
        image_path: Path to the original image.
        detections: List of detection dicts (from pipeline.detect_faults).
        output_path: Path to save the annotated image.
        skip_clean: If True, skip drawing boxes for clean panels.

    Returns:
        The output_path where the annotated image was saved.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    for det in detections:
        if skip_clean and det["class"] == "panel":
            continue

        x1, y1, x2, y2 = [int(c) for c in det["bbox"]]
        severity = det.get("severity", "medium")
        color = SEVERITY_COLORS.get(severity, (0, 0, 255))

        # Draw bounding box
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)

        # Build label text
        conf = det.get("confidence", 0)
        label = f"{det['class']} ({severity}) {conf:.0%}"

        # Draw label background
        (text_w, text_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
        )
        label_y = max(y1 - 10, text_h + 5)
        cv2.rectangle(
            img,
            (x1, label_y - text_h - 5),
            (x1 + text_w + 5, label_y + baseline),
            color,
            -1,
        )
        cv2.putText(
            img, label, (x1 + 2, label_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
        )

    cv2.imwrite(output_path, img)
    return output_path
