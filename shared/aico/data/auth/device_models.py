"""
Auth Device Data Models

Dataclasses for device entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Device:
    """Device model - matches auth_devices table."""
    uuid: str
    device_name: str
    device_type: str
    platform: str
    is_active: bool = True
    last_seen: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
