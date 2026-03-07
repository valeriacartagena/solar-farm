"""
Stage 2: Gemini verification and severity assessment.

Crops detected fault regions and sends them to Gemini for
confirmation, severity rating, and maintenance recommendations.
"""

import json
import os

import google.generativeai as genai
from PIL import Image

# Configurable model name — adjust to whatever is available at the hackathon
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

_gemini_configured = False


def _ensure_configured():
    """Configure the Gemini API client once."""
    global _gemini_configured
    if not _gemini_configured:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY environment variable not set. "
                "Set it to your Gemini API key."
            )
        genai.configure(api_key=api_key)
        _gemini_configured = True


def verify_fault_with_gemini(
    image_path: str,
    bbox: list[float],
    yolo_class: str,
    yolo_conf: float,
) -> dict:
    """
    Crop the detected region and ask Gemini to verify and describe the fault.

    Args:
        image_path: Path to the full image.
        bbox: Bounding box [x1, y1, x2, y2].
        yolo_class: Class label from YOLOv8.
        yolo_conf: Confidence score from YOLOv8.

    Returns:
        Dict with keys: confirmed, fault_class, severity, description, action.
    """
    _ensure_configured()

    img = Image.open(image_path)
    x1, y1, x2, y2 = bbox
    cropped = img.crop((int(x1), int(y1), int(x2), int(y2)))

    prompt = f"""You are a solar panel inspection expert analyzing a cropped region from a drone image.

YOLOv8 detected this region as: {yolo_class} (confidence: {yolo_conf:.2f})

Analyze this image region. Respond ONLY with valid JSON (no markdown, no code fences):
{{
    "confirmed": true or false,
    "fault_class": "the actual fault type you observe",
    "severity": "low" or "medium" or "high",
    "description": "one-sentence description of the fault",
    "action": "recommended maintenance action"
}}

If the region appears to be a false positive (no actual fault visible), set confirmed to false."""

    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content([prompt, cropped])

    # Parse JSON from response, handling potential markdown fences
    text = response.text.strip()
    if text.startswith("```"):
        # Strip markdown code fences
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    return json.loads(text)
