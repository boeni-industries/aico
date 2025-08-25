"""
AICO Echo API Router

Provides simple echo endpoints for testing encrypted communication.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import time

from aico.core.logging import get_logger

router = APIRouter()
logger = get_logger("api", "echo_router")


class EchoRequest(BaseModel):
    """Echo request model"""
    message: str
    test_data: Dict[str, Any] = {}


class EchoResponse(BaseModel):
    """Echo response model"""
    echo: str
    received_data: Dict[str, Any]
    server_timestamp: int
    status: str = "success"


@router.post("/", response_model=EchoResponse)
async def echo_message(request: EchoRequest):
    """
    Echo back the received message with server timestamp.
    Useful for testing encrypted communication.
    """
    logger.info("Echo request received", extra={
        "message": request.message,
        "test_data_keys": list(request.test_data.keys()) if request.test_data else [],
        "endpoint": "/echo"
    })
    
    response = EchoResponse(
        echo=request.message,
        received_data=request.test_data,
        server_timestamp=int(time.time()),
        status="success"
    )
    
    logger.info("Echo response sent", extra={
        "message": request.message,
        "server_timestamp": response.server_timestamp,
        "status": response.status
    })
    
    return response


@router.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"message": "pong", "timestamp": int(time.time())}
