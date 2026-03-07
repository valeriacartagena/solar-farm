from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import random
from datetime import datetime

router = APIRouter()

class GEERequest(BaseModel):
    lat: float
    lng: float
    dataset_ids: List[str]

@router.post("/gee")
async def get_gee_data(request: GEERequest):
    # Mock fallback if auth fails or keys omitted
    return {
        "thumbnail_url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/15/12918/29080",
        "ndvi_mean": round(random.uniform(0.3, 0.45), 2),
        "cloud_cover_pct": round(random.uniform(2.0, 15.0), 1),
        "acquisition_date": datetime.today().strftime('%Y-%m-%d'),
        "datasets_used": request.dataset_ids,
        "mock": True
    }
