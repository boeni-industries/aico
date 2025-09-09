"""
AICO Echo API Router

Provides simple echo endpoints for testing encrypted communication.
"""

from fastapi import APIRouter, Request, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any
import time

from aico.core.logging import get_logger, is_cli_context

# Initialize logger at the module level
logger = get_logger("aico.api.echo", "router")

router = APIRouter()


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


@router.post("/", response_model=EchoResponse, status_code=status.HTTP_200_OK)
@router.post("", response_model=EchoResponse, status_code=status.HTTP_200_OK)
async def echo_message(request: EchoRequest, raw_request: Request, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> EchoResponse:
    """
    Echo back the received message with server timestamp.
    Useful for testing encrypted communication.
    """
    import uuid
    trace_id = str(uuid.uuid4())[:8]
    #print(f"[ECHO TRACE {trace_id}] STEP 1: /echo called with message='{request.message}'")

    logger.info("[ECHO TRACE] Echo request received", extra={
        "message": request.message,
        "test_data_keys": list(request.test_data.keys()) if request.test_data else [],
        "endpoint": "/api/v1/echo",
        "trace_id": trace_id,
        "test_message": "THIS_IS_A_TEST_LOG_FOR_TRACING"
    })
    
    response = EchoResponse(
        echo=request.message,
        received_data=request.test_data,
        server_timestamp=int(time.time()),
        status="success"
    )
    
    logger.info("[ECHO TRACE] Echo response sent", extra={
        "message": request.message,
        "server_timestamp": response.server_timestamp,
        "status": response.status,
        "trace_id": trace_id,
        "test_message": "THIS_IS_A_TEST_LOG_FOR_TRACING"
    })
    #print(f"[ECHO TRACE {trace_id}] STEP 2: Response prepared and logger.info() called")
    
    return response


@router.get("/ping")
async def ping(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Simple ping endpoint with comprehensive tracing"""
    import uuid
    trace_id = str(uuid.uuid4())[:8]
    
    #print(f"[ECHO TRACE {trace_id}] STEP 1: Echo ping endpoint called")
    
    logger.info(f"[ECHO TRACE {trace_id}] Echo ping endpoint called - testing full logging chain", extra={
        "endpoint": "/echo/ping",
        "trace_id": trace_id,
        "test_message": "THIS_IS_A_TEST_LOG_FOR_TRACING"
    })
    
    #print(f"[ECHO TRACE {trace_id}] STEP 2: Logger.info() call completed")
    
    response = {"message": "pong", "timestamp": int(time.time()), "trace_id": trace_id}
    
    #print(f"[ECHO TRACE {trace_id}] STEP 3: Returning response: {response}")
    
    return response
