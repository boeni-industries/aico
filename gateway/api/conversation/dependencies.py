from __future__ import annotations

from fastapi import HTTPException, Request

from aico.core.bus import MessageBusClient
from aico.common.errors import raise_api_error

logger = None
_message_bus_client_cache: MessageBusClient | None = None


async def get_message_bus_client(request: Request) -> MessageBusClient:
    global _message_bus_client_cache
    try:
        if _message_bus_client_cache is not None:
            return _message_bus_client_cache
        client = MessageBusClient("gateway_conversation_api")
        await client.connect()
        _message_bus_client_cache = client
        return client
    except HTTPException:
        raise
    except Exception as exc:
        raise_api_error(
            status_code=500,
            error_code="MESSAGE_BUS_UNAVAILABLE",
            message="Message bus service unavailable",
            details={"error": str(exc)},
        )
