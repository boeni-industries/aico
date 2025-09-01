"""
FastAPI router for modelservice endpoints.
"""

import sys
import time
import httpx
import asyncio
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from typing import Dict, Any

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.version import get_modelservice_version
from .schemas import (
    HealthResponse, CompletionRequest, CompletionResponse, 
    ModelsResponse, ModelInfo, ModelStatus, ModelType,
    UsageStats, ErrorResponse
)
from .dependencies import get_modelservice_config

# Get version from VERSIONS file
__version__ = get_modelservice_version()

router = APIRouter(prefix="/api/v1", tags=["modelservice"])


async def check_system_health(config: dict) -> Dict[str, Any]:
    """
    Comprehensive system health check function.
    
    This function can be extended to check multiple health indicators:
    - Ollama connectivity and status
    - Model availability
    - Resource usage (memory, disk)
    - Service dependencies
    - Performance metrics
    
    Returns:
        Dict containing health status and detailed information
    """
    health_data = {
        "status": "healthy",
        "checks": {},
        "details": {},
        "errors": [],
        "suggestions": []
    }
    
    # Check Ollama connectivity
    ollama_url = config.get("ollama_url", "http://localhost:11434")
    ollama_healthy = await _check_ollama_health(ollama_url)
    
    health_data["checks"]["ollama"] = ollama_healthy
    health_data["details"]["ollama_url"] = ollama_url
    
    # Determine overall status and add actionable error information
    if not ollama_healthy["healthy"]:
        if not ollama_healthy["reachable"]:
            health_data["status"] = "unhealthy"
            if ollama_healthy.get("error") == "timeout":
                health_data["errors"].append(f"Ollama service at {ollama_url} is not responding (timeout)")
                health_data["suggestions"].extend([
                    "Check if Ollama is installed and running",
                    f"Verify Ollama is accessible at {ollama_url}",
                    "Try starting Ollama with: ollama serve"
                ])
            else:
                error_msg = ollama_healthy.get("error", "connection failed")
                health_data["errors"].append(f"Cannot connect to Ollama service: {error_msg}")
                health_data["suggestions"].extend([
                    "Ensure Ollama is installed and running",
                    f"Check if the configured URL {ollama_url} is correct",
                    "Verify network connectivity and firewall settings",
                    "Try starting Ollama with: ollama serve"
                ])
        else:
            health_data["status"] = "degraded"
            status_code = ollama_healthy.get("status_code", "unknown")
            health_data["errors"].append(f"Ollama service returned HTTP {status_code}")
            health_data["suggestions"].extend([
                "Ollama is running but not responding correctly",
                "Check Ollama service logs for errors",
                "Try restarting Ollama service",
                f"Verify API endpoint {ollama_url}/api/tags is accessible"
            ])
    
    # Future health checks can be added here:
    # - Model availability check
    # - Resource usage monitoring
    # - Dependency service checks
    
    return health_data


async def _check_ollama_health(ollama_url: str) -> Dict[str, Any]:
    """Check Ollama service health."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            return {
                "healthy": response.status_code == 200,
                "reachable": True,
                "status_code": response.status_code,
                "response_time_ms": None  # Could add timing here
            }
    except httpx.TimeoutException:
        return {
            "healthy": False,
            "reachable": False,
            "error": "timeout",
            "response_time_ms": None
        }
    except httpx.RequestError as e:
        return {
            "healthy": False,
            "reachable": False,
            "error": str(e),
            "response_time_ms": None
        }


@router.get("/health", response_model=HealthResponse)
async def health_check(config: dict = Depends(get_modelservice_config)):
    """Health check endpoint for modelservice."""
    health_data = await check_system_health(config)
    
    return HealthResponse(
        status=health_data["status"],
        service="modelservice",
        version=__version__,
        timestamp=datetime.utcnow().isoformat(),
        checks=health_data.get("checks"),
        errors=health_data.get("errors") if health_data.get("errors") else None,
        suggestions=health_data.get("suggestions") if health_data.get("suggestions") else None
    )


@router.post("/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    config: dict = Depends(get_modelservice_config)
):
    """Generate text completion using Ollama."""
    ollama_url = config.get("ollama_url", "http://localhost:11434")
    
    # Prepare Ollama request payload
    ollama_payload = {
        "model": request.model,
        "prompt": request.prompt,
        "stream": False,  # Non-streaming for now
        "options": {}
    }
    
    # Map parameters to Ollama options
    if request.parameters:
        params = request.parameters
        if params.max_tokens is not None:
            ollama_payload["options"]["num_predict"] = params.max_tokens
        if params.temperature is not None:
            ollama_payload["options"]["temperature"] = params.temperature
        if params.top_p is not None:
            ollama_payload["options"]["top_p"] = params.top_p
        if params.top_k is not None:
            ollama_payload["options"]["top_k"] = params.top_k
        if params.repeat_penalty is not None:
            ollama_payload["options"]["repeat_penalty"] = params.repeat_penalty
        if params.stop is not None:
            ollama_payload["options"]["stop"] = params.stop
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json=ollama_payload
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Ollama error: {response.text}"
                )
            
            ollama_response = response.json()
            
            # Extract completion text
            completion_text = ollama_response.get("response", "")
            
            # Calculate token usage (approximate)
            prompt_tokens = len(request.prompt.split())
            completion_tokens = len(completion_text.split())
            
            usage = UsageStats(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )
            
            return CompletionResponse(
                completion=completion_text,
                model=request.model,
                usage=usage,
                finish_reason="stop",
                created=int(time.time())
            )
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to Ollama: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/models", response_model=ModelsResponse)
async def list_models(config: dict = Depends(get_modelservice_config)):
    """List available models from Ollama."""
    ollama_url = config.get("ollama_url", "http://localhost:11434")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Ollama error: {response.text}"
                )
            
            ollama_response = response.json()
            models = []
            
            for model_data in ollama_response.get("models", []):
                model_info = ModelInfo(
                    name=model_data.get("name", ""),
                    description=model_data.get("details", {}).get("family", ""),
                    status=ModelStatus.LOADED,
                    type=ModelType.LLM,
                    size=_format_size(model_data.get("size", 0)),
                    modified_at=model_data.get("modified_at", ""),
                    details=model_data.get("details", {})
                )
                models.append(model_info)
            
            return ModelsResponse(models=models)
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to Ollama: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


def _format_size(size_bytes: int) -> str:
    """Format size in bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"