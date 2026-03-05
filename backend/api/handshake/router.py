"""
Handshake API Router

Handles encrypted transport handshake requests for establishing secure sessions.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
import time
from aico.core.logging import get_logger
from backend.api.errors import raise_api_error

router = APIRouter()
logger = get_logger("backend.api.handshake")

# This will be injected during app initialization
transport_manager = None
key_manager = None

# Removed initialize_router - using proper FastAPI dependency injection


@router.post("")
@router.post("/")
async def handshake(request: Request):
    """Handle encrypted transport handshake requests"""
    logger.info("Handshake request received")
    
    try:
        # Parse request body
        request_data = await request.json()
        logger.info("Handshake request parsed", extra={
            "has_handshake_request": "handshake_request" in request_data
        })
        
        if "handshake_request" not in request_data:
            logger.warning("Invalid handshake request format - missing handshake_request field")
            raise_api_error(
                status_code=400,
                error_code="HANDSHAKE_INVALID_REQUEST",
                message="Invalid handshake request format",
            )
        
        handshake_request = request_data["handshake_request"]
        
        # Log handshake details
        logger.info("Processing handshake", extra={
            "component": handshake_request.get("component", "unknown"),
            "has_identity_key": "identity_key" in handshake_request,
            "has_public_key": "public_key" in handshake_request,
            "has_signature": "signature" in handshake_request
        })
        
        # Check if transport encryption is enabled
        from aico.core.config import ConfigurationManager
        config = ConfigurationManager()
        encryption_enabled = config.get("security.transport.encryption.enabled", default=False)
        
        if not encryption_enabled:
            # Transport encryption disabled - return bypass response
            logger.info("Transport encryption disabled - returning bypass handshake")
            response_data = {
                "status": "encryption_disabled",
                "message": "Transport encryption is disabled. Requests will be processed without encryption."
            }
            return JSONResponse(content=response_data)

        encryption_middleware = getattr(request.app.state, "encryption_middleware", None)
        if encryption_middleware is None:
            logger.warning("Transport encryption enabled but encryption middleware not available on app.state")
            raise_api_error(
                status_code=503,
                error_code="TRANSPORT_NOT_INITIALIZED",
                message="Transport encryption is enabled but not properly initialized. Please check backend configuration.",
            )

        return await encryption_middleware._handle_handshake(request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Handshake processing failed: {e}", extra={
            "error_type": type(e).__name__
        })
        raise_api_error(
            status_code=500,
            error_code="HANDSHAKE_PROCESSING_FAILED",
            message="Internal handshake processing error",
        )
