"""
geo_utils.py — GEE helper functions, efficiency model, and fault fusion.

Contains:
  - gee_array_to_df()           GEE getRegion() → pandas DataFrame
  - pull_sentinel2_to_df()      Sentinel-2/HLS NDVI/BSI/NDWI time-series
  - pull_landsat_to_df()        Landsat 9 Land-Surface Temperature
  - pull_solar_irradiance_to_df() Global Solar Atlas GHI/DNI/GTI
  - build_farm_summary_df()     Merge all dataset DataFrames
  - calculate_ideal_efficiency() Physics-based efficiency model from farm_df
  - enrich_detections_with_satellite() KEY fusion: CV faults + satellite context
  - generate_thumbnail_url()    GEE Sentinel-2 thumbnail for Leaflet overlay
  - mock_gee_response()         Deterministic fallback (no GEE credentials)
  - haversine_km()              Great-circle distance
"""

import ee
import pandas as pd
import numpy as np
import hashlib
import random
import math
from datetime import datetime
from typing import Optional


# ─── GEE ARRAY → DATAFRAME ───────────────────────────────────────────────────

def gee_array_to_df(region_array: list, band_cols: list) -> pd.DataFrame:
    """
    Convert GEE ImageCollection.getRegion().getInfo() output to a pandas DataFrame.
    region_array[0] = header row ['id','longitude','latitude','time', band1, ...]
    region_array[1:] = data rows
    """
    if len(region_array) <= 1:
        return pd.DataFrame()

    headers = region_array[0]
    rows = region_array[1:]
    df = pd.DataFrame(rows, columns=headers)

    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df = df.rename(columns={"time": "date"})
    if "longitude" in df.columns:
        df = df.rename(columns={"longitude": "lng", "latitude": "lat"})

    # Drop rows where all band values are None (cloudy/no-data scenes)
    valid_cols = [c for c in band_cols if c in df.columns]
    if valid_cols:
        df = df.dropna(subset=valid_cols)

    for col in band_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "date" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)

    return df


# ─── PULL SENTINEL-2 / HLS → DATAFRAME ───────────────────────────────────────

def pull_sentinel2_to_df(
    dataset_id: str, aoi, farm_point, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    """
    Pull Sentinel-2 or HLS ImageCollection from GEE.
    Computes NDVI, NDWI, BSI per image and converts time-series to DataFrame.
    Uses getRegion() at 10m scale centred on the farm point.
    """
    try:
        collection = (
            ee.ImageCollection(dataset_id)
            .filterBounds(aoi)
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 25))
        )

        def add_indices(image):
            ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
            ndwi = image.normalizedDifference(["B3", "B8"]).rename("ndwi")
            bsi = image.expression(
                "((SWIR + RED) - (NIR + BLUE)) / ((SWIR + RED) + (NIR + BLUE))",
                {
                    "SWIR": image.select("B11"),
                    "RED":  image.select("B4"),
                    "NIR":  image.select("B8"),
                    "BLUE": image.select("B2"),
                }
            ).rename("bsi")
            cloud = image.get("CLOUDY_PIXEL_PERCENTAGE")
            return (image
                    .addBands(ndvi)
                    .addBands(ndwi)
                    .addBands(bsi)
                    .set("cloud_cover", cloud))

        indexed = collection.map(add_indices).select(["ndvi", "ndwi", "bsi"])
        region_data = indexed.getRegion(farm_point, scale=10).getInfo()
        df = gee_array_to_df(region_data, band_cols=["ndvi", "ndwi", "bsi"])
        df["dataset"] = dataset_id
        return df

    except Exception as e:
        import logging
        logging.warning(f"Sentinel-2 pull failed for {dataset_id}: {e}")
        return pd.DataFrame()


# ─── PULL LANDSAT LST → DATAFRAME ────────────────────────────────────────────

