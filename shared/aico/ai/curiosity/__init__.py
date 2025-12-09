"""
Curiosity Engine

Provides intrinsic motivation for AICO through curiosity-driven goal generation.
Detects gaps, anomalies, and under-explored areas in the world model and AMS.
"""

from .models import (
    CuriosityType,
    IntrinsicSignal,
    HobbyTemplate,
    HobbyCategory,
    DEFAULT_HOBBY_TEMPLATES,
)
from .engine import CuriosityEngine

__all__ = [
    "CuriosityType",
    "IntrinsicSignal",
    "HobbyTemplate",
    "HobbyCategory",
    "DEFAULT_HOBBY_TEMPLATES",
    "CuriosityEngine",
]
