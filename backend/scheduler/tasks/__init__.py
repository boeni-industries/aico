"""
AICO Task Definitions

Contains base task classes and built-in task implementations.
"""

from .base import BaseTask, TaskContext, TaskResult, TaskStatus
from .curiosity_scan import CuriosityScanTask

__all__ = [
    "BaseTask",
    "TaskContext", 
    "TaskResult",
    "TaskStatus",
    "CuriosityScanTask",
]
