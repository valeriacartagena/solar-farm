from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import random

router = APIRouter()

class DetectRequest(BaseModel):
    session_id: str
    fault_types: List[str]

@router.post("/detect")
async def detect_faults(request: DetectRequest):
    # Base center of solar farm mapping
    base_lat = 35.6
    base_lng = 139.7
    
    detections = []
    # Mocking logic
    num_mock_detections = random.randint(8, 12)
    
    for i in range(num_mock_detections):
        fault_type = random.choice(request.fault_types)
        confidence = random.uniform(0.3, 0.95)
        
        # Jitter coordinates
        lat = base_lat + random.uniform(-0.002, 0.002)
        lng = base_lng + random.uniform(-0.002, 0.002)
        
        if confidence > 0.7:
            severity = "critical"
            cost = random.randint(800, 1200)
        elif confidence > 0.4:
            severity = "moderate"
            cost = random.randint(400, 600)
        else:
            severity = "minor"
            cost = random.randint(50, 150)
            
        detections.append({
            "panel_id": f"PNL-X{random.randint(10, 99)}",
            "fault_type": fault_type,
            "confidence": round(confidence, 2),
            "severity": severity,
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "cost_estimate": cost,
            "description": f"Automated detection of {fault_type} via drone scan."
        })
        
    # Return placeholder annotated frame
    return {
        "detections": detections,
        "annotated_frame_urls": ["/sample_data/frames/annotated_frame_0.jpg"]
    }