def pull_landsat_to_df(
    dataset_id: str, aoi, farm_point, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    """
    Pull Landsat 9 Collection 2 Level-2 from GEE.
    Converts ST_B10 thermal band to Celsius.
    Returns time-series DataFrame with 'lst_celsius' column.
    Scale: raw × 0.00341802 + 149.0 → Kelvin → subtract 273.15 → Celsius
    """
    try:
        collection = (
            ee.ImageCollection(dataset_id)
            .filterBounds(aoi)
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            .filter(ee.Filter.lt("CLOUD_COVER", 30))
        )

        def compute_lst(image):
            lst_celsius = (
                image.select("ST_B10")
                .multiply(0.00341802)
                .add(149.0)
                .subtract(273.15)
                .rename("lst_celsius")
            )
            return image.addBands(lst_celsius)

        lst_collection = collection.map(compute_lst).select(["lst_celsius"])
        region_data = lst_collection.getRegion(farm_point, scale=30).getInfo()
        df = gee_array_to_df(region_data, band_cols=["lst_celsius"])
        df["dataset"] = dataset_id
        return df

    except Exception as e:
        import logging
        logging.warning(f"Landsat LST pull failed for {dataset_id}: {e}")
        return pd.DataFrame()


# ─── PULL SOLAR IRRADIANCE (GHI/DNI/GTI) → DATAFRAME ────────────────────────

def pull_solar_irradiance_to_df(aoi) -> pd.DataFrame:
    """
    Pull long-term average solar irradiance from the Global Solar Atlas in GEE.
    Returns a single-row DataFrame with GHI, DNI, GTI in kWh/m²/day.
    Uses reduceRegion() on community catalog assets (no upload needed).
    """
    try:
        GHI_ASSET = "projects/earthengine-legacy/assets/projects/sat-io/open-datasets/global_solar_atlas/ghi_LTAy_AvgDailyTotals"
        DNI_ASSET = "projects/earthengine-legacy/assets/projects/sat-io/open-datasets/global_solar_atlas/dni_LTAy_AvgDailyTotals"
        GTI_ASSET = "projects/earthengine-legacy/assets/projects/sat-io/open-datasets/global_solar_atlas/gti_LTAy_AvgDailyTotals"

        irr_stack = (
            ee.Image(GHI_ASSET).rename("GHI")
            .addBands(ee.Image(DNI_ASSET).rename("DNI"))
            .addBands(ee.Image(GTI_ASSET).rename("GTI"))
        )

        stats = irr_stack.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=250,
            maxPixels=1e9,
        ).getInfo()

        return pd.DataFrame([{
            "GHI": stats.get("GHI"),
            "DNI": stats.get("DNI"),
            "GTI": stats.get("GTI"),
        }])

    except Exception as e:
        import logging
        logging.warning(f"Solar irradiance pull failed: {e}")
        return pd.DataFrame([{"GHI": None, "DNI": None, "GTI": None}])


# ─── BUILD FARM SUMMARY DATAFRAME ────────────────────────────────────────────

