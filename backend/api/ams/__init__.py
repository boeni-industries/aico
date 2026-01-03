"""
AMS (Adaptive Memory System) API Module

Provides REST endpoints for AMS statistics, consolidation status,
behavioral learning metrics, user preferences, and feedback analytics.
"""

from .router import router

__all__ = ["router"]
