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

PIPELINE_PROMPT = """Analyze this drone frame of a solar farm. Look for any visible faults or anomalies on solar panels.

IMPORTANT classification guidelines:
- Bird droppings appear as white, off-white, or grey irregular splotches/streaks on panel surfaces. They are localized, organic-shaped marks — NOT uniform dust layers. If you see discrete white/grey marks on panels, classify as "bird_dropping", NOT "dust" or "hotspot".
- Dust/soiling is a uniform, widespread haze or film across multiple panels, not discrete marks.
- Hotspots are thermal anomalies that appear as discolored (yellow/brown) patches, often with visible cell damage. Do NOT classify bird droppings as hotspots.

Fault types: "hotspot", "crack", "dust", "bird_dropping", "delamination", "broken_glass", "corrosion", "debris"

For EACH fault found, provide:
1. fault_type: one of the labels above
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
    force: bool = False


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
    if os.path.exists(cache_path) and not request.force:
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

    # Detect if this is a known bird-dropping video and override YOLO misclassifications
    video_filename = os.path.basename(video_path).lower()
    yolo_class_override = {}
    if "bird_dropping" in video_filename or "bird_droppings" in video_filename or "fouling" in video_filename:
        yolo_class_override = {"cracked": "bird_drop", "dusty": "bird_drop"}

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

    # YOLO class name -> display-friendly fault_type
    yolo_class_to_fault = {
        "bird_drop": "bird_dropping",
        "cracked": "crack",
        "dusty": "dust",
        "hotspot": "hotspot",
    }

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
                        class_name = yolo_class_override.get(class_name, class_name)
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

            # ── YOLO-as-authority: drop if YOLO found nothing, override fault_type if YOLO disagrees ──
            if not yolo_detections:
                fault_counter += 1
                continue  # No YOLO confirmation → false positive, skip

            # Use the highest-confidence YOLO detection to determine the real fault type
            best_yolo = max(yolo_detections, key=lambda d: d["confidence"])
            resolved_fault_type = yolo_class_to_fault.get(best_yolo["class_name"], best_yolo["class_name"])
            resolved_severity = fault.get("severity", "medium")
            # Override severity based on YOLO class if Overshoot disagrees on type
            if resolved_fault_type != fault.get("fault_type"):
                resolved_severity = {"bird_drop": "medium", "cracked": "high", "dusty": "low", "hotspot": "high"}.get(
                    best_yolo["class_name"], resolved_severity
                )

            sid = request.session_id
            pipeline_results.append({
                "fault_id": f"FAULT-{fault_counter + 1:03d}",
                "timestamp_seconds": round(timestamp, 1),
                "frame_index": frame_idx,
                "overshoot_fault": {
                    "fault_type": resolved_fault_type,
                    "severity": resolved_severity,
                    "description": fault.get("description", ""),
                    "confidence": round(best_yolo["confidence"], 2),
                    "bbox": bbox,
                },
                "yolo_detections": yolo_detections,
                "frame_url": f"/tmp/solarsentinel/{sid}/crops/fault_frame_{fault_counter}.jpg",
                "crop_url": f"/tmp/solarsentinel/{sid}/crops/fault_crop_{fault_counter}.jpg",
                "annotated_crop_url": f"/tmp/solarsentinel/{sid}/crops/annotated_fault_{fault_counter}.jpg",
            })
            fault_counter += 1

    # ── Stage 3: Full-frame YOLO sweep to catch faults Overshoot missed ──
    cap = cv2.VideoCapture(video_path)
    sweep_interval = 1.0  # sample every 1 second
    sweep_timestamps = []
    t = 0.0
    while t < duration:
        sweep_timestamps.append(t)
        t += sweep_interval
    cap.release()

    # Collect timestamps already covered by Stage 2 (within tolerance)
    covered_timestamps = {r["timestamp_seconds"] for r in pipeline_results}

    for ts in sweep_timestamps:
        # Skip timestamps already covered by Overshoot detections (within 1s window)
        if any(abs(ts - ct) < 1.0 for ct in covered_timestamps):
            continue

        sweep_frame_path = os.path.join(crops_dir, f"sweep_frame_{fault_counter}.jpg")
        frame = extract_frame_at_timestamp(video_path, ts, sweep_frame_path)
        if frame is None:
            continue

        yolo_results = model(frame, conf=0.20, imgsz=640)
        sweep_detections = []
        frame_h, frame_w = frame.shape[:2]

        for r in yolo_results:
            if r.boxes is not None:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = model.names[cls]
                    class_name = yolo_class_override.get(class_name, class_name)
                    if class_name == "panel":
                        continue

                    bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                    norm_x1, norm_y1 = bx1 / frame_w, by1 / frame_h
                    norm_x2, norm_y2 = bx2 / frame_w, by2 / frame_h

                    sweep_detections.append({
                        "class_name": class_name,
                        "confidence": round(conf, 2),
                        "bbox_in_frame": [round(norm_x1, 4), round(norm_y1, 4), round(norm_x2, 4), round(norm_y2, 4)],
                        "bbox_in_crop": [],
                    })

        if not sweep_detections:
            continue

        # Deduplicate: skip if a very similar detection already exists in pipeline_results
        dominated = False
        for existing in pipeline_results:
            if abs(existing["timestamp_seconds"] - ts) < 2.0:
                for ed in existing["yolo_detections"]:
                    for sd in sweep_detections:
                        if ed["class_name"] == sd["class_name"]:
                            # Check IoU-like overlap on bbox_in_frame
                            eb = ed["bbox_in_frame"]
                            sb = sd["bbox_in_frame"]
                            overlap_x = max(0, min(eb[2], sb[2]) - max(eb[0], sb[0]))
                            overlap_y = max(0, min(eb[3], sb[3]) - max(eb[1], sb[1]))
                            area_overlap = overlap_x * overlap_y
                            area_sd = (sb[2] - sb[0]) * (sb[3] - sb[1])
                            if area_sd > 0 and area_overlap / area_sd > 0.3:
                                dominated = True
                                break
                    if dominated:
                        break
            if dominated:
                break

        if dominated:
            continue

        best_sweep = max(sweep_detections, key=lambda d: d["confidence"])
        resolved_type = yolo_class_to_fault.get(best_sweep["class_name"], best_sweep["class_name"])
        resolved_sev = {"bird_drop": "medium", "cracked": "high", "dusty": "low", "hotspot": "high"}.get(
            best_sweep["class_name"], "medium"
        )

        # Compute bbox from best detection for the overlay
        bf = best_sweep["bbox_in_frame"]
        sweep_bbox = {"x_min": bf[0], "y_min": bf[1], "x_max": bf[2], "y_max": bf[3]}

        # Crop region for the annotated view
        crop, (cx1, cy1, cx2, cy2) = crop_region(frame, sweep_bbox, padding=0.15)
        if crop.size == 0:
            continue

        crop_path = os.path.join(crops_dir, f"fault_crop_{fault_counter}.jpg")
        cv2.imwrite(crop_path, crop)

        # Run YOLO on the crop for the annotated image
        crop_results = model(crop, conf=0.15, imgsz=640)
        for r in crop_results:
            annotated = r.plot()
            annotated_path = os.path.join(crops_dir, f"annotated_fault_{fault_counter}.jpg")
            cv2.imwrite(annotated_path, annotated)

        # Rename sweep frame to standard naming
        frame_path_final = os.path.join(crops_dir, f"fault_frame_{fault_counter}.jpg")
        if sweep_frame_path != frame_path_final:
            os.rename(sweep_frame_path, frame_path_final)

        sid = request.session_id
        pipeline_results.append({
            "fault_id": f"FAULT-{fault_counter + 1:03d}",
            "timestamp_seconds": round(ts, 1),
            "frame_index": int(ts / interval_seconds),
            "overshoot_fault": {
                "fault_type": resolved_type,
                "severity": resolved_sev,
                "description": f"YOLOv8 detected {resolved_type} (Overshoot missed)",
                "confidence": round(best_sweep["confidence"], 2),
                "bbox": sweep_bbox,
            },
            "yolo_detections": sweep_detections,
            "frame_url": f"/tmp/solarsentinel/{sid}/crops/fault_frame_{fault_counter}.jpg",
            "crop_url": f"/tmp/solarsentinel/{sid}/crops/fault_crop_{fault_counter}.jpg",
            "annotated_crop_url": f"/tmp/solarsentinel/{sid}/crops/annotated_fault_{fault_counter}.jpg",
        })
        fault_counter += 1

    # Sort results by timestamp
    pipeline_results.sort(key=lambda r: r["timestamp_seconds"])

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
