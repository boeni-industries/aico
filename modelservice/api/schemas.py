"""
Pydantic schemas for modelservice API endpoints.
"""

from pydantic import BaseModel
from typing import Optional


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    service: str
    version: Optional[str] = None
    timestamp: str


# TODO: Add additional schemas for modelservice endpoints as needed