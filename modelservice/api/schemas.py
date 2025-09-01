"""
Pydantic schemas for modelservice API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    service: str
    version: Optional[str] = None
    timestamp: str
    checks: Optional[Dict[str, Any]] = Field(default=None)
    errors: Optional[List[str]] = Field(default=None)
    suggestions: Optional[List[str]] = Field(default=None)


class ModelStatus(str, Enum):
    """Model status enumeration."""
    LOADED = "loaded"
    AVAILABLE = "available"
    LOADING = "loading"
    ERROR = "error"


class ModelType(str, Enum):
    """Model type enumeration."""
    LLM = "llm"
    VISION = "vision"
    EMBEDDING = "embedding"


class CompletionParameters(BaseModel):
    """Parameters for text completion requests."""
    max_tokens: Optional[int] = Field(default=128, ge=1, le=4096)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=0.9, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=40, ge=1, le=100)
    repeat_penalty: Optional[float] = Field(default=1.1, ge=0.0, le=2.0)
    stop: Optional[List[str]] = Field(default=None, max_items=4)
    stream: Optional[bool] = Field(default=False)


class CompletionRequest(BaseModel):
    """Request schema for text completion."""
    model: str = Field(..., min_length=1, max_length=100)
    prompt: str = Field(..., min_length=1, max_length=32768)
    parameters: Optional[CompletionParameters] = Field(default_factory=CompletionParameters)


class UsageStats(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    total_tokens: Optional[int] = Field(default=None, ge=0)

    def __init__(self, **data):
        super().__init__(**data)
        if self.total_tokens is None:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


class CompletionResponse(BaseModel):
    """Response schema for text completion."""
    completion: str
    model: str
    usage: UsageStats
    finish_reason: Optional[str] = Field(default="stop")
    created: Optional[int] = Field(default=None)


class ModelInfo(BaseModel):
    """Model information schema."""
    name: str = Field(..., min_length=1)
    description: Optional[str] = Field(default="")
    status: ModelStatus
    type: ModelType = Field(default=ModelType.LLM)
    size: Optional[str] = Field(default=None)
    modified_at: Optional[str] = Field(default=None)
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ModelsResponse(BaseModel):
    """Response schema for models list."""
    models: List[ModelInfo]


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    message: str
    code: Optional[int] = Field(default=None)