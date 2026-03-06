"""
Scheduler Events - DEPRECATED

WebSocket functionality moved to API Gateway WebSocket adapter.
This module is kept for backward compatibility but should not be used.
Clients should connect to ws://gateway:8772/ws and subscribe to "scheduler.events"
"""

import uuid
from typing import Dict, Any
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from datetime import datetime, UTC

from aico.core.logging import get_logger
from backend.api.dependencies import authenticate_websocket
from backend.api.scheduler.schemas import (
    SchedulerEventMessage,
    SchedulerEventType
)

logger = get_logger("backend.api.scheduler.events")

# DEPRECATED: Active WebSocket connections moved to gateway adapter
active_scheduler_connections: Dict[str, WebSocket] = {}


async def scheduler_events_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time scheduler event updates.
    
    Provides live notifications for:
    - Stuck tasks (exceeded timeout + buffer)
    - Long-running tasks (approaching timeout)
    - Task failures
    - Critical scheduler errors
    
    Follows the same pattern as conversation WebSocket endpoint.
    """
    try:
        user = authenticate_websocket(websocket=websocket)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    user_id = user["user_id"]
    connection_id = f"scheduler_{user_id}_{uuid.uuid4()}"
    active_scheduler_connections[connection_id] = websocket
    
    logger.info(f"Scheduler WebSocket connection established", extra={
        "connection_id": connection_id
    })
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (heartbeat, etc.)
                data = await websocket.receive_json()
                
                if data.get("type") == "heartbeat":
                    await websocket.send_json({
                        "type": "heartbeat_ack",
                        "timestamp": datetime.now(UTC).isoformat()
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Scheduler WebSocket error: {e}", extra={
                    "connection_id": connection_id
                })
                break
    
    except Exception as e:
        logger.error(f"Scheduler WebSocket connection error: {e}", extra={
            "connection_id": connection_id
        })
    
    finally:
        # Cleanup
        if connection_id in active_scheduler_connections:
            del active_scheduler_connections[connection_id]
        
        logger.info(f"Scheduler WebSocket connection closed", extra={
            "connection_id": connection_id
        })


async def broadcast_scheduler_event(event: Dict[str, Any]):
    """
    Broadcast a scheduler event to all connected WebSocket clients.
    
    Args:
        event: Event data containing type, task_id, severity, details, etc.
    """
    if not active_scheduler_connections:
        return
    
    # Create structured event message
    event_message = {
        "type": event.get("type", "unknown"),
        "task_id": event.get("task_id"),
        "severity": event.get("severity", "info"),
        "timestamp": event.get("timestamp", datetime.now(UTC).isoformat()),
        "details": event.get("details", {})
    }
    
    # Broadcast to all connected clients
    disconnected = []
    for connection_id, websocket in active_scheduler_connections.items():
        try:
            await websocket.send_json(event_message)
            logger.debug(f"Sent scheduler event to {connection_id}", extra={
                "event_type": event_message["type"],
                "task_id": event_message["task_id"]
            })
        except Exception as e:
            logger.warning(f"Failed to send event to {connection_id}: {e}")
            disconnected.append(connection_id)
    
    # Clean up disconnected clients
    for connection_id in disconnected:
        if connection_id in active_scheduler_connections:
            del active_scheduler_connections[connection_id]
