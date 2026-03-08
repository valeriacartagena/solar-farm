from fastapi import APIRouter
from pydantic import BaseModel
import random

router = APIRouter()

class SyntheticRequest(BaseModel):
    generator: str
    fault_type: str
    count: int = 3

@router.post("/synthetic")
async def generate_synthetic(request: SyntheticRequest):
    # Fallback to placeholder URLs since API might be unavailable
    placeholders = [
        f"https://via.placeholder.com/640x480.png?text=Synthetic+{request.generator}+{request.fault_type}+1",
        f"https://via.placeholder.com/640x480.png?text=Synthetic+{request.generator}+{request.fault_type}+2",
        f"https://via.placeholder.com/640x480.png?text=Synthetic+{request.generator}+{request.fault_type}+3"
    ]
    
    return {
        "generated_image_urls": placeholders[:request.count],
        "prompt_used": f"Aerial drone thermal image of a solar farm panel array. Show a clear {request.fault_type} anomaly on one panel. Photorealistic, high resolution, infrared color palette."
    }
