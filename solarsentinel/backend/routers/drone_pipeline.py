from fastapi import APIRouter
from pydantic import BaseModel
import os
import asyncio
import json
import cv2
import overshoot
from dotenv import load_dotenv
from routers.detection import get_model

load_dotenv()

router = APIRouter()

BASE_DIR = "/tmp/solarsentinel"

PIPELINE_PROMPT = """Analyze this drone frame of a solar farm. Look for any visible faults or anomalies on solar panels including: hotspots, cracked or broken cells, dust/soiling, bird droppings, delamination, broken glass, corrosion, or debris.

For EACH fault found, provide:
1. fault_type: a short label (e.g. "hotspot", "crack", "dust", "bird_dropping", "delamination", "broken_glass", "corrosion", "debris")
2. severity: "low", "medium", or "high"
3. description: one sentence describing the fault
4. confidence: 0.0 to 1.0
5. bbox: normalized bounding box coordinates where (0,0) is the top-left corner and (1,1) is the bottom-right corner of the image. Provide x_min, y_min (top-left of the fault region) and x_max, y_max (bottom-right of the fault region).

If no faults are visible, set faults_detected to false and return an empty faults array."""

PIPELINE_SCHEMA = {
    "type": "object",
    "properties": {
        "faults_detected": {"type": "boolean"},
        "faults": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fault_type": {"type": "string"},
                    "severity": {"type": "string"},
                    "description": {"type": "string"},
                    "confidence": {"type": "number"},
                    "bbox": {
                        "type": "object",
                        "properties": {
                            "x_min": {"type": "number"},
                            "y_min": {"type": "number"},
                            "x_max": {"type": "number"},
                            "y_max": {"type": "number"}
                        },
                        "required": ["x_min", "y_min", "x_max", "y_max"]
                    }
                },
                "required": ["fault_type", "severity", "description", "confidence", "bbox"]
            }
        }
    },
    "required": ["faults_detected", "faults"]
}


def extract_frame_at_timestamp(video_path: str, timestamp_sec: float, output_path: str):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000)
    ret, frame = cap.read()
    cap.release()
    if ret:
        cv2.imwrite(output_path, frame)
        return frame
    return None


def crop_region(frame, bbox, padding=0.15):
    h, w = frame.shape[:2]
    x1 = int(max(0, (bbox["x_min"] - padding) * w))
    y1 = int(max(0, (bbox["y_min"] - padding) * h))
    x2 = int(min(w, (bbox["x_max"] + padding) * w))
    y2 = int(min(h, (bbox["y_max"] + padding) * h))
    return frame[y1:y2, x1:x2], (x1, y1, x2, y2)


class PipelineRequest(BaseModel):
    session_id: str


