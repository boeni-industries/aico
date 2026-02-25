"""
NATS client helpers for gateway→core communication.

Provides request/reply helpers for gateway endpoints to communicate with core services.
"""

import json
from typing import Any, Dict, Optional
from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient, MessageBusTimeoutError, MessageBusError
from google.protobuf.struct_pb2 import Struct
from google.protobuf.any_pb2 import Any as ProtoAny

logger = get_logger("backend.api_gateway.nats_client")


class GatewayNATSClient:
    """Helper for gateway to make NATS requests to core services"""
    
    def __init__(self, message_bus_client: MessageBusClient):
        self.bus = message_bus_client
        self.logger = logger
    
    async def request_scheduler_status(self) -> Dict[str, Any]:
        """Request scheduler status from core via NATS"""
        try:
            # Create empty request (no params needed)
            request_struct = Struct()
            
            # Send request via NATS
            reply_msg = await self.bus._nats.request(
                "scheduler.status",
                b"{}",
                timeout=5.0
            )
            
            # Parse JSON response directly from bytes
            response_data = json.loads(reply_msg.data.decode('utf-8'))
            
            if response_data.get("error"):
                raise Exception(f"{response_data['error']}: {response_data.get('message', 'Unknown error')}")
            
            return response_data
            
        except MessageBusTimeoutError:
            raise Exception("SCHEDULER_NOT_AVAILABLE: Request timed out")
        except MessageBusError as e:
            raise Exception(f"SCHEDULER_NOT_AVAILABLE: {str(e)}")
    
    async def request_scheduler_tasks(self, enabled_only: bool = False) -> Dict[str, Any]:
        """Request scheduler tasks list from core via NATS"""
        try:
            # Create request with params
            request_struct = Struct()
            request_struct.update({
                "enabled_only": enabled_only
            })
            
            # Send request via NATS
            request_json = json.dumps({"enabled_only": enabled_only})
            reply_msg = await self.bus._nats.request(
                "scheduler.tasks",
                request_json.encode('utf-8'),
                timeout=5.0
            )
            
            # Parse JSON response directly from bytes
            response_data = json.loads(reply_msg.data.decode('utf-8'))
            
            if response_data.get("error"):
                raise Exception(f"{response_data['error']}: {response_data.get('message', 'Unknown error')}")
            
            return response_data
            
        except MessageBusTimeoutError:
            raise Exception("SCHEDULER_NOT_AVAILABLE: Request timed out")
        except MessageBusError as e:
            raise Exception(f"SCHEDULER_NOT_AVAILABLE: {str(e)}")
    
    async def request_emotion_history(self, limit: int = 10, hours: int = 24) -> Dict[str, Any]:
        """Request emotion history from core via NATS"""
        try:
            # Create request with params
            request_struct = Struct()
            request_struct.update({
                "limit": limit,
                "hours": hours
            })
            
            # Send request via NATS
            request_json = json.dumps({"limit": limit, "hours": hours})
            reply_msg = await self.bus._nats.request(
                "emotion.history",
                request_json.encode('utf-8'),
                timeout=5.0
            )
            
            # Parse JSON response directly from bytes
            response_data = json.loads(reply_msg.data.decode('utf-8'))
            
            if response_data.get("error"):
                raise Exception(f"{response_data['error']}: {response_data.get('message', 'Unknown error')}")
            
            return response_data
            
        except MessageBusTimeoutError:
            raise Exception("EMOTION_ENGINE_UNAVAILABLE: Request timed out")
        except MessageBusError as e:
            raise Exception(f"EMOTION_ENGINE_UNAVAILABLE: {str(e)}")
    
    def _extract_response_data(self, reply_envelope) -> Dict[str, Any]:
        """Extract JSON data from protobuf response envelope"""
        try:
            # Extract JSON from metadata attributes
            json_response = reply_envelope.metadata.attributes.get("json_response", "{}")
            return json.loads(json_response)
            
        except Exception as e:
            self.logger.error(f"Failed to extract response data: {e}")
            return {"error": "RESPONSE_PARSE_ERROR", "message": str(e)}


# Singleton instance (will be initialized in gateway lifecycle)
_gateway_nats_client: Optional[GatewayNATSClient] = None


def get_gateway_nats_client() -> GatewayNATSClient:
    """Get the gateway NATS client singleton"""
    global _gateway_nats_client
    if _gateway_nats_client is None:
        raise RuntimeError("Gateway NATS client not initialized")
    return _gateway_nats_client


def initialize_gateway_nats_client(message_bus_client: MessageBusClient):
    """Initialize the gateway NATS client singleton"""
    global _gateway_nats_client
    _gateway_nats_client = GatewayNATSClient(message_bus_client)
    logger.info("Gateway NATS client initialized")
