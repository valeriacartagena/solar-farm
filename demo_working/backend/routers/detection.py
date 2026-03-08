from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import os
import random
import cv2
from pathlib import Path
from ultralytics import YOLO

router = APIRouter()

# Load trained YOLOv8 model once at startup
WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "weights", "best.pt")
WEIGHTS_PATH = os.path.abspath(WEIGHTS_PATH)

_model = None

def get_model():
    global _model
    if _model is None:
        if not os.path.exists(WEIGHTS_PATH):
            raise FileNotFoundError(f"Model weights not found at {WEIGHTS_PATH}")
        _model = YOLO(WEIGHTS_PATH)
    return _model

BASE_DIR = "/tmp/solarsentinel"

class DetectRequest(BaseModel):
    session_id: str
    fault_types: List[str] = []

@router.post("/detect")
async def detect_faults(request: DetectRequest):
    model = get_model()

    # Find frames for this session
    session_dir = os.path.join(BASE_DIR, request.session_id)
    frames_dir = os.path.join(session_dir, "frames")

    if not os.path.exists(frames_dir):
        return {"detections": [], "annotated_frame_urls": [], "error": "Session not found"}

    frame_files = sorted(
        p for p in Path(frames_dir).iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png") and not p.name.startswith("annotated_")
    )

    if not frame_files:
        return {"detections": [], "annotated_frame_urls": [], "error": "No frames found"}

    # Run YOLOv8 inference on all frames
    detections = []
    annotated_urls = []
    base_lat = 35.6
    base_lng = 139.7

    severity_map = {"bird_drop": "moderate", "cracked": "critical", "dusty": "minor", "hotspot": "critical"}
    cost_map = {"critical": (800, 1200), "moderate": (400, 600), "minor": (50, 150)}

    for frame_path in frame_files:
        results = model(str(frame_path), conf=0.25, imgsz=640)

        for r in results:
            # Save annotated frame
            annotated = r.plot()
            annotated_name = f"annotated_{frame_path.name}"
            annotated_path = os.path.join(frames_dir, annotated_name)
            cv2.imwrite(annotated_path, annotated)
            annotated_urls.append(f"/tmp/solarsentinel/{request.session_id}/frames/{annotated_name}")

            # Extract detections
            if r.boxes is not None:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = model.names[cls]

                    # Skip clean panels
                    if class_name == "panel":
                        continue

                    severity = severity_map.get(class_name, "moderate")
                    cost_range = cost_map.get(severity, (50, 150))

                    detections.append({
                        "panel_id": f"PNL-{random.randint(10, 99)}",
                        "fault_type": class_name,
                        "confidence": round(conf, 2),
                        "severity": severity,
                        "lat": round(base_lat + random.uniform(-0.002, 0.002), 6),
                        "lng": round(base_lng + random.uniform(-0.002, 0.002), 6),
                        "cost_estimate": random.randint(*cost_range),
                        "description": f"YOLOv8 detected {class_name} with {conf:.0%} confidence",
                    })

    return {
        "detections": detections,
        "annotated_frame_urls": annotated_urls,
    }
