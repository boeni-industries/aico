from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class UserProactivePreferences(BaseModel):
    user_id: str

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

    updated_at: str
