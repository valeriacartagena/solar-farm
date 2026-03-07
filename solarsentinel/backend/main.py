from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()  # load .env before anything else reads os.getenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import upload, detection, gee, synthetic, analysis
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize GEE once at server startup."""
    try:
        from routers.gee import init_gee
        ok = init_gee()
        logger.info(f"GEE init at startup: {'success' if ok else 'using mock mode'}")
    except Exception as e:
        logger.warning(f"GEE init skipped at startup: {e}")
    yield


app = FastAPI(title="SolarSentinel API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure required directories exist before mounting
os.makedirs("../sample_data", exist_ok=True)
os.makedirs("/tmp/solarsentinel", exist_ok=True)
app.mount("/sample_data", StaticFiles(directory="../sample_data"), name="sample_data")
app.mount("/tmp/solarsentinel", StaticFiles(directory="/tmp/solarsentinel"), name="tmp_data")

app.include_router(upload.router,    prefix="/api")
app.include_router(detection.router, prefix="/api")
app.include_router(gee.router,       prefix="/api")
app.include_router(synthetic.router, prefix="/api")
app.include_router(analysis.router,  prefix="/api")


@app.get("/")
def read_root():
    return {"message": "SolarSentinel API is running"}
