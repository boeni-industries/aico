from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict


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


def _build_ws_contract() -> Dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    repo_config_dir = repo_root / "config"
    os.environ.setdefault("AICO_CONFIG_DIR", str(repo_config_dir))

    # Ensure config can be loaded in lightweight mode (mirrors OpenAPI generation scripts)
    from aico.core.config import ConfigurationManager

    ConfigurationManager(config_dir=repo_config_dir).initialize(lightweight=True)

    from backend.api.conversation.schemas import (
        WebSocketAIResponse,
        WebSocketError,
        WebSocketStatusUpdate,
    )
    from backend.api.scheduler.schemas import SchedulerEventMessage

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
            "description": "Protocol-level WS server implemented in backend/api_gateway/adapters/websocket_adapter.py (websockets library).",
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