def build_farm_summary_df(dataset_dfs: dict, irradiance_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge all per-dataset DataFrames into one farm-level summary DataFrame.
    Each row = one observation date with all available satellite metrics.
    """
    combined = [df for df in dataset_dfs.values() if not df.empty]

    if not combined:
        return pd.DataFrame()

    merged = pd.concat(combined, ignore_index=True)

    agg_cols = {
        col: "mean"
        for col in ["ndvi", "ndwi", "bsi", "lst_celsius", "cloud_cover"]
        if col in merged.columns
    }

    if "date" in merged.columns and agg_cols:
        summary = merged.groupby("date").agg(agg_cols).reset_index()
    else:
        # No date column — just take the whole merged df
        summary = merged

    # Append irradiance (static — same for all dates)
    if not irradiance_df.empty and irradiance_df["GHI"].iloc[0] is not None:
        summary["ghi_kwh_m2_day"] = irradiance_df["GHI"].iloc[0]
        summary["dni_kwh_m2_day"] = irradiance_df["DNI"].iloc[0]
        summary["gti_kwh_m2_day"] = irradiance_df["GTI"].iloc[0]

    return summary


# ─── CALCULATE IDEAL EFFICIENCY ──────────────────────────────────────────────

NAMEPLATE_EFFICIENCY = {
    "crystalline silicon":     20.1,
    "monocrystalline silicon": 22.0,
    "cdte":                    18.6,
    "thin film":               16.0,
    "cigs":                    17.5,
    "bifacial":                21.5,
    "unknown":                 18.0,
}
TEMP_COEFFICIENT = {
    "crystalline silicon":     -0.40,
    "monocrystalline silicon": -0.35,
    "cdte":                    -0.25,
    "thin film":               -0.28,
    "cigs":                    -0.32,
    "bifacial":                -0.35,
    "unknown":                 -0.38,
}


def calculate_ideal_efficiency(
    module_type: str,
    axis_type: str,
    farm_df: pd.DataFrame,
    capacity_dc_mw: float,
) -> tuple:
    """
    Derive efficiency inputs from the merged satellite DataFrame and compute
    theoretical ideal efficiency factoring in temperature, shading, soiling,
    and cloud/irradiance conditions.
    """
    key = (module_type or "unknown").lower()
    nameplate_eff = NAMEPLATE_EFFICIENCY.get(key, 18.0)
    temp_coeff    = TEMP_COEFFICIENT.get(key, -0.38)

    def col_mean(col):
        if farm_df.empty or col not in farm_df.columns:
            return None
        vals = pd.to_numeric(farm_df[col], errors="coerce").dropna()
        return float(vals.mean()) if not vals.empty else None

    lst_celsius     = col_mean("lst_celsius") or 28.0
    ndvi_mean       = col_mean("ndvi")        or 0.10
    bsi_mean        = col_mean("bsi")         or 0.10
    cloud_cover_pct = col_mean("cloud_cover") or 10.0
    ghi             = col_mean("ghi_kwh_m2_day")

    # 1. Temperature loss
    cell_temp = lst_celsius + 25.0
    temp_delta = max(0.0, cell_temp - 25.0)
    temperature_loss = min(abs(temp_coeff) * temp_delta / 100.0 * nameplate_eff, nameplate_eff * 0.05)

    # 2. Shading loss from NDVI
    shading_loss = max(0.0, min(2.0, (ndvi_mean - 0.15) * 6.5)) if ndvi_mean > 0.15 else 0.0
    if "tracking" in (axis_type or "").lower():
        shading_loss *= 0.6

    # 3. Soiling loss from BSI
    soiling_loss = min(3.0, bsi_mean * 8.0) if bsi_mean > 0.05 else 0.0

    # 4. Cloud/irradiance loss
    cloud_loss = (cloud_cover_pct / 100.0) * nameplate_eff * 0.15
    ghi_factor = (ghi / 5.5) if (ghi and ghi > 0) else 1.0
    ghi_loss   = max(0.0, 1.0 - ghi_factor) * nameplate_eff * 0.10
    cloud_irr_loss = min(cloud_loss + ghi_loss, nameplate_eff * 0.12)

    total_loss   = temperature_loss + shading_loss + soiling_loss + cloud_irr_loss
    ideal_eff    = max(nameplate_eff - total_loss, nameplate_eff * 0.70)
    ideal_output = capacity_dc_mw * (ideal_eff / nameplate_eff)
    perf_ratio   = ideal_output / capacity_dc_mw

    risk_flags = {
        "high_temperature_risk":   cell_temp > 50.0,
        "vegetation_shading_risk": ndvi_mean > 0.30,
        "dust_soiling_risk":       bsi_mean  > 0.15,
        "cloud_coverage_risk":     cloud_cover_pct > 30.0,
        "low_irradiance_risk":     (ghi is not None and ghi < 3.5),
    }

    result = {
        "nameplate_efficiency_pct": round(nameplate_eff, 2),
        "ideal_efficiency_pct":     round(ideal_eff, 2),
        "efficiency_loss_pct":      round(total_loss, 2),
        "loss_breakdown": {
            "temperature_loss_pct":      round(temperature_loss, 2),
            "shading_loss_pct":          round(shading_loss, 2),
            "soiling_loss_pct":          round(soiling_loss, 2),
            "cloud_irradiance_loss_pct": round(cloud_irr_loss, 2),
        },
        "ghi_kwh_m2_day":      round(ghi, 2) if ghi else None,
        "ideal_output_mw":     round(ideal_output, 3),
        "nameplate_output_mw": round(capacity_dc_mw, 3),
        "performance_ratio":   round(perf_ratio, 4),
    }
    return result, risk_flags


# ─── ENRICH DETECTIONS WITH SATELLITE DATA ───────────────────────────────────

FAULT_PENALTY = {
    "hotspot":           {"critical": 0.35, "moderate": 0.20, "minor": 0.08},
    "cracked cell":      {"critical": 0.40, "moderate": 0.25, "minor": 0.10},
    "cracked":           {"critical": 0.40, "moderate": 0.25, "minor": 0.10},
    "dust accumulation": {"critical": 0.15, "moderate": 0.08, "minor": 0.03},
    "dust":              {"critical": 0.15, "moderate": 0.08, "minor": 0.03},
    "shading":           {"critical": 0.30, "moderate": 0.18, "minor": 0.06},
    "delamination":      {"critical": 0.45, "moderate": 0.30, "minor": 0.12},
    "default":           {"critical": 0.30, "moderate": 0.18, "minor": 0.07},
}


def enrich_detections_with_satellite(
    detections: list,
    farm_df: pd.DataFrame,
    efficiency_result: dict,
    module_type: str,
    axis_type: str,
    capacity_dc_mw: float,
) -> list:
    """
    Core fusion function: for each CV-detected faulty panel, look up satellite
    conditions in the farm DataFrame and compute efficiency penalties and
    irradiance-adjusted daily energy losses.
    """
    if not detections:
        return detections

    # Use most-recent snapshot as "current conditions"
    if not farm_df.empty:
        if "date" in farm_df.columns:
            latest = farm_df.sort_values("date").iloc[-1].to_dict()
        else:
            latest = farm_df.iloc[-1].to_dict()
    else:
        latest = {}

    # Safely convert to Python scalars
    def safe_float(val):
        try:
            v = float(val)
            return None if (v != v) else v  # NaN check
        except Exception:
            return None

    sat_conditions = {
        "lst_celsius":     safe_float(latest.get("lst_celsius")),
        "ndvi":            safe_float(latest.get("ndvi")),
        "bsi":             safe_float(latest.get("bsi")),
        "cloud_cover_pct": safe_float(latest.get("cloud_cover")),
        "ghi_kwh_m2_day":  safe_float(latest.get("ghi_kwh_m2_day")),
        "dni_kwh_m2_day":  safe_float(latest.get("dni_kwh_m2_day")),
        "gti_kwh_m2_day":  safe_float(latest.get("gti_kwh_m2_day")),
    }

    ideal_eff_pct = efficiency_result.get("ideal_efficiency_pct", 18.0)
    ghi = sat_conditions.get("ghi_kwh_m2_day")

    enriched = []
    for det in detections:
        det = dict(det)

        fault_key = (det.get("fault_type") or "default").lower()
        severity  = (det.get("severity")   or "moderate").lower()
        penalty_map = FAULT_PENALTY.get(fault_key, FAULT_PENALTY["default"])
        fault_penalty_fraction = penalty_map.get(severity, 0.18)

        actual_eff_pct = ideal_eff_pct * (1 - fault_penalty_fraction)

        # Irradiance-adjusted daily energy loss per panel (~2 m² area at 400W STC)
        panel_area_m2 = 2.0
        if ghi and ghi > 0:
            ideal_daily_kwh  = ghi * panel_area_m2 * (ideal_eff_pct / 100)
            actual_daily_kwh = ghi * panel_area_m2 * (actual_eff_pct / 100)
            daily_loss_kwh   = round(ideal_daily_kwh - actual_daily_kwh, 3)
        else:
            daily_loss_kwh = None

        irradiance_note = (
            f"GHI {ghi:.1f} kWh/m²/day — this panel loses "
            f"{round(fault_penalty_fraction*100,1)}% efficiency from {fault_key}"
        ) if ghi else "Irradiance data unavailable"

        det["satellite_context"] = {
            **sat_conditions,
            "ideal_efficiency_pct":  round(ideal_eff_pct, 2),
            "actual_efficiency_pct": round(actual_eff_pct, 2),
            "fault_penalty_pct":     round(fault_penalty_fraction * 100, 1),
            "daily_energy_loss_kwh": daily_loss_kwh,
            "irradiance_note":       irradiance_note,
        }
        enriched.append(det)

    return enriched


# ─── GEE THUMBNAIL URL ────────────────────────────────────────────────────────

def generate_thumbnail_url(aoi, start_date: datetime, end_date: datetime) -> Optional[str]:
    """
    Generate a GEE Sentinel-2 true-color thumbnail URL for Leaflet overlay.
    """
    try:
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi)
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
            .sort("CLOUDY_PIXEL_PERCENTAGE")
            .first()
        )
        url = s2.getThumbURL({
            "bands": ["B4", "B3", "B2"],
            "min": 0,
            "max": 3000,
            "gamma": 1.4,
            "region": aoi,
            "dimensions": 512,
            "format": "png",
        })
        return url
    except Exception:
        return None


# ─── MOCK GEE RESPONSE ────────────────────────────────────────────────────────

def mock_gee_response(
    lat: float,
    lng: float,
    capacity_dc_mw: float,
    detections: list = None,
    module_type: str = "crystalline silicon",
    axis_type: str = "Fixed",
) -> dict:
    """
    Deterministic mock response when GEE credentials are unavailable.
    Uses lat/lng hash as seed so the same location always returns the same values.
    """
    seed = int(hashlib.md5(f"{lat:.2f}{lng:.2f}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    lst     = rng.uniform(22.0, 42.0)
    ndvi    = rng.uniform(0.05, 0.35)
    bsi     = rng.uniform(0.05, 0.30)
    cloud   = rng.uniform(5.0, 28.0)
    ghi     = rng.uniform(4.2, 6.5)
    dni     = ghi * rng.uniform(0.6, 0.85)
    gti     = ghi * rng.uniform(1.0, 1.15)

    mock_df = pd.DataFrame([{
        "date":            pd.Timestamp.now(),
        "ndvi":            round(ndvi, 3),
        "bsi":             round(bsi, 3),
        "cloud_cover":     round(cloud, 1),
        "lst_celsius":     round(lst, 1),
        "ghi_kwh_m2_day":  round(ghi, 2),
        "dni_kwh_m2_day":  round(dni, 2),
        "gti_kwh_m2_day":  round(gti, 2),
    }])

    eff_result, risk_flags = calculate_ideal_efficiency(
        module_type=module_type,
        axis_type=axis_type,
        farm_df=mock_df,
        capacity_dc_mw=capacity_dc_mw,
    )

    enriched = enrich_detections_with_satellite(
        detections=detections or [],
        farm_df=mock_df,
        efficiency_result=eff_result,
        module_type=module_type,
        axis_type=axis_type,
        capacity_dc_mw=capacity_dc_mw,
    )

    return {
        "thumbnail_url": None,  # no random image in mock mode
        "acquisition_date_range": "mock — GEE credentials not configured",
        "farm_summary": mock_df.to_dict(orient="records"),
        "environmental_conditions": {
            "lst_celsius":     round(lst, 1),
            "ndvi_mean":       round(ndvi, 3),
            "bsi_mean":        round(bsi, 3),
            "cloud_cover_pct": round(cloud, 1),
            "ghi_kwh_m2_day":  round(ghi, 2),
            "dni_kwh_m2_day":  round(dni, 2),
            "gti_kwh_m2_day":  round(gti, 2),
        },
        "efficiency": eff_result,
        "risk_flags": risk_flags,
        "enriched_detections": enriched,
        "dataset_dataframes": {},
        "mock": True,
    }


# ─── HAVERSINE DISTANCE ───────────────────────────────────────────────────────

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two lat/lng points in kilometres."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a  = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
