from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import upload, detection, gee, synthetic, analysis, drone_analyze, drone_pipeline
import os

app = FastAPI(title="SolarSentinel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure sample data exists
os.makedirs("../sample_data", exist_ok=True)
app.mount("/sample_data", StaticFiles(directory="../sample_data"), name="sample_data")
app.mount("/tmp/solarsentinel", StaticFiles(directory="/tmp/solarsentinel"), name="tmp_data")

app.include_router(upload.router, prefix="/api")
app.include_router(detection.router, prefix="/api")
app.include_router(gee.router, prefix="/api")
app.include_router(synthetic.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(drone_analyze.router, prefix="/api")
app.include_router(drone_pipeline.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "SolarSentinel API is running"}
