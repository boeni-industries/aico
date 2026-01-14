"""
User Proactive Preferences Data Models

Dataclasses for user proactive behavior preferences.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserProactivePreferences:
    """User proactive preferences model - matches user_proactive_preferences table."""
    user_id: str
    updated_at: str
    followup_enabled: bool = True
    reminder_enabled: bool = True
    preferred_followup_times: Optional[str] = None
    preferred_reminder_times: Optional[str] = None
    max_followups_per_day: int = 3
    max_reminders_per_day: int = 5
    min_hours_between_followups: int = 4
    min_hours_between_reminders: int = 2
    cluster_reminders: int = 1
    auto_snooze_duration_minutes: int = 60
