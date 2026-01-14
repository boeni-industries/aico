"""
System Event Data Models

Dataclasses for system event entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class SystemEvent:
    """System event model - matches system_events table."""
    id: int
    timestamp: str
    topic: str
    source: str
    message_type: str
    message_id: str
    priority: int
    correlation_id: Optional[str] = None
    payload: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