@router.post("/drone-pipeline")
async def drone_pipeline(request: PipelineRequest):
    api_key = os.getenv("OVERSHOOT_API_KEY")
    if not api_key:
        return {"error": "OVERSHOOT_API_KEY not configured"}

    session_dir = os.path.join(BASE_DIR, request.session_id)
    if not os.path.exists(session_dir):
        return {"error": "Session not found"}

    # Check for cached results
    cache_path = os.path.join(session_dir, "pipeline_cache.json")
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)

    # Find video file
    video_path = None
    for f in os.listdir(session_dir):
        if f.endswith(('.mp4', '.mov', '.avi', '.mkv')):
            video_path = os.path.join(session_dir, f)
            break

    if not video_path:
        return {"error": "No video file found in session"}

    # Create crops directory
    crops_dir = os.path.join(session_dir, "crops")
    os.makedirs(crops_dir, exist_ok=True)

    # Get video duration for smarter wait time
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 30
    cap.release()

    # ── Stage 1: Overshoot (coarse fault detection with bounding boxes) ──
    interval_seconds = 2.0
    frame_results = []  # list of (frame_index, timestamp, parsed_result)
    frame_counter = [0]  # mutable counter for callback

    def on_result(r: overshoot.StreamInferenceResult):
        idx = frame_counter[0]
        frame_counter[0] += 1
        timestamp = idx * interval_seconds
        if r.ok and r.result:
            try:
                parsed = json.loads(r.result)
                frame_results.append((idx, timestamp, parsed))
            except json.JSONDecodeError:
                pass

    def on_error(e: Exception):
        print(f"Pipeline Overshoot error: {e}")

    client = overshoot.Overshoot(api_key=api_key)

    try:
        stream = await client.streams.create(
            source=overshoot.FileSource(path=video_path, loop=False),
            prompt=PIPELINE_PROMPT,
            model="Qwen/Qwen3.5-9B",
            on_result=on_result,
            on_error=on_error,
            output_schema=PIPELINE_SCHEMA,
            mode="frame",
            interval_seconds=interval_seconds,
        )

        # Wait for video to finish processing (duration + buffer for inference)
        wait_time = min(duration + 20, 60)
        await asyncio.sleep(wait_time)
        try:
            await stream.close()
        except (ProcessLookupError, OSError):
            pass
    finally:
        try:
            await client.close()
        except (ProcessLookupError, OSError):
            pass

    # ── Stage 2: YOLOv8 on cropped fault regions ──
    model = get_model()
    pipeline_results = []
    fault_counter = 0

    severity_map = {"bird_drop": "moderate", "cracked": "critical", "dusty": "minor", "hotspot": "critical"}
    cost_map = {"critical": (800, 1200), "moderate": (400, 600), "minor": (50, 150)}

    for frame_idx, timestamp, result in frame_results:
        if not result.get("faults_detected") or not result.get("faults"):
            continue

        for fault in result["faults"]:
            bbox = fault.get("bbox")
            if not bbox:
                continue

            # Clamp bbox values to valid range
            bbox = {
                "x_min": max(0, min(1, bbox.get("x_min", 0))),
                "y_min": max(0, min(1, bbox.get("y_min", 0))),
                "x_max": max(0, min(1, bbox.get("x_max", 1))),
                "y_max": max(0, min(1, bbox.get("y_max", 1))),
            }

            # Skip invalid bboxes
            if bbox["x_max"] <= bbox["x_min"] or bbox["y_max"] <= bbox["y_min"]:
                continue

            # Extract the frame at this timestamp
            frame_path = os.path.join(crops_dir, f"fault_frame_{fault_counter}.jpg")
            frame = extract_frame_at_timestamp(video_path, timestamp, frame_path)
            if frame is None:
                continue

            # Crop the fault region with padding
            crop, (cx1, cy1, cx2, cy2) = crop_region(frame, bbox, padding=0.15)
            if crop.size == 0:
                continue

            crop_path = os.path.join(crops_dir, f"fault_crop_{fault_counter}.jpg")
            cv2.imwrite(crop_path, crop)

            # Run YOLOv8 on the cropped region
            yolo_results = model(crop, conf=0.15, imgsz=640)
            yolo_detections = []

            frame_h, frame_w = frame.shape[:2]
            crop_h, crop_w = crop.shape[:2]

            for r in yolo_results:
                # Save annotated crop
                annotated = r.plot()
                annotated_path = os.path.join(crops_dir, f"annotated_fault_{fault_counter}.jpg")
                cv2.imwrite(annotated_path, annotated)

                if r.boxes is not None:
                    for box in r.boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        class_name = model.names[cls]
                        if class_name == "panel":
                            continue

                        # Box coords in crop pixel space
                        bx1, by1, bx2, by2 = box.xyxy[0].tolist()

                        # Remap to full-frame normalized coords
                        norm_x1 = (cx1 + bx1) / frame_w
                        norm_y1 = (cy1 + by1) / frame_h
                        norm_x2 = (cx1 + bx2) / frame_w
                        norm_y2 = (cy1 + by2) / frame_h

                        yolo_detections.append({
                            "class_name": class_name,
                            "confidence": round(conf, 2),
                            "bbox_in_frame": [round(norm_x1, 4), round(norm_y1, 4), round(norm_x2, 4), round(norm_y2, 4)],
                            "bbox_in_crop": [round(bx1), round(by1), round(bx2), round(by2)],
                        })

            sid = request.session_id
            pipeline_results.append({
                "fault_id": f"FAULT-{fault_counter + 1:03d}",
                "timestamp_seconds": round(timestamp, 1),
                "frame_index": frame_idx,
                "overshoot_fault": {
                    "fault_type": fault.get("fault_type", "unknown"),
                    "severity": fault.get("severity", "medium"),
                    "description": fault.get("description", ""),
                    "confidence": round(fault.get("confidence", 0.5), 2),
                    "bbox": bbox,
                },
                "yolo_detections": yolo_detections,
                "frame_url": f"/tmp/solarsentinel/{sid}/crops/fault_frame_{fault_counter}.jpg",
                "crop_url": f"/tmp/solarsentinel/{sid}/crops/fault_crop_{fault_counter}.jpg",
                "annotated_crop_url": f"/tmp/solarsentinel/{sid}/crops/annotated_fault_{fault_counter}.jpg",
            })
            fault_counter += 1

    response = {
        "pipeline_results": pipeline_results,
        "total_faults": len(pipeline_results),
        "frames_analyzed": len(frame_results),
        "source": "overshoot_yolo_pipeline",
    }

    # Cache results for instant re-runs
    with open(cache_path, "w") as f:
        json.dump(response, f)

    return response
