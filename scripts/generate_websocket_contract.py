from __future__ import annotations

import argparse
import json
import os
from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def _stable_json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _read_text_if_exists(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _get_pydantic_schema(model: Any) -> Dict[str, Any]:
    # Pydantic v1: .schema(); Pydantic v2: .model_json_schema()
    if hasattr(model, "model_json_schema"):
        return model.model_json_schema()  # type: ignore[attr-defined]
    return model.schema()  # type: ignore[attr-defined]


class WebSocketMessageType(str, Enum):
    """WebSocket message types"""

    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    AI_RESPONSE = "ai_response"
    SYSTEM_MESSAGE = "system_message"
    ERROR = "error"
    STATUS_UPDATE = "status_update"


class WebSocketAIResponse(BaseModel):
    """AI response via WebSocket"""

    type: WebSocketMessageType = Field(WebSocketMessageType.AI_RESPONSE, description="Message type")
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: str = Field(..., description="AI message ID")
    message: str = Field(..., description="AI response text")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    data: Optional[dict[str, Any]] = Field(None, description="Message payload")
    confidence: Optional[float] = Field(None, description="Response confidence score")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")


class WebSocketError(BaseModel):
    """Error message via WebSocket"""

    type: WebSocketMessageType = Field(WebSocketMessageType.ERROR, description="Message type")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    conversation_id: Optional[str] = Field(None, description="Related conversation ID if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    data: Optional[dict[str, Any]] = Field(None, description="Message payload")


class WebSocketStatusUpdate(BaseModel):
    """Status update via WebSocket"""

    type: WebSocketMessageType = Field(WebSocketMessageType.STATUS_UPDATE, description="Message type")
    conversation_id: str = Field(..., description="Conversation ID")
    status: str = Field(..., description="New status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    data: Optional[dict[str, Any]] = Field(None, description="Message payload")
    details: Optional[dict[str, Any]] = Field(None, description="Additional status details")


class SchedulerEventSeverity(str, Enum):
    """Event severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SchedulerEventType(str, Enum):
    """Scheduler event types for WebSocket notifications"""

    TASK_STUCK = "task_stuck"
    TASK_LONG_RUNNING = "task_long_running"
    TASK_FAILED = "task_failed"
    TASK_COMPLETED = "task_completed"
    SCHEDULER_ERROR = "scheduler_error"


class SchedulerEventMessage(BaseModel):
    """WebSocket message for scheduler events"""

    type: SchedulerEventType = Field(..., description="Event type")
    task_id: str = Field(..., description="Task identifier")
    severity: SchedulerEventSeverity = Field(..., description="Event severity")
    timestamp: str = Field(..., description="Event timestamp (ISO format)")
    details: dict[str, Any] = Field(default_factory=dict, description="Event details")


def _build_ws_contract() -> Dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    repo_config_dir = repo_root / "config"
    os.environ.setdefault("AICO_CONFIG_DIR", str(repo_config_dir))

    # Ensure config can be loaded in lightweight mode (mirrors OpenAPI generation scripts)
    from aico.core.config import ConfigurationManager

    ConfigurationManager(config_dir=repo_config_dir).initialize(lightweight=True)

    contract: Dict[str, Any] = {
        "version": "v1",
        "fastapi": {
            "endpoints": [
                {
                    "path": "/api/v1/conversation/ws",
                    "auth": {
                        "type": "jwt",
                        "header": "Authorization: Bearer <token>",
                        "query_param_fallback": "token",
                    },
                    "description": "User-scoped real-time conversation updates.",
                    "incoming": [
                        {
                            "type": "heartbeat",
                            "shape": {"type": "heartbeat"},
                        }
                    ],
                    "outgoing_schemas": {
                        "ai_response": _get_pydantic_schema(WebSocketAIResponse),
                        "error": _get_pydantic_schema(WebSocketError),
                        "status_update": _get_pydantic_schema(WebSocketStatusUpdate),
                    },
                },
                {
                    "path": "/api/v1/scheduler/ws/events",
                    "auth": {
                        "type": "jwt",
                        "header": "Authorization: Bearer <token>",
                        "query_param_fallback": "token",
                    },
                    "description": "Admin-scoped real-time scheduler event notifications.",
                    "incoming": [
                        {
                            "type": "heartbeat",
                            "shape": {"type": "heartbeat"},
                        }
                    ],
                    "outgoing_schemas": {
                        "scheduler_event": _get_pydantic_schema(SchedulerEventMessage),
                        "heartbeat_ack": {
                            "type": "object",
                            "properties": {
                                "type": {"const": "heartbeat_ack"},
                                "timestamp": {"type": "string"},
                            },
                            "required": ["type", "timestamp"],
                            "additionalProperties": False,
                        },
                    },
                },
            ],
        },
        "gateway_websocket_adapter": {
            "description": "Protocol-level WS server implemented in gateway/adapters/websocket_adapter.py (websockets library).",
            "path_default": "/ws",
            "message_format": "json",
            "incoming_messages": {
                "auth": {
                    "type": "object",
                    "properties": {
                        "type": {"const": "auth"},
                        "token": {"type": "string"},
                        "device_uuid": {"type": "string"},
                    },
                    "required": ["type"],
                    "additionalProperties": True,
                },
                "subscribe": {
                    "type": "object",
                    "properties": {"type": {"const": "subscribe"}, "topic": {"type": "string"}},
                    "required": ["type", "topic"],
                    "additionalProperties": False,
                },
                "unsubscribe": {
                    "type": "object",
                    "properties": {"type": {"const": "unsubscribe"}, "topic": {"type": "string"}},
                    "required": ["type", "topic"],
                    "additionalProperties": False,
                },
                "request": {
                    "type": "object",
                    "properties": {
                        "type": {"const": "request"},
                        "id": {"type": ["string", "null"]},
                        "message_type": {"type": "string"},
                        "payload": {"type": "object"},
                    },
                    "required": ["type", "message_type"],
                    "additionalProperties": True,
                },
                "heartbeat": {
                    "type": "object",
                    "properties": {"type": {"const": "heartbeat"}},
                    "required": ["type"],
                    "additionalProperties": True,
                },
            },
            "outgoing_messages": {
                "welcome": {
                    "type": "object",
                    "properties": {
                        "type": {"const": "welcome"},
                        "client_id": {"type": "string"},
                        "server": {"type": "string"},
                        "version": {"type": "string"},
                    },
                    "required": ["type", "client_id", "server", "version"],
                    "additionalProperties": False,
                },
                "auth_success": {
                    "type": "object",
                    "properties": {
                        "type": {"const": "auth_success"},
                        "user_uuid": {"type": "string"},
                        "roles": {"type": "array"},
                        "session_id": {"type": ["string", "null"]},
                    },
                    "required": ["type", "user_uuid", "roles"],
                    "additionalProperties": False,
                },
                "subscribed": {
                    "type": "object",
                    "properties": {"type": {"const": "subscribed"}, "topic": {"type": "string"}},
                    "required": ["type", "topic"],
                    "additionalProperties": False,
                },
                "unsubscribed": {
                    "type": "object",
                    "properties": {"type": {"const": "unsubscribed"}, "topic": {"type": "string"}},
                    "required": ["type", "topic"],
                    "additionalProperties": False,
                },
                "response": {
                    "type": "object",
                    "properties": {
                        "type": {"const": "response"},
                        "id": {"type": ["string", "null"]},
                        "success": {"type": "boolean"},
                        "correlation_id": {"type": ["string", "null"]},
                        "data": {},
                        "error": {},
                    },
                    "required": ["type", "success"],
                    "additionalProperties": True,
                },
                "heartbeat_ack": {
                    "type": "object",
                    "properties": {"type": {"const": "heartbeat_ack"}, "timestamp": {}},
                    "required": ["type", "timestamp"],
                    "additionalProperties": False,
                },
                "error": {
                    "type": "object",
                    "properties": {
                        "type": {"const": "error"},
                        "error": {"type": "string"},
                        "detail": {"type": ["string", "null"]},
                    },
                    "required": ["type", "error"],
                    "additionalProperties": False,
                },
            },
        },
    }

    return contract


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate frozen WebSocket contract (golden artifact)")
    parser.add_argument(
        "--output",
        default="contracts/websocket/v1.json",
        help="Output path for generated WebSocket contract (json)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the generated contract differs from the existing artifact",
    )
    args = parser.parse_args()

    output_path = Path(args.output)

    contract = _build_ws_contract()
    rendered = _stable_json_dumps(contract)

    if args.check:
        existing = _read_text_if_exists(output_path)
        if existing is None:
            raise SystemExit(f"WebSocket contract artifact missing: {output_path}")
        if existing != rendered:
            raise SystemExit(
                "WebSocket contract artifact differs from generated contract. "
                "Run scripts/generate_websocket_contract.py to update contracts/websocket/v1.json"
            )
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
