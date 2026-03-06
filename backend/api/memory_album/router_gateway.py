"""
Gateway Memory Album endpoints - proxy to core via NATS.

Gateway is HTTP termination only. All memory album business logic lives in core.
These endpoints validate auth and proxy requests to core via NATS request/reply.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.api.system.dependencies import get_current_user
from backend.api.errors import raise_api_error

router = APIRouter(prefix="/memory-album", tags=["memory-album"])


class MemoryAlbumResponse(BaseModel):
    """Memory album list response."""
    memories: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


@router.get("", response_model=MemoryAlbumResponse)
async def get_memory_album(
    category: Optional[str] = Query(None),
    favorites_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _auth: dict = Depends(get_current_user)
):
    """
    Get user's memory album entries.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_memory_album(
            user_uuid=_auth["user_uuid"],
            category=category,
            favorites_only=favorites_only,
            limit=limit,
            offset=offset
        )
        
        return MemoryAlbumResponse(**data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="MEMORY_ALBUM_FAILED",
            message=f"Failed to retrieve memory album: {str(e)}",
        )
