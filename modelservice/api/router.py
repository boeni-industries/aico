"""
FastAPI router for modelservice endpoints.
"""

import time
import httpx
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from typing import Dict, Any

from aico.core.version import get_modelservice_version
from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from aico.security.exceptions import EncryptionError
from aico.security.transport import TransportIdentityManager
from .schemas import (
    HealthResponse, CompletionRequest, CompletionResponse, 
    ModelsResponse, ModelInfo, ModelStatus, ModelType,
    UsageStats, ErrorResponse
)
from .dependencies import get_modelservice_config, get_identity_manager
from .logging_client import get_logging_client, APIGatewayLoggingClient
from .service_logger import get_service_logger, ServiceLogger

# Get version from VERSIONS file
__version__ = get_modelservice_version()

router = APIRouter(prefix="/api/v1", tags=["modelservice"])

# Logger for modelservice router - uses "modelservice" subsystem log level from config
logger = get_logger("modelservice", "api_router")


@router.post("/handshake")
async def handshake(request_data: Dict[str, Any], identity_manager: TransportIdentityManager = Depends(get_identity_manager)):
    """
    Handshake endpoint for establishing encrypted communication between CLI and modelservice.
    
    This endpoint enables secure CLI-to-modelservice communication by:
    1. Exchanging Ed25519 identity keys and X25519 ephemeral keys
    2. Establishing XChaCha20-Poly1305 encrypted channels
    3. Creating session-based encryption for all subsequent API calls
    4. Following AICO's transport security pattern (same as API Gateway)
    
    The CLI initiates handshake before making other modelservice API calls to ensure
    all communication is encrypted end-to-end, maintaining AICO's privacy-first principles.
    """
    try:
        client_id, response_data, channel = identity_manager.process_handshake_and_create_channel(
            request_data, "modelservice"
        )
        
        logger.info(
            f"Successful handshake with client {client_id}",
            extra={"topic": AICOTopics.LOGS_ENTRY}
        )
        
        return response_data
        
    except EncryptionError as e:
        error_msg = f"Handshake failed: {str(e)}"
        logger.error(
            error_msg,
            extra={"topic": AICOTopics.LOGS_ENTRY}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        error_msg = f"Internal handshake error: {str(e)}"
        logger.error(
            error_msg,
            extra={"topic": AICOTopics.LOGS_ENTRY}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


async def check_system_health(config: dict, logging_client: APIGatewayLoggingClient) -> Dict[str, Any]:
    """
    Comprehensive system health check function.
    
    This function can be extended to check multiple health indicators:
    - Ollama connectivity and status
    - API Gateway connectivity and logging
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
    
    # Check API Gateway connectivity
    api_gateway_health = await logging_client.check_api_gateway_health()
    health_data["checks"]["api_gateway"] = api_gateway_health
    
    if api_gateway_health["status"] != "healthy":
        health_data["status"] = "unhealthy"
        if not api_gateway_health["reachable"]:
            health_data["errors"].append("API Gateway is not reachable")
            health_data["suggestions"].extend([
                "Check if API Gateway (backend) is running",
                "Verify API Gateway URL configuration",
                "Check network connectivity to API Gateway"
            ])
        else:
            health_data["errors"].append(f"API Gateway returned error: {api_gateway_health.get('error', 'unknown')}")
            health_data["suggestions"].extend([
                "API Gateway is running but not responding correctly",
                "Check API Gateway service logs for errors",
                "Verify service authentication configuration"
            ])
    
    # Check Ollama connectivity
    ollama_health = await _check_ollama_health(config.get("ollama_url", "http://localhost:11434"))
    health_data["checks"]["ollama"] = ollama_health
    
    if not ollama_health["healthy"]:
        health_data["status"] = "unhealthy"
        if not ollama_health["reachable"]:
            health_data["errors"].append("Ollama service is not reachable")
            health_data["suggestions"].extend([
                "Check if Ollama is running",
                "Verify Ollama URL configuration",
                "Check network connectivity to Ollama service"
            ])
        else:
            status_code = ollama_health.get("status_code")
            health_data["errors"].append(f"Ollama service returned HTTP {status_code}")
            health_data["suggestions"].extend([
                "Ollama is running but not responding correctly",
                "Check Ollama service logs for errors",
                "Try restarting Ollama service",
                f"Verify API endpoint {config.get('ollama_url', 'http://localhost:11434')}/api/tags is accessible"
            ])
    
    # Future health checks can be added here:
    # - Model availability check
    # - Resource usage monitoring
    # - Dependency service checks
    
    return health_data


async def _check_ollama_health(ollama_url: str) -> Dict[str, Any]:
    """Check Ollama service health."""
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
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
async def health_check(
    config: dict = Depends(get_modelservice_config),
    identity_manager: TransportIdentityManager = Depends(get_identity_manager),
    logging_client: APIGatewayLoggingClient = Depends(get_logging_client)
) -> HealthResponse:
    """Health check endpoint for modelservice."""
    health_data = await check_system_health(config, logging_client)
    
    # Log health check results
    if health_data["status"] == "healthy":
        logger.info(
            "Health check passed - all systems operational",
            extra={"topic": AICOTopics.SYSTEM_HEALTH_CHECK}
        )
    else:
        logger.warning(
            f"Health check failed - status: {health_data['status']}, errors: {health_data.get('errors', [])}",
            extra={"topic": AICOTopics.SYSTEM_HEALTH_CHECK}
        )
    
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
    config: dict = Depends(get_modelservice_config),
    logging_client: APIGatewayLoggingClient = Depends(get_logging_client)
) -> CompletionResponse:
    """Generate text completion using Ollama."""
    ollama_url = config.get("ollama_url", "http://localhost:11434")
    
    # Log completion request
    service_logger = get_service_logger(logging_client)
    await service_logger._log_async("INFO", f"Completion request received for model: {request.model}", 
                                   extra={"model": request.model, "prompt_length": len(request.prompt)})
    
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


# Ollama-specific endpoints for CLI integration
@router.get("/ollama/status")
@router.post("/ollama/status")
async def ollama_status():
    """Get Ollama status and system information."""
    from fastapi import Request
    from starlette.requests import Request as StarletteRequest
    
    # Access the ollama_manager from app state
    try:
        # This will be set by the lifespan function in main.py
        from fastapi import Request
        import inspect
        
        # Get the current request context to access app state
        frame = inspect.currentframe()
        while frame:
            if 'request' in frame.f_locals and hasattr(frame.f_locals['request'], 'app'):
                request = frame.f_locals['request']
                break
            frame = frame.f_back
        
        if frame and hasattr(request.app.state, 'ollama_manager'):
            ollama_manager = request.app.state.ollama_manager
            status_data = await ollama_manager.get_status()
            return status_data
        else:
            # Fallback: create new manager instance
            from ..core.ollama_manager import OllamaManager
            ollama_manager = OllamaManager()
            status_data = await ollama_manager.get_status()
            return status_data
            
    except Exception as e:
        return {
            "installed": False,
            "running": False,
            "healthy": False,
            "error": str(e)
        }


@router.post("/ollama/install")
async def ollama_install(force: bool = False):
    """Install or update Ollama binary."""
    try:
        from ..core.ollama_manager import OllamaManager
        ollama_manager = OllamaManager()
        
        success = await ollama_manager.ensure_installed(force_update=force)
        
        if success:
            status = await ollama_manager.get_status()
            return {
                "success": True,
                "version": status.get("version"),
                "binary_path": status.get("binary_path")
            }
        else:
            return {
                "success": False,
                "error": "Installation failed"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/ollama/serve")
async def ollama_serve():
    """Start Ollama server directly."""
    try:
        from ..core.ollama_manager import OllamaManager
        ollama_manager = OllamaManager()
        
        success = await ollama_manager.start_ollama()
        
        return {
            "success": success,
            "error": None if success else "Failed to start Ollama server"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/ollama/logs")
async def ollama_logs(lines: int = 50):
    """Get Ollama logs."""
    try:
        from ..core.ollama_manager import OllamaManager
        ollama_manager = OllamaManager()
        
        logs = await ollama_manager.get_logs(lines)
        
        return {
            "logs": logs
        }
        
    except Exception as e:
        return {
            "logs": [],
            "error": str(e)
        }


@router.get("/ollama/models")
@router.post("/ollama/models")
async def ollama_models():
    """List Ollama models."""
    try:
        from ..core.ollama_manager import OllamaManager
        ollama_manager = OllamaManager()
        
        models = await ollama_manager.list_models()
        
        return models
        
    except Exception as e:
        return {
            "models": [],
            "error": str(e)
        }


@router.get("/ollama/models/running")
@router.post("/ollama/models/running")
async def ollama_models_running():
    """List currently running models."""
    try:
        from ..core.ollama_manager import OllamaManager
        ollama_manager = OllamaManager()
        
        # For now, return the same as list_models
        # In the future, this could query Ollama's running processes
        models = await ollama_manager.list_models()
        
        return models
        
    except Exception as e:
        return {
            "models": [],
            "error": str(e)
        }


@router.post("/ollama/models/pull")
async def ollama_pull_model(request: Dict[str, str]):
    """Pull/download a model."""
    try:
        model_name = request.get("name")
        if not model_name:
            return {
                "success": False,
                "error": "Model name is required"
            }
        
        from ..core.ollama_manager import OllamaManager
        ollama_manager = OllamaManager()
        
        success = await ollama_manager.pull_model(model_name)
        
        return {
            "success": success,
            "error": None if success else f"Failed to pull model {model_name}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/ollama/models/{model_name}")
async def ollama_remove_model(model_name: str):
    """Remove a model."""
    try:
        from ..core.ollama_manager import OllamaManager
        ollama_manager = OllamaManager()
        
        success = await ollama_manager.remove_model(model_name)
        
        return {
            "success": success,
            "error": None if success else f"Failed to remove model {model_name}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/ollama/shutdown")
async def ollama_shutdown():
    """Stop Ollama server daemon."""
    try:
        from ..core.ollama_manager import OllamaManager
        ollama_manager = OllamaManager()
        
        success = await ollama_manager.stop_ollama()
        
        return {
            "success": success,
            "error": None if success else "Failed to stop Ollama server"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/ollama/models/start")
async def ollama_start_model(request: Dict[str, str]):
    """Start/run a specific model."""
    try:
        model_name = request.get("name")
        if not model_name:
            return {
                "success": False,
                "error": "Model name is required"
            }
        
        from ..core.ollama_manager import OllamaManager
        ollama_manager = OllamaManager()
        
        success = await ollama_manager.start_model(model_name)
        
        return {
            "success": success,
            "error": None if success else f"Failed to start model {model_name}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/ollama/models/stop")
async def ollama_stop_model(request: Dict[str, str]):
    """Stop a specific model."""
    try:
        model_name = request.get("name")
        if not model_name:
            return {
                "success": False,
                "error": "Model name is required"
            }
        
        from ..core.ollama_manager import OllamaManager
        ollama_manager = OllamaManager()
        
        success = await ollama_manager.stop_model(model_name)
        
        return {
            "success": success,
            "error": None if success else f"Failed to stop model {model_name}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }