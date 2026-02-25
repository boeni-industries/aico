"""
NATS request handlers for core services.

Handles gateway→core requests via NATS request/reply pattern.
"""

import json
from typing import Any, Dict
from aico.core.logging import get_logger
from google.protobuf.struct_pb2 import Struct

logger = get_logger("backend.core.nats_handlers")


class CoreNATSHandlers:
    """NATS request handlers for core services"""
    
    def __init__(self, service_container):
        self.container = service_container
        self.logger = logger
    
    async def handle_scheduler_status_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scheduler status request from gateway"""
        try:
            scheduler = self.container.get_service("task_scheduler")
            if scheduler is None:
                return {
                    "error": "SCHEDULER_NOT_AVAILABLE",
                    "message": "Task scheduler not available"
                }
            
            status = scheduler.get_status()
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get scheduler status: {e}")
            return {
                "error": "SCHEDULER_ERROR",
                "message": str(e)
            }
    
    async def handle_scheduler_tasks_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scheduler tasks list request from gateway"""
        try:
            enabled_only = request_data.get("enabled_only", False)
            
            # Get scheduler service
            scheduler = self.container.get_service("task_scheduler")
            if scheduler is None:
                return {
                    "error": "SCHEDULER_NOT_AVAILABLE",
                    "message": "Task scheduler not available"
                }
            
            # Return task info matching TaskConfigResponse schema
            tasks = []
            for task_id, task_class in scheduler.task_registry.tasks.items():
                tasks.append({
                    "task_id": task_id,
                    "task_class": task_class.__name__ if hasattr(task_class, '__name__') else str(task_class),
                    "schedule": "* * * * *",
                    "config": {},
                    "enabled": True,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                })
            
            return {"tasks": tasks, "total_count": len(tasks)}
            
        except Exception as e:
            self.logger.error(f"Failed to list scheduler tasks: {e}", exc_info=True)
            return {
                "error": "SCHEDULER_ERROR",
                "message": str(e)
            }
    
    async def handle_emotion_history_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emotion history request from gateway"""
        try:
            # Extract query params
            limit = request_data.get("limit", 10)
            hours = request_data.get("hours", 24)
            
            # Get emotion engine service
            emotion_engine = self.container.get_service("emotion_engine")
            if emotion_engine is None:
                return {
                    "error": "EMOTION_ENGINE_UNAVAILABLE",
                    "message": "Emotion engine unavailable"
                }
            
            # Get emotion state history from engine
            history = await emotion_engine.get_state_history(limit=limit)
            self.logger.info(f"🎭 Emotion engine returned {len(history)} states (limit={limit})")
            
            # Add metadata about data age and diversity
            metadata = {}
            if history:
                from datetime import datetime, UTC
                
                # Check data age
                try:
                    last_timestamp = datetime.fromisoformat(history[-1]["timestamp"].replace('Z', '+00:00'))
                    age_hours = (datetime.now(UTC) - last_timestamp).total_seconds() / 3600
                    metadata["oldest_record_age_hours"] = age_hours
                    metadata["newest_record_timestamp"] = history[-1]["timestamp"]
                    metadata["oldest_record_timestamp"] = history[0]["timestamp"]
                except Exception as e:
                    self.logger.warning(f"Could not parse timestamp for metadata: {e}")
                
                # Check diversity
                unique_feelings = len(set(h.get('feeling') for h in history))
                metadata["unique_feelings_count"] = unique_feelings
                
                self.logger.info(f"🎭 Data diversity: {unique_feelings} unique feelings, newest record age: {metadata.get('oldest_record_age_hours', 0):.1f}h")
            
            return {
                "count": len(history), 
                "history": history,
                "metadata": metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get emotion history: {e}", exc_info=True)
            return {
                "error": "EMOTION_ENGINE_ERROR",
                "message": str(e)
            }
    
    def _extract_request_data(self, request_envelope) -> Dict[str, Any]:
        """Extract JSON data from request envelope"""
        try:
            # Check if request has JSON data in attributes
            if hasattr(request_envelope, 'metadata') and hasattr(request_envelope.metadata, 'attributes'):
                json_data = request_envelope.metadata.attributes.get('json_data', '{}')
                return json.loads(json_data)
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to extract request data: {e}")
            return {}
    
    async def setup_handlers(self, message_bus_client):
        """Register all NATS request handlers using native NATS request/reply"""
        
        def make_handler(handler_func, response_type):
            """Create a NATS message handler that processes requests and sends replies"""
            async def handler(msg):
                try:
                    # Parse JSON request directly from bytes
                    request_data = json.loads(msg.data.decode('utf-8')) if msg.data else {}
                    
                    # Process request
                    response_data = await handler_func(request_data)
                    
                    # Send JSON response as plain bytes (simplest approach)
                    response_bytes = json.dumps(response_data).encode('utf-8')
                    
                    # Send reply using NATS built-in reply mechanism
                    await message_bus_client._nats.publish(
                        msg.reply,
                        response_bytes
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error in {response_type} handler: {e}", exc_info=True)
            
            return handler
        
        # Register handlers using direct NATS subscriptions (not MessageBusClient.subscribe)
        # because we need access to the raw NATS message for the reply subject
        self.logger.info("Subscribing to scheduler.status...")
        sid1 = await message_bus_client._nats.subscribe(
            "scheduler.status",
            cb=make_handler(self.handle_scheduler_status_request, "scheduler.status.reply")
        )
        self.logger.info(f"✅ Subscribed to scheduler.status (sid={sid1})")
        
        self.logger.info("Subscribing to scheduler.tasks...")
        sid2 = await message_bus_client._nats.subscribe(
            "scheduler.tasks",
            cb=make_handler(self.handle_scheduler_tasks_request, "scheduler.tasks.reply")
        )
        self.logger.info(f"✅ Subscribed to scheduler.tasks (sid={sid2})")
        
        self.logger.info("Subscribing to emotion.history...")
        sid3 = await message_bus_client._nats.subscribe(
            "emotion.history",
            cb=make_handler(self.handle_emotion_history_request, "emotion.history.reply")
        )
        self.logger.info(f"✅ Subscribed to emotion.history (sid={sid3})")
        
        self.logger.info("Core NATS request handlers registered (scheduler.status, scheduler.tasks, emotion.history)")
