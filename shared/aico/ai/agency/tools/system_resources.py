"""System Resource Monitoring Tools

Atomic tools for measuring CPU, memory, and disk usage.
"""

from __future__ import annotations

import os
import psutil
import shutil
from datetime import datetime, UTC
from typing import Dict, Any
from pathlib import Path

from aico.core.logging import get_logger
from aico.core.paths import AICOPaths
from .registry import ToolDefinition, get_tool_registry


logger = get_logger("shared.ai.agency.tools.system_resources")


async def tool_system_cpu_measure_load() -> Dict[str, Any]:
    """Atomic tool: measure current CPU load.
    
    Returns CPU usage percentage and load averages.
    """
    start = datetime.now(UTC)
    try:
        # Get CPU percentage over 1 second interval
        cpu_percent = psutil.cpu_percent(interval=1.0)
        
        # Get load averages (1, 5, 15 minutes) - Unix only
        try:
            load_avg = os.getloadavg()
            load_1, load_5, load_15 = load_avg
        except (AttributeError, OSError):
            # Windows doesn't have getloadavg
            load_1 = load_5 = load_15 = None
        
        cpu_count = psutil.cpu_count()
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "cpu_percent": cpu_percent,
                    "cpu_count": cpu_count,
                    "load_avg_1min": load_1,
                    "load_avg_5min": load_5,
                    "load_avg_15min": load_15,
                },
            },
            "error": None,
        }
    except Exception as exc:
        logger.error("[TOOL_SYSTEM_RESOURCES] CPU measurement failed: %s", exc)
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
                "code": "cpu_measurement_failed",
                "message": str(exc),
            },
        }


async def tool_system_memory_measure_usage() -> Dict[str, Any]:
    """Atomic tool: measure current memory usage."""
    start = datetime.now(UTC)
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "total_bytes": mem.total,
                    "available_bytes": mem.available,
                    "used_bytes": mem.used,
                    "percent": mem.percent,
                    "swap_total_bytes": swap.total,
                    "swap_used_bytes": swap.used,
                    "swap_percent": swap.percent,
                },
            },
            "error": None,
        }
    except Exception as exc:
        logger.error("[TOOL_SYSTEM_RESOURCES] Memory measurement failed: %s", exc)
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
                "code": "memory_measurement_failed",
                "message": str(exc),
            },
        }


async def tool_system_disk_measure_usage() -> Dict[str, Any]:
    """Atomic tool: measure disk usage for AICO data directory."""
    start = datetime.now(UTC)
    try:
        # Measure AICO data directory
        data_path = AICOPaths.get_data_directory()
        
        # Get disk usage for the partition containing AICO data
        usage = shutil.disk_usage(data_path)
        
        # Also get PostgreSQL data size if accessible
        postgres_size = None
        try:
            postgres_path = data_path / "postgres"
            if postgres_path.exists():
                postgres_size = sum(
                    f.stat().st_size for f in postgres_path.rglob('*') if f.is_file()
                )
        except Exception:
            pass
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "percent": (usage.used / usage.total * 100) if usage.total > 0 else 0,
                    "data_path": str(data_path),
                    "postgres_size_bytes": postgres_size,
                },
            },
            "error": None,
        }
    except Exception as exc:
        logger.error("[TOOL_SYSTEM_RESOURCES] Disk measurement failed: %s", exc)
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
                "code": "disk_measurement_failed",
                "message": str(exc),
            },
        }


def _register_system_resource_tools() -> None:
    """Register system resource monitoring tools in the global ToolRegistry."""
    registry = get_tool_registry()
    
    # CPU
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.system.cpu.measure_load",
            name="CPU Load Measurement",
            description="Measure current CPU usage percentage and load averages.",
            domain="system",
            backend="python",
            runtime_context="backend_service",
            capability_tags=["check_health", "measure_resources"],
            side_effect_tags=["reads_system_state"],
            safety_level="low",
            resource_profile="tiny",
            default_timeout_seconds=5,
            handler=tool_system_cpu_measure_load,
        )
    )
    
    # Memory
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.system.memory.measure_usage",
            name="Memory Usage Measurement",
            description="Measure current memory and swap usage.",
            domain="system",
            backend="python",
            runtime_context="backend_service",
            capability_tags=["check_health", "measure_resources"],
            side_effect_tags=["reads_system_state"],
            safety_level="low",
            resource_profile="tiny",
            default_timeout_seconds=3,
            handler=tool_system_memory_measure_usage,
        )
    )
    
    # Disk
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.system.disk.measure_usage",
            name="Disk Usage Measurement",
            description="Measure disk usage for AICO data directory.",
            domain="system",
            backend="python",
            runtime_context="backend_service",
            capability_tags=["check_health", "measure_resources"],
            side_effect_tags=["reads_system_state"],
            safety_level="low",
            resource_profile="tiny",
            default_timeout_seconds=3,
            handler=tool_system_disk_measure_usage,
        )
    )


# Register tools at import time
_register_system_resource_tools()
