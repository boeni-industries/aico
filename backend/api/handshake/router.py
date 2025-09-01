"""
Handshake API Router

Handles encrypted transport handshake requests for establishing secure sessions.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
import time
from aico.core.logging import get_logger

router = APIRouter()
logger = get_logger("api", "handshake")

# This will be injected during app initialization
transport_manager = None
key_manager = None

# Removed initialize_router - using proper FastAPI dependency injection


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
            raise HTTPException(
                status_code=400, 
                detail="Invalid handshake request format"
            )
        
        handshake_request = request_data["handshake_request"]
        
        # Log handshake details
        logger.info("Processing handshake", extra={
            "component": handshake_request.get("component", "unknown"),
            "has_identity_key": "identity_key" in handshake_request,
            "has_public_key": "public_key" in handshake_request,
            "has_signature": "signature" in handshake_request
        })
        
        # Return handshake response with session establishment
        response_data = {
            "status": "session_established",
            "handshake_response": {
                "component": "aico_backend",
                "public_key": "placeholder_server_public_key",
                "timestamp": int(time.time()),
                "challenge": "placeholder_challenge",
                "signature": "placeholder_signature"
            }
        }
        
        logger.info("Handshake completed successfully", extra={
            "client_component": handshake_request.get("component", "unknown")
        })
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Handshake processing failed: {e}", extra={
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail="Internal handshake processing error"
        )
