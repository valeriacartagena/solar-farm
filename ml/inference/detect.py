"""
Stage 1: YOLOv8 solar panel fault detection.

Loads the trained YOLOv8-s model and runs inference on drone imagery,
returning bounding boxes with class labels and confidence scores.
"""

from pathlib import Path

from ultralytics import YOLO

# Module-level model cache to avoid reloading per call
_model_cache: dict[str, YOLO] = {}


def _get_model(model_path: str) -> YOLO:
    """Load and cache the YOLO model."""
    if model_path not in _model_cache:
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Model weights not found at '{model_path}'. "
                "Train the model first using training/train.py, then place best.pt in weights/."
            )
        _model_cache[model_path] = YOLO(model_path)
    return _model_cache[model_path]


def detect_panels(
    image_path: str,
    model_path: str = "ml/weights/best.pt",
    conf_threshold: float = 0.25,
    imgsz: int = 640,
) -> list[dict]:
    """
    Run YOLOv8 detection on a single image.

    Args:
        image_path: Path to the input image.
        model_path: Path to trained YOLOv8 weights.
        conf_threshold: Minimum confidence threshold.
        imgsz: Input image size for inference.

    Returns:
        List of detections, each with keys: bbox, class, confidence.
    """
    model = _get_model(model_path)
    results = model(image_path, conf=conf_threshold, imgsz=imgsz)

    detections = []
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            class_name = model.names[cls]
            detections.append({
                "bbox": [x1, y1, x2, y2],
                "class": class_name,
                "confidence": round(conf, 4),
            })

    return detections
