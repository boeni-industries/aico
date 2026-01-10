"""
Metrics Endpoints

Individual endpoint modules for each metrics category.
Each module is self-contained and focused on a single responsibility.
"""

from .gateway import router as gateway_router
from .modelservice import router as modelservice_router
from .memory import router as memory_router
from .scheduler import router as scheduler_router
from .messagebus import router as messagebus_router
from .system import router as system_router
from .all import router as all_router

__all__ = [
    "gateway_router",
    "modelservice_router",
    "memory_router",
    "scheduler_router",
    "messagebus_router",
    "system_router",
    "all_router",
]
