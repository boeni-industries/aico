"""
Message Processing Core

Handles the complex logic for processing user messages through the AI pipeline.
This module centralizes all completion-related processing logic.
"""

from __future__ import annotations

from typing import Optional


class MessageProcessor:
    """Handles complex message processing logic."""
    
    def __init__(self, config_manager: Optional[object] = None):
        raise RuntimeError(
            "MessageProcessor is retired: modelservice uses ModelserviceNATSService + handlers (vLLM)."
        )

