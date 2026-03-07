from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import os

router = APIRouter()

class AnalysisRequest(BaseModel):
    detections: List[Dict[str, Any]]
    gee_data: Dict[str, Any]
    fault_types: List[str]

@router.post("/analysis")
async def generate_analysis(request: AnalysisRequest):
    # Calculate totals
    fault_counts = {ft: 0 for ft in request.fault_types}
    total_cost = 0
    
    for det in request.detections:
        ft = det.get("fault_type")
        if ft in fault_counts:
            fault_counts[ft] += 1
        else:
            fault_counts[ft] = 1
        total_cost += det.get("cost_estimate", 0)
    
    total_faults = len(request.detections)
    
    # Static fallback report
    report_text = f"Executive Summary: Our CV scan identified {total_faults} total anomalies across the array. The estimated repair cost currently stands at ${total_cost}. The overall vegetation and shading index (NDVI: {request.gee_data.get('ndvi_mean')}) reveals suitable conditions without major blockage. We recommend immediate repair of the critical hotspots to prevent cascading string failure."
    
    return {
        "report_text": report_text,
        "total_cost": total_cost,
        "fault_counts": fault_counts
    }
