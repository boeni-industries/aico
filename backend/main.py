from fastapi import FastAPI
import sys
from pathlib import Path

# Add shared module to path
shared_path = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.logging import get_logger

__version__ = "0.0.1"

# Initialize logger for backend
logger = get_logger("backend.main")

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Log server startup"""
    logger.info("AICO backend server starting up", extra={
        "version": __version__,
        "component": "fastapi_server"
    })

@app.on_event("shutdown") 
async def shutdown_event():
    """Log server shutdown"""
    logger.info("AICO backend server shutting down", extra={
        "version": __version__,
        "component": "fastapi_server"
    })

@app.get("/")
def read_root():
    logger.debug("Health check endpoint accessed")
    return {"AICO backend": f"running (version {__version__})"}
