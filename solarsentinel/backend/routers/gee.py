"""
gee.py — GEE satellite analysis router for Radiant.

Endpoints:
  POST /api/farm-lookup   — USPVDB metadata lookup from lat/lng
  POST /api/gee           — Full GEE satellite analysis + CV fault fusion
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional

import ee
import httpx
from fastapi import APIRouter
from pydantic import BaseModel

# Ensure backend package is on sys.path so 'utils' resolves correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.geo_utils import (
    pull_sentinel2_to_df,
    pull_landsat_to_df,
    pull_solar_irradiance_to_df,
    build_farm_summary_df,
    calculate_ideal_efficiency,
    enrich_detections_with_satellite,
    generate_thumbnail_url,
    mock_gee_response,
    haversine_km,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── GEE INITIALISATION ───────────────────────────────────────────────────────

_gee_initialized = False


def init_gee():
    """
    Initialize GEE with service account credentials (server-safe, non-interactive).
    Falls back gracefully if credentials are missing.
    """
    global _gee_initialized
    if _gee_initialized:
        return True

    sa_email = os.getenv("GEE_SERVICE_ACCOUNT")
    sa_key   = os.getenv("GEE_KEY_FILE")
    gee_project = os.getenv("GEE_PROJECT")

    if sa_email and sa_key and os.path.exists(sa_key):
        try:
            credentials = ee.ServiceAccountCredentials(email=sa_email, key_file=sa_key)
            ee.Initialize(credentials, project=gee_project)
            _gee_initialized = True
            logger.info("GEE initialized via service account.")
            return True
        except Exception as e:
            logger.warning(f"GEE service account init failed: {e}")

    # Fallback: try application default credentials
    try:
        if gee_project:
            ee.Initialize(project=gee_project)
        else:
            ee.Initialize()
        _gee_initialized = True
        logger.info("GEE initialized via application default credentials.")
        return True
    except Exception as e:
        logger.warning(f"GEE initialization failed (will use mock): {e}")
        return False


# ─── PYDANTIC MODELS ──────────────────────────────────────────────────────────

class DetectionItem(BaseModel):
    panel_id: str
    fault_type: str
    confidence: float
    severity: str
    lat: float
    lng: float
    cost_estimate: Optional[float] = None


class FarmLookupRequest(BaseModel):
    lat: float
    lng: float
    radius_km: float = 5.0


class GEERequest(BaseModel):
    lat: float
    lng: float
    area_sq_ft: Optional[float] = None
    module_type: Optional[str] = "crystalline silicon"
    axis_type: Optional[str] = "Fixed"
    capacity_dc_mw: Optional[float] = 1.0
    dataset_ids: List[str] = [
        "COPERNICUS/S2_SR_HARMONIZED",
        "LANDSAT/LC09/C02/T1_L2",
    ]
    detections: Optional[List[DetectionItem]] = []


# ─── ENDPOINT 1: FARM LOOKUP ─────────────────────────────────────────────────

@router.post("/farm-lookup")
async def farm_lookup(body: FarmLookupRequest):
    """
    Query the USPVDB REST API to find the nearest solar facility to the given
    coordinates. Returns facility metadata to auto-populate the sidebar.
    """
    lat, lng = body.lat, body.lng
    delta = body.radius_km / 111.0
    url = (
        f"https://energy.usgs.gov/api/uspvdb/v1/facilities"
        f"?p_lon=gte.{lng - delta}&p_lon=lte.{lng + delta}"
        f"&p_lat=gte.{lat - delta}&p_lat=lte.{lat + delta}"
        f"&limit=10"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            facilities = resp.json()
    except Exception as e:
        logger.warning(f"USPVDB lookup failed: {e}")
        return {"found": False, "error": str(e)}

    if not facilities:
        return {"found": False}

    closest = min(
        facilities,
        key=lambda f: haversine_km(lat, lng, float(f.get("ylat", 0)), float(f.get("xlong", 0)))
    )

    return {
        "found": True,
        "facility_name":    closest.get("p_name"),
        "capacity_dc_mw":   closest.get("p_cap_dc"),
        "module_type":      closest.get("p_type", "unknown"),
        "axis_type":        closest.get("p_axis", "Fixed"),
        "year_operational": closest.get("p_year_op"),
        "state":            closest.get("p_state"),
        "verified_lat":     closest["ylat"],
        "verified_lng":     closest["xlong"],
        "distance_km":      round(
            haversine_km(lat, lng, float(closest["ylat"]), float(closest["xlong"])), 2
        ),
    }


# ─── ENDPOINT 2: FULL GEE ANALYSIS ───────────────────────────────────────────

@router.post("/gee")
async def gee_endpoint(body: GEERequest):
    """
    Main satellite analysis endpoint:
      1. Pull satellite data from each selected dataset (Sentinel-2, Landsat, HLS)
      2. Convert GEE ImageCollections → pandas DataFrames
      3. Pull GHI/DNI/GTI from Global Solar Atlas
      4. Merge into a single farm-level DataFrame
      5. Calculate ideal efficiency from satellite-derived conditions
      6. Fuse satellite data with CV-detected fault pins (the key output)
      7. Return enriched detections + farm summary + efficiency metrics
    """
    gee_available = init_gee()

    if not gee_available:
        logger.info("Using mock GEE response (credentials not configured).")
        detections = [d.dict() for d in body.detections] if body.detections else []
        return mock_gee_response(
            lat=body.lat,
            lng=body.lng,
            capacity_dc_mw=body.capacity_dc_mw or 1.0,
            detections=detections,
            module_type=body.module_type or "crystalline silicon",
            axis_type=body.axis_type or "Fixed",
        )

    try:
        result = await asyncio.to_thread(_run_gee_analysis, body)
        return result
    except Exception as e:
        logger.error(f"GEE analysis failed: {e}", exc_info=True)
        detections = [d.dict() for d in body.detections] if body.detections else []
        return mock_gee_response(
            lat=body.lat,
            lng=body.lng,
            capacity_dc_mw=body.capacity_dc_mw or 1.0,
            detections=detections,
            module_type=body.module_type or "crystalline silicon",
            axis_type=body.axis_type or "Fixed",
        )


def _run_gee_analysis(body: GEERequest) -> dict:
    """
    Synchronous core of the GEE analysis pipeline.
    Runs inside asyncio.to_thread() to avoid blocking FastAPI's event loop.
    """
    lat, lng = body.lat, body.lng
    capacity_dc_mw = body.capacity_dc_mw or 1.0
    module_type    = body.module_type or "crystalline silicon"
    axis_type      = body.axis_type   or "Fixed"

    PAD = 0.005  # ~550m bounding box around farm centre
    aoi        = ee.Geometry.Rectangle([lng - PAD, lat - PAD, lng + PAD, lat + PAD])
    farm_point = ee.Geometry.Point([lng, lat])

    end_date   = datetime.utcnow()
    start_date = end_date - timedelta(days=90)

    # ── Stage 1: Pull each dataset → DataFrame ────────────────────────────────
    dataset_dfs = {}
    for dataset_id in body.dataset_ids:
        if "S2" in dataset_id or "HLS" in dataset_id:
            df = pull_sentinel2_to_df(dataset_id, aoi, farm_point, start_date, end_date)
        elif "LC09" in dataset_id or "LC08" in dataset_id:
            df = pull_landsat_to_df(dataset_id, aoi, farm_point, start_date, end_date)
        else:
            df = None

        if df is not None and not df.empty:
            dataset_dfs[dataset_id] = df

    # ── Stage 2: Solar irradiance ─────────────────────────────────────────────
    irradiance_df = pull_solar_irradiance_to_df(aoi)

    # ── Stage 3: Merge all DataFrames ─────────────────────────────────────────
    farm_df = build_farm_summary_df(dataset_dfs, irradiance_df)

    # ── Stage 4: Efficiency model ─────────────────────────────────────────────
    efficiency_result, risk_flags = calculate_ideal_efficiency(
        module_type=module_type,
        axis_type=axis_type,
        farm_df=farm_df,
        capacity_dc_mw=capacity_dc_mw,
    )

    # ── Stage 5: Fault fusion ─────────────────────────────────────────────────
    detections = [d.dict() for d in body.detections] if body.detections else []
    enriched_detections = enrich_detections_with_satellite(
        detections=detections,
        farm_df=farm_df,
        efficiency_result=efficiency_result,
        module_type=module_type,
        axis_type=axis_type,
        capacity_dc_mw=capacity_dc_mw,
    )

    # ── Stage 6: thumbnail ────────────────────────────────────────────────────
    thumbnail_url = generate_thumbnail_url(aoi, start_date, end_date)

    # ── Build response ────────────────────────────────────────────────────────
    def safe_mean(col):
        if farm_df.empty or col not in farm_df.columns:
            return None
        import pandas as pd
        vals = pd.to_numeric(farm_df[col], errors="coerce").dropna()
        return round(float(vals.mean()), 3) if not vals.empty else None

    return {
        "thumbnail_url": thumbnail_url,
        "acquisition_date_range": (
            f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        ),
        "farm_summary": (
            farm_df.to_dict(orient="records")
            if not farm_df.empty
            else []
        ),
        "environmental_conditions": {
            "lst_celsius":     safe_mean("lst_celsius"),
            "ndvi_mean":       safe_mean("ndvi"),
            "bsi_mean":        safe_mean("bsi"),
            "cloud_cover_pct": safe_mean("cloud_cover"),
            "ghi_kwh_m2_day":  (
                round(float(irradiance_df["GHI"].iloc[0]), 2)
                if not irradiance_df.empty and irradiance_df["GHI"].iloc[0] is not None
                else None
            ),
            "dni_kwh_m2_day":  (
                round(float(irradiance_df["DNI"].iloc[0]), 2)
                if not irradiance_df.empty and irradiance_df["DNI"].iloc[0] is not None
                else None
            ),
            "gti_kwh_m2_day":  (
                round(float(irradiance_df["GTI"].iloc[0]), 2)
                if not irradiance_df.empty and irradiance_df["GTI"].iloc[0] is not None
                else None
            ),
        },
        "efficiency": efficiency_result,
        "risk_flags": risk_flags,
        "enriched_detections": enriched_detections,
        "dataset_dataframes": {
            k: v.to_dict(orient="records") for k, v in dataset_dfs.items()
        },
        "mock": False,
    }
