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
from opentelemetry import trace

logger = get_logger("backend.api_gateway.nats_client")
tracer = trace.get_tracer(__name__)


class GatewayNATSClient:
    """Helper for gateway to make NATS requests to core services"""
    
    def __init__(self, message_bus_client: MessageBusClient):
        self.bus = message_bus_client
        self.logger = logger
    
    async def _nats_request_with_trace(
        self, 
        subject: str, 
        payload: bytes, 
        timeout: float = 5.0,
        operation_name: str = None
    ) -> Dict[str, Any]:
        """Make NATS request with OpenTelemetry tracing"""
        span_name = operation_name or f"nats.request.{subject}"
        
        with tracer.start_as_current_span(
            span_name,
            kind=trace.SpanKind.CLIENT,
            attributes={
                "messaging.system": "nats",
                "messaging.destination": subject,
                "messaging.operation": "request",
                "messaging.message_payload_size_bytes": len(payload),
            }
        ) as span:
            try:
                reply_msg = await self.bus._nats.request(subject, payload, timeout=timeout)
                response_data = json.loads(reply_msg.data.decode('utf-8'))
                
                if response_data.get("error"):
                    span.set_status(trace.Status(trace.StatusCode.ERROR, response_data.get('message', 'Unknown error')))
                    span.set_attribute("error.type", response_data.get("error"))
                    raise Exception(f"{response_data['error']}: {response_data.get('message', 'Unknown error')}")
                
                span.set_status(trace.Status(trace.StatusCode.OK))
                span.set_attribute("messaging.response_size_bytes", len(reply_msg.data))
                return response_data
                
            except MessageBusTimeoutError as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Request timed out"))
                span.record_exception(e)
                raise Exception(f"{subject.upper()}_TIMEOUT: Request timed out")
            except MessageBusError as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise Exception(f"{subject.upper()}_FAILED: {str(e)}")
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    async def request_scheduler_status(self) -> Dict[str, Any]:
        """Request scheduler status from core via NATS"""
        return await self._nats_request_with_trace("scheduler.status", b"{}")
    
    async def request_scheduler_tasks(self, enabled_only: bool = False) -> Dict[str, Any]:
        """Request scheduler tasks list from core via NATS"""
        payload = json.dumps({"enabled_only": enabled_only}).encode('utf-8')
        return await self._nats_request_with_trace("scheduler.tasks", payload)
    
    async def request_current_emotion(self) -> Dict[str, Any]:
        """Request current emotion state from core via NATS"""
        return await self._nats_request_with_trace("emotion.current", b"{}")
    
    async def request_emotion_history(self, limit: int = 10, hours: int = 24) -> Dict[str, Any]:
        """Request emotion history from core via NATS"""
        payload = json.dumps({"limit": limit, "hours": hours}).encode('utf-8')
        return await self._nats_request_with_trace("emotion.history", payload)
    
    async def request_semantic_memory_stats(self) -> Dict[str, Any]:
        """Request semantic memory stats from core via NATS"""
        return await self._nats_request_with_trace("memory.semantic.stats", b"{}")
    
    async def request_working_memory_stats(self) -> Dict[str, Any]:
        """Request working memory stats from core via NATS"""
        return await self._nats_request_with_trace("memory.working.stats", b"{}")
    
    async def request_kg_stats(self, user_id: str) -> Dict[str, Any]:
        """Request KG stats from core via NATS"""
        payload = json.dumps({"user_id": user_id}).encode('utf-8')
        return await self._nats_request_with_trace("kg.stats", payload)
    
    async def request_kg_nodes(self, user_id: str, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        """Request KG nodes from core via NATS"""
        payload = json.dumps({"user_id": user_id, "limit": limit, "offset": offset}).encode('utf-8')
        return await self._nats_request_with_trace("kg.nodes", payload)
    
    async def request_kg_edges(self, user_id: str, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        """Request KG edges from core via NATS"""
        payload = json.dumps({"user_id": user_id, "limit": limit, "offset": offset}).encode('utf-8')
        return await self._nats_request_with_trace("kg.edges", payload)

    async def request_kg_schema(self, user_id: str) -> Dict[str, Any]:
        """Request KG schema from core via NATS"""
        payload = json.dumps({"user_id": user_id}).encode("utf-8")
        return await self._nats_request_with_trace("kg.schema", payload)

    async def request_kg_changes(
        self,
        user_id: str,
        from_timestamp: str,
        to_timestamp: str,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """Request KG changes in a time range from core via NATS"""
        payload = json.dumps(
            {
                "user_id": user_id,
                "from_timestamp": from_timestamp,
                "to_timestamp": to_timestamp,
                "limit": limit,
            }
        ).encode("utf-8")
        return await self._nats_request_with_trace("kg.changes", payload)

    async def request_kg_query_templates(self, user_id: str) -> Dict[str, Any]:
        """Request KG query templates from core via NATS"""
        payload = json.dumps({"user_id": user_id}).encode("utf-8")
        return await self._nats_request_with_trace("kg.query-templates", payload)
    
    async def request_memory_album(
        self, 
        user_uuid: str,
        category: str = None,
        favorites_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Request memory album from core via NATS"""
        payload = json.dumps({
            "user_uuid": user_uuid,
            "category": category,
            "favorites_only": favorites_only,
            "limit": limit,
            "offset": offset
        }).encode('utf-8')
        return await self._nats_request_with_trace("memory.album", payload)
    
    async def request_operations_databases(self) -> Dict[str, Any]:
        """Request operations databases from core via NATS"""
        return await self._nats_request_with_trace("operations.databases", b"{}")

    async def request_operations_postgresql_schema(self) -> Dict[str, Any]:
        """Request PostgreSQL schema metadata from core via NATS"""
        return await self._nats_request_with_trace("operations.databases.postgresql.schema", b"{}")

    async def request_operations_postgresql_details(self) -> Dict[str, Any]:
        """Request PostgreSQL database details from core via NATS"""
        return await self._nats_request_with_trace("operations.databases.postgresql.details", b"{}")
    
    async def request_operations_topology(self) -> Dict[str, Any]:
        """Request operations topology from core via NATS"""
        return await self._nats_request_with_trace("operations.topology", b"{}")
    
    async def request_operations_create_backup(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Request backup creation from core via NATS"""
        payload = json.dumps(request_data).encode('utf-8')
        return await self._nats_request_with_trace("operations.backup.create", payload, timeout=60.0)
    
    async def request_operations_backup_sets(self) -> Dict[str, Any]:
        """Request operations backup sets from core via NATS"""
        return await self._nats_request_with_trace("operations.backup_sets", b"{}")
    
    async def request_scheduler_expected_runs_today(self) -> Dict[str, Any]:
        """Request scheduler expected runs today from core via NATS"""
        return await self._nats_request_with_trace("scheduler.expected_runs_today", b"{}")
    
    async def request_system_metrics_all(self) -> Dict[str, Any]:
        """Request all system metrics from core via NATS"""
        return await self._nats_request_with_trace("system.metrics.all", b"{}", timeout=10.0)
    
    async def request_system_overview(self) -> Dict[str, Any]:
        """Request system overview from core via NATS"""
        return await self._nats_request_with_trace("system.overview", b"{}")
    
    async def request_system_health(self) -> Dict[str, Any]:
        """Request system health from core via NATS"""
        return await self._nats_request_with_trace("system.health", b"{}")
    
    async def request_health_services(self) -> Dict[str, Any]:
        """Request health services from core via NATS"""
        return await self._nats_request_with_trace("system.health.services", b"{}")
    
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
