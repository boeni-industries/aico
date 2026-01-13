"""
AMS (Adaptive Modeling System) Data Models

Dataclasses for AMS entities (trajectories, feedback).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Trajectory:
    """AMS trajectory model."""
    trajectory_id: str
    user_id: str
    start_time: datetime
    status: str
    goal_id: Optional[str] = None
    end_time: Optional[datetime] = None
    outcome: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Feedback:
    """AMS feedback model."""
    feedback_id: str
    user_id: str
    trajectory_id: Optional[str]
    feedback_type: str
    content: str
    rating: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
