"""
FastAPI router for modelservice endpoints.
"""

import sys
from pathlib import Path
from fastapi import APIRouter, Depends
from datetime import datetime

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.version import get_modelservice_version
from .schemas import HealthResponse
from .dependencies import get_modelservice_config

# Get version from VERSIONS file
__version__ = get_modelservice_version()

router = APIRouter(prefix="/api/v1", tags=["modelservice"])


@router.get("/health", response_model=HealthResponse)
async def health_check(config: dict = Depends(get_modelservice_config)):
    """Health check endpoint for modelservice."""
    return HealthResponse(
        status="healthy",
        service="modelservice",
        version=__version__,
        timestamp=datetime.utcnow().isoformat()
    )


# TODO: Add additional endpoints as needed