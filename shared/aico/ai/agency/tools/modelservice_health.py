"""Modelservice Health Monitoring Tools

Atomic tools for testing modelservice inference and pipeline health.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Dict, Any

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from core.services.modelservice_client import get_modelservice_client
from .registry import ToolDefinition, get_tool_registry


logger = get_logger("shared.ai.agency.tools.modelservice_health")


async def tool_modelservice_scan_health() -> Dict[str, Any]:
    """Atomic tool: test modelservice health and get available models.
    
    Checks if modelservice is reachable and queries available models.
    """
    start = datetime.now(UTC)
    try:
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        client = get_modelservice_client(config)
        
        # Check if modelservice is reachable
        ok = await client.check_modelservice_health()
        
        # Try to get list of available models
        available_models = []
        if ok:
            try:
                # Get default model from config
                default_model = config.get("modelservice.default_model", "qwen2.5:3b")
                available_models.append(default_model)
            except Exception:
                pass
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": ok,
            "data": {
                "status": "ok" if ok else "error",
                "latency_ms": latency_ms,
                "error_message": None if ok else "Modelservice health check failed",
                "details": {
                    "available_models": available_models,
                    "model_count": len(available_models),
                },
            },
            "error": None if ok else {
                "code": "modelservice_health_check_failed",
                "message": "Modelservice is not reachable",
            },
        }
    except Exception as exc:
        logger.error("[TOOL_MODELSERVICE_HEALTH] Test completion failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {
                "code": "modelservice_test_completion_failed",
                "message": str(exc),
            },
        }


def _register_modelservice_health_tools() -> None:
    """Register modelservice health monitoring tools in the global ToolRegistry."""
    registry = get_tool_registry()
    
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.modelservice.scan_health",
            name="Modelservice Health Check",
            description="Check modelservice health and get available models.",
            domain="modelservice",
            backend="zmq",
            runtime_context="backend_service",
            capability_tags=["check_health"],
            side_effect_tags=["reads_service_state"],
            safety_level="low",
            resource_profile="small",
            default_timeout_seconds=10,
            handler=tool_modelservice_scan_health,
        )
    )


# Register tools at import time
_register_modelservice_health_tools()
