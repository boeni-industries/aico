"""
Proactive System Data Models

Dataclasses for proactive analytics and reminder entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ProactiveAnalytics:
    """Proactive analytics model - matches proactive_analytics table."""
    id: str
    user_id: str
    event_type: str
    created_at: datetime
    event_data: Optional[str] = None
    confidence_score: Optional[float] = None
    triggered_action: Optional[str] = None


@dataclass
class ProactiveReminderCluster:
    """Proactive reminder cluster model - matches proactive_reminder_clusters table."""
    cluster_id: str
    user_id: str
    cluster_name: str
    created_at: datetime
    reminder_ids: Optional[str] = None
    pattern_description: Optional[str] = None
    confidence_score: Optional[float] = None
