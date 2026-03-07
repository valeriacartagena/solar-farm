"""
Full end-to-end detection pipeline.

Combines YOLOv8 detection (Stage 1), Gemini verification (Stage 2),
and returns enriched fault detections matching the interface contract.
"""

from ml.inference.detect import detect_panels
from ml.inference.gemini_verify import verify_fault_with_gemini


def detect_faults(
    image_path: str,
    model_path: str = "ml/weights/best.pt",
    use_gemini: bool = True,
    conf_threshold: float = 0.25,
) -> list[dict]:
    """
    Full pipeline: YOLOv8 detect -> Gemini verify -> enriched detections.

    Args:
        image_path: Path to a drone video frame (RGB or thermal image).
        model_path: Path to trained YOLOv8 weights.
        use_gemini: Whether to use Gemini for verification. Set False for offline testing.
        conf_threshold: Minimum detection confidence.

    Returns:
        List of detected faults:
        [
            {
                "bbox": [x1, y1, x2, y2],
                "class": "hotspot",
                "confidence": 0.87,
                "severity": "high",
                "description": "Thermal anomaly indicating cell mismatch",
                "action": "Schedule immediate inspection"
            },
            ...
        ]
    """
    # Stage 1: YOLOv8 detection
    raw_detections = detect_panels(
        image_path, model_path=model_path, conf_threshold=conf_threshold
    )

    # Stage 2: Gemini verification (only for fault classes)
    enriched = []
    for det in raw_detections:
        if det["class"] == "panel":
            enriched.append({
                **det,
                "severity": "none",
                "description": "Clean panel",
                "action": "No action needed",
            })
            continue

        if not use_gemini:
            enriched.append({
                **det,
                "severity": "medium",
                "description": f"Detected {det['class']} fault",
                "action": "Manual inspection recommended",
            })
            continue

        try:
            gemini_result = verify_fault_with_gemini(
                image_path, det["bbox"], det["class"], det["confidence"]
            )
            if gemini_result.get("confirmed", True):
                enriched.append({
                    **det,
                    "severity": gemini_result.get("severity", "medium"),
                    "description": gemini_result.get("description", ""),
                    "action": gemini_result.get("action", ""),
                })
            # If not confirmed, it's a false positive — drop it
        except Exception as e:
            # If Gemini fails, keep the detection with default severity
            enriched.append({
                **det,
                "severity": "medium",
                "description": f"Gemini verification failed: {e}",
                "action": "Manual inspection recommended",
            })

    return enriched
