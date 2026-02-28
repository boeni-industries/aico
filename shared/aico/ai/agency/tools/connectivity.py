from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Dict

import httpx

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
from aico.data.uow import UnitOfWork
from aico.data.influx.connection import InfluxDBConnection
from .registry import ToolDefinition, get_tool_registry


logger = get_logger("shared.ai.agency.tools.maintenance.connectivity")


async def tool_db_postgres_ping(session_factory: Any) -> Dict[str, Any]:
    """Atomic tool: check PostgreSQL connectivity via a lightweight read.

    Contract (per WIP-self-healing-skills-tools.md):
    {
        "ok": bool,
        "data": {
            "status": "ok" | "warning" | "error",
            "latency_ms": int | None,
            "error_message": str | None,
            "details": dict,
        },
        "error": None | {"code": str, "message": str},
    }
    """

    start = datetime.now(UTC)
    try:
        async with UnitOfWork(session_factory) as uow:
            # Simple query to validate DB connectivity via repositories.
            if hasattr(uow, "user_profiles"):
                await uow.user_profiles.list(limit=1)

        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {},
            },
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - defensive safety net
        logger.error("[TOOL_CONNECTIVITY] PostgreSQL ping failed: %s", exc)
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
                "code": "db_postgres_ping_failed",
                "message": str(exc),
            },
        }


async def tool_db_influx_ping() -> Dict[str, Any]:
    """Atomic tool: ping InfluxDB using the connection wrapper.

    Uses InfluxDBConnection.ping() which issues a lightweight health request.
    """

    start = datetime.now(UTC)
    try:
        conn = InfluxDBConnection()
        ok = conn.ping()
        conn.close()

        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        status = "ok" if ok else "error"
        return {
            "ok": ok,
            "data": {
                "status": status,
                "latency_ms": latency_ms,
                "error_message": None if ok else "Ping returned False",
                "details": {},
            },
            "error": None if ok else {
                "code": "db_influx_ping_failed",
                "message": "InfluxDB ping returned False",
            },
        }
    except Exception as exc:  # pragma: no cover - defensive safety net
        logger.error("[TOOL_CONNECTIVITY] InfluxDB ping failed: %s", exc)
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
                "code": "db_influx_ping_failed",
                "message": str(exc),
            },
        }


async def tool_db_lmdb_ping() -> Dict[str, Any]:
    """Atomic tool: ping LMDB working memory by opening and closing the env."""

    start = datetime.now(UTC)
    try:
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": True,
            "data": {
                "status": "deprecated",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {},
            },
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - defensive safety net
        logger.error("[TOOL_CONNECTIVITY] LMDB ping failed: %s", exc)
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
                "code": "db_lmdb_ping_failed",
                "message": str(exc),
            },
        }


async def tool_modelservice_ping() -> Dict[str, Any]:
    """Atomic tool: ping modelservice via its ZMQ health endpoint."""

    start = datetime.now(UTC)
    try:
        # Importing backend.services from shared is acceptable here; this tool is
        # only used in backend contexts for maintenance.
        from backend.services import get_modelservice_client

        config = ConfigurationManager()
        config.initialize(lightweight=True)
        client = get_modelservice_client(config)
        ok = await client.check_modelservice_health()

        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        status = "ok" if ok else "error"
        return {
            "ok": ok,
            "data": {
                "status": status,
                "latency_ms": latency_ms,
                "error_message": None if ok else "Modelservice health check failed",
                "details": {},
            },
            "error": None if ok else {
                "code": "modelservice_ping_failed",
                "message": "Modelservice health check failed",
            },
        }
    except Exception as exc:  # pragma: no cover - defensive safety net
        logger.error("[TOOL_CONNECTIVITY] Modelservice ping failed: %s", exc)
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
                "code": "modelservice_ping_failed",
                "message": str(exc),
            },
        }


async def tool_ollama_ping() -> Dict[str, Any]:
    """Atomic tool: ping Ollama HTTP API /api/version for basic connectivity."""

    start = datetime.now(UTC)
    try:
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        ollama_cfg = config.get("modelservice.ollama", {}) or {}
        host = ollama_cfg.get("host", "127.0.0.1")
        port = ollama_cfg.get("port", 11434)
        url = f"http://{host}:{port}/api/version"

        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(url)
        ok = response.status_code == 200

        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        status = "ok" if ok else "error"
        details: Dict[str, Any] = {"status_code": response.status_code}
        if ok:
            try:
                data = response.json()
                details["version"] = data.get("version")
            except Exception:
                pass

        return {
            "ok": ok,
            "data": {
                "status": status,
                "latency_ms": latency_ms,
                "error_message": None if ok else f"HTTP {response.status_code}",
                "details": details,
            },
            "error": None if ok else {
                "code": "ollama_ping_failed",
                "message": f"Ollama /api/version returned HTTP {response.status_code}",
            },
        }
    except Exception as exc:  # pragma: no cover - defensive safety net
        logger.error("[TOOL_CONNECTIVITY] Ollama ping failed: %s", exc)
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
                "code": "ollama_ping_failed",
                "message": str(exc),
            },
        }


def _register_connectivity_tools() -> None:
    """Register connectivity ping tools in the global ToolRegistry.

    This makes them discoverable by skills via tool_id rather than direct
    imports, following the Skill & Tool Layer design.
    """

    registry = get_tool_registry()

    # PostgreSQL
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.db.postgres.ping",
            name="PostgreSQL Ping",
            description="Check PostgreSQL connectivity via a lightweight UoW query.",
            domain="connectivity",
            backend="python",
            runtime_context="backend_service",
            capability_tags=["check_health", "check_connectivity"],
            side_effect_tags=["reads_database"],
            safety_level="low",
            resource_profile="tiny",
            default_timeout_seconds=3,
            handler=tool_db_postgres_ping,
        )
    )

    # InfluxDB
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.db.influx.ping",
            name="InfluxDB Ping",
            description="Check InfluxDB connectivity using the InfluxDBConnection wrapper.",
            domain="connectivity",
            backend="python",
            runtime_context="backend_service",
            capability_tags=["check_health", "check_connectivity"],
            side_effect_tags=["reads_metrics"],
            safety_level="low",
            resource_profile="tiny",
            default_timeout_seconds=3,
            handler=tool_db_influx_ping,
        )
    )

    # Modelservice
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.modelservice.ping",
            name="Modelservice Ping",
            description="Check modelservice health via its ZMQ health endpoint.",
            domain="connectivity",
            backend="zmq",
            runtime_context="backend_service",
            capability_tags=["check_health", "check_connectivity"],
            side_effect_tags=["reads_service_state"],
            safety_level="low",
            resource_profile="tiny",
            default_timeout_seconds=3,
            handler=tool_modelservice_ping,
        )
    )

    # Ollama
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.ollama.ping",
            name="Ollama Ping",
            description="Check Ollama HTTP API /api/version for basic connectivity.",
            domain="connectivity",
            backend="http",
            runtime_context="backend_service",
            capability_tags=["check_health", "check_connectivity"],
            side_effect_tags=["reads_service_state"],
            safety_level="low",
            resource_profile="tiny",
            default_timeout_seconds=3,
            handler=tool_ollama_ping,
        )
    )


# Register tools at import time so the registry is ready for skills.
_register_connectivity_tools()
