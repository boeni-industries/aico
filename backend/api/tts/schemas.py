"""
TTS API Schemas

Pydantic models for TTS API requests and responses.
"""

from pydantic import BaseModel, Field


class TtsSynthesizeRequest(BaseModel):
    """Request model for TTS synthesis"""
    text: str = Field(..., description="Text to synthesize", min_length=1, max_length=5000)
    language: str = Field(default="", description="Language code (empty = auto-detect)")
    speed: float = Field(default=1.0, description="Speech speed multiplier", ge=0.5, le=2.0)
    voice: str | None = Field(default=None, description="Optional voice identifier")
