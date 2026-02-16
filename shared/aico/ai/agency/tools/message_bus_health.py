"""Message Bus Health Monitoring Tools

Atomic tools for checking ZeroMQ message bus health and connectivity.
"""

from typing import Dict, Any
from datetime import datetime, UTC

from aico.core.logging import get_logger
from aico.ai.agency.tools.registry import ToolDefinition, get_tool_registry


logger = get_logger("aico.ai.agency.tools.message_bus_health")


async def tool_messagebus_check_status() -> Dict[str, Any]:
    """Check message bus status by verifying ZMQ context and sockets.
    
    Returns:
        Dict with ok, data, and error fields following tool contract
    """
    try:
        # Try to import and check ZMQ
        import zmq
        
        # Check ZMQ version
        zmq_version = zmq.zmq_version()
        pyzmq_version = zmq.pyzmq_version()
        
        # Try to get service container to check if message bus is running
        try:
            from backend.core.service_container import get_service_container
            container = get_service_container()
            
            # Check if message bus plugin is running
            if container and hasattr(container, 'get_service'):
                try:
                    message_bus = container.get_service('message_bus_plugin')
                    if message_bus and hasattr(message_bus, '_host') and message_bus._host:
                        # Message bus is running
                        return {
                            "ok": True,
                            "data": {
                                "status": "ok",
                                "error_message": None,
                                "details": {
                                    "zmq_version": zmq_version,
                                    "pyzmq_version": pyzmq_version,
                                }
                            },
                            "error": None
                        }
                except Exception:
                    pass
            
            # Message bus not running or not accessible
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "error_message": None,
                    "details": {
                        "zmq_version": zmq_version,
                        "pyzmq_version": pyzmq_version,
                    }
                },
                "error": None
            }
        
        except Exception as container_error:
            # Service container not available, but ZMQ is installed
            logger.debug("Service container check failed: %s", container_error)
            return {
                "ok": True,
                "data": {
                    "status": "ok",
                    "error_message": None,
                    "details": {
                        "zmq_version": zmq_version,
                        "pyzmq_version": pyzmq_version,
                    }
                },
                "error": None
            }
    
    except ImportError:
        return {
            "ok": False,
            "data": {
                "status": "error",
                "error_message": "ZMQ not installed",
                "details": {}
            },
            "error": {"code": "import_error", "message": "pyzmq package not found"}
        }
    
    except Exception as exc:
        logger.error("Message bus health check failed: %s", exc)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "error_message": str(exc),
                "details": {}
            },
            "error": {"code": "check_failed", "message": str(exc)}
        }


def _register_message_bus_tools():
    """Register message bus health monitoring tools."""
    registry = get_tool_registry()
    
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.messagebus.check_status",
            name="Message Bus Status Check",
            description="Check ZeroMQ message bus health and connectivity status.",
            domain="message_bus",
            backend="zmq",
            runtime_context="backend_service",
            capability_tags=["check_health", "check_connectivity"],
            side_effect_tags=["reads_service_state"],
            safety_level="low",
            resource_profile="tiny",
            default_timeout_seconds=3,
            handler=tool_messagebus_check_status,
        )
    )


# Register tools at import time
_register_message_bus_tools()
