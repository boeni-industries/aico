"""
Proactive Behaviors - Phase 6.7

Implements policy-aware follow-up generation and smart reminder scheduling
with relationship-informed timing, values-based filtering, clustering, and adaptation.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass
from enum import Enum

from aico.data.libsql import EncryptedLibSQLConnection


# ============================================================================
# Enums & Data Models
# ============================================================================

class FollowupType(str, Enum):
    """Type of follow-up interaction."""
    CHECK_IN = "check_in"
    PROGRESS_UPDATE = "progress_update"
    COMPLETION_PROMPT = "completion_prompt"
    CLARIFICATION = "clarification"


class FollowupStatus(str, Enum):
    """Status of a follow-up."""
    PENDING = "pending"
    DELIVERED = "delivered"
    RESPONDED = "responded"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class ReminderPriority(str, Enum):
    """Priority level for reminders."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ReminderStatus(str, Enum):
    """Status of a reminder."""
    PENDING = "pending"
    DELIVERED = "delivered"
    SNOOZED = "snoozed"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


@dataclass
class Followup:
    """Follow-up interaction."""
    followup_id: str
    user_id: str
    goal_id: Optional[str]
    related_message_id: Optional[str]
    followup_type: FollowupType
    content: str
    scheduled_at: datetime
    delivered_at: Optional[datetime]
    user_response: Optional[str]
    response_sentiment: Optional[float]
    status: FollowupStatus
    priority: int
    policy_approved: bool
    relationship_context: Dict[str, Any]
    values_alignment: Optional[float]
    created_at: datetime
    updated_at: datetime


@dataclass
class Reminder:
    """Smart reminder."""
    reminder_id: str
    user_id: str
    goal_id: Optional[str]
    title: str
    description: Optional[str]
    scheduled_at: datetime
    delivered_at: Optional[datetime]
    snoozed_until: Optional[datetime]
    snooze_count: int
    status: ReminderStatus
    priority: ReminderPriority
    urgency_score: float
    recurrence_rule: Optional[Dict[str, Any]]
    cluster_id: Optional[str]
    adaptation_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class ReminderCluster:
    """Cluster of related reminders for batching."""
    cluster_id: str
    user_id: str
    cluster_name: Optional[str]
    scheduled_delivery: datetime
    status: str
    reminder_count: int
    created_at: datetime


# ============================================================================
# Follow-up System
# ============================================================================

class FollowupSystem:
    """
    Policy-aware follow-up generation system.
    
    Generates contextual follow-ups based on:
    - Policy rules (consent, timing, frequency)
    - Relationship strength and interaction history
    - User values alignment
    - Goal progress and context
    """
    
    def __init__(
        self,
        db: EncryptedLibSQLConnection,
        policy_service=None,
        values_service=None,
        logger=None
    ):
        self.db = db
        self.policy_service = policy_service
        self.values_service = values_service
        self.logger = logger
    
    def create_followup(
        self,
        user_id: str,
        followup_type: FollowupType,
        content: str,
        scheduled_at: datetime,
        goal_id: Optional[str] = None,
        related_message_id: Optional[str] = None,
        priority: int = 50,
        relationship_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new follow-up.
        
        Args:
            user_id: User ID
            followup_type: Type of follow-up
            content: Follow-up content
            scheduled_at: When to deliver
            goal_id: Optional related goal
            related_message_id: Optional related message
            priority: Priority (0-100)
            relationship_context: Relationship data
            
        Returns:
            followup_id
        """
        followup_id = str(uuid.uuid4())
        relationship_context = relationship_context or {}
        
        # Check policy approval
        policy_approved = self._check_policy_approval(
            user_id, followup_type, scheduled_at
        )
        
        # Calculate values alignment if values_service available
        values_alignment = None
        if self.values_service and goal_id:
            values_alignment = self._calculate_values_alignment(user_id, goal_id)
        
        try:
            self.db.execute(
                """
                INSERT INTO agency_followups (
                    followup_id, user_id, goal_id, related_message_id,
                    followup_type, content, scheduled_at, status, priority,
                    policy_approved, relationship_context, values_alignment,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    followup_id,
                    user_id,
                    goal_id,
                    related_message_id,
                    followup_type.value,
                    content,
                    scheduled_at.isoformat(),
                    FollowupStatus.PENDING.value,
                    priority,
                    1 if policy_approved else 0,
                    json.dumps(relationship_context),
                    values_alignment,
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat()
                )
            )
            self.db.commit()
            
            if self.logger:
                self.logger.info(
                    f"[FOLLOWUP] Created {followup_type.value} for user {user_id} "
                    f"(scheduled: {scheduled_at.isoformat()})"
                )
            
            return followup_id
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FOLLOWUP] Failed to create follow-up: {e}")
            raise
    
    def _check_policy_approval(
        self,
        user_id: str,
        followup_type: FollowupType,
        scheduled_at: datetime
    ) -> bool:
        """Check if follow-up is approved by policies."""
        # Get user preferences
        prefs = self._get_user_preferences(user_id)
        
        if not prefs.get("followup_enabled", True):
            return False
        
        # Check daily limit
        today_count = self._count_todays_followups(user_id)
        if today_count >= prefs.get("max_followups_per_day", 3):
            return False
        
        # Check minimum time between follow-ups
        last_followup = self._get_last_followup_time(user_id)
        if last_followup:
            min_hours = prefs.get("min_hours_between_followups", 4)
            if (scheduled_at - last_followup).total_seconds() < min_hours * 3600:
                return False
        
        return True
    
    def _calculate_values_alignment(self, user_id: str, goal_id: str) -> float:
        """Calculate how well follow-up aligns with user values."""
        if not self.values_service:
            return 0.5
        
        try:
            # Get goal values alignment from values service
            # This would integrate with the existing values_ethics service
            return 0.7  # Placeholder
        except Exception:
            return 0.5
    
    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user proactive preferences."""
        try:
            row = self.db.fetch_one(
                "SELECT * FROM user_proactive_preferences WHERE user_id = ?",
                (user_id,)
            )
            
            if row:
                return dict(row)
            
            # Return defaults
            return {
                "followup_enabled": True,
                "max_followups_per_day": 3,
                "min_hours_between_followups": 4
            }
            
        except Exception:
            return {}
    
    def _count_todays_followups(self, user_id: str) -> int:
        """Count follow-ups delivered today."""
        try:
            today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            
            row = self.db.fetch_one(
                """
                SELECT COUNT(*) as count FROM agency_followups
                WHERE user_id = ? AND delivered_at >= ?
                """,
                (user_id, today_start.isoformat())
            )
            
            return row["count"] if row else 0
            
        except Exception:
            return 0
    
    def _get_last_followup_time(self, user_id: str) -> Optional[datetime]:
        """Get time of last delivered follow-up."""
        try:
            row = self.db.fetch_one(
                """
                SELECT delivered_at FROM agency_followups
                WHERE user_id = ? AND delivered_at IS NOT NULL
                ORDER BY delivered_at DESC LIMIT 1
                """,
                (user_id,)
            )
            
            if row and row["delivered_at"]:
                return datetime.fromisoformat(row["delivered_at"]).replace(tzinfo=UTC)
            
            return None
            
        except Exception:
            return None
    
    def get_pending_followups(
        self,
        user_id: str,
        before: Optional[datetime] = None
    ) -> List[Followup]:
        """Get pending follow-ups ready for delivery."""
        before = before or datetime.now(UTC)
        
        try:
            rows = self.db.fetch_all(
                """
                SELECT * FROM agency_followups
                WHERE user_id = ? AND status = ? AND scheduled_at <= ?
                  AND policy_approved = 1
                ORDER BY priority DESC, scheduled_at ASC
                """,
                (user_id, FollowupStatus.PENDING.value, before.isoformat())
            )
            
            return [self._row_to_followup(row) for row in rows]
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FOLLOWUP] Failed to get pending follow-ups: {e}")
            return []
    
    def mark_delivered(
        self,
        followup_id: str,
        delivered_at: Optional[datetime] = None
    ) -> None:
        """Mark follow-up as delivered."""
        delivered_at = delivered_at or datetime.now(UTC)
        
        try:
            self.db.execute(
                """
                UPDATE agency_followups
                SET status = ?, delivered_at = ?, updated_at = ?
                WHERE followup_id = ?
                """,
                (
                    FollowupStatus.DELIVERED.value,
                    delivered_at.isoformat(),
                    datetime.now(UTC).isoformat(),
                    followup_id
                )
            )
            self.db.commit()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FOLLOWUP] Failed to mark delivered: {e}")
            raise
    
    def record_response(
        self,
        followup_id: str,
        response: str,
        sentiment: Optional[float] = None
    ) -> None:
        """Record user response to follow-up."""
        try:
            self.db.execute(
                """
                UPDATE agency_followups
                SET status = ?, user_response = ?, response_sentiment = ?, updated_at = ?
                WHERE followup_id = ?
                """,
                (
                    FollowupStatus.RESPONDED.value,
                    response,
                    sentiment,
                    datetime.now(UTC).isoformat(),
                    followup_id
                )
            )
            self.db.commit()
            
            # Record analytics
            self._record_analytics(followup_id, "responded", sentiment)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FOLLOWUP] Failed to record response: {e}")
            raise
    
    def _row_to_followup(self, row: Dict[str, Any]) -> Followup:
        """Convert database row to Followup object."""
        return Followup(
            followup_id=row["followup_id"],
            user_id=row["user_id"],
            goal_id=row["goal_id"],
            related_message_id=row["related_message_id"],
            followup_type=FollowupType(row["followup_type"]),
            content=row["content"],
            scheduled_at=datetime.fromisoformat(row["scheduled_at"]).replace(tzinfo=UTC),
            delivered_at=datetime.fromisoformat(row["delivered_at"]).replace(tzinfo=UTC) if row["delivered_at"] else None,
            user_response=row["user_response"],
            response_sentiment=row["response_sentiment"],
            status=FollowupStatus(row["status"]),
            priority=row["priority"],
            policy_approved=bool(row["policy_approved"]),
            relationship_context=json.loads(row["relationship_context"]) if row["relationship_context"] else {},
            values_alignment=row["values_alignment"],
            created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
            updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC)
        )
    
    def _record_analytics(
        self,
        followup_id: str,
        action: str,
        sentiment: Optional[float] = None
    ) -> None:
        """Record analytics for follow-up interaction."""
        try:
            # Get followup details
            row = self.db.fetch_one(
                "SELECT user_id, delivered_at FROM agency_followups WHERE followup_id = ?",
                (followup_id,)
            )
            
            if not row:
                return
            
            analytics_id = str(uuid.uuid4())
            
            self.db.execute(
                """
                INSERT INTO proactive_analytics (
                    analytics_id, user_id, behavior_type, item_id,
                    delivered_at, user_action, sentiment_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analytics_id,
                    row["user_id"],
                    "followup",
                    followup_id,
                    row["delivered_at"] or datetime.now(UTC).isoformat(),
                    action,
                    sentiment,
                    datetime.now(UTC).isoformat()
                )
            )
            self.db.commit()
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[FOLLOWUP] Failed to record analytics: {e}")


# ============================================================================
# Reminder System
# ============================================================================

class ReminderSystem:
    """
    Smart reminder scheduling system.
    
    Features:
    - Intelligent scheduling based on user patterns
    - Clustering and batching of related reminders
    - Priority and urgency calculation
    - Adaptation based on user response
    - Recurrence support
    """
    
    def __init__(
        self,
        db: EncryptedLibSQLConnection,
        logger=None
    ):
        self.db = db
        self.logger = logger
    
    def create_reminder(
        self,
        user_id: str,
        title: str,
        scheduled_at: datetime,
        description: Optional[str] = None,
        goal_id: Optional[str] = None,
        priority: ReminderPriority = ReminderPriority.NORMAL,
        recurrence_rule: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new reminder.
        
        Args:
            user_id: User ID
            title: Reminder title
            scheduled_at: When to deliver
            description: Optional description
            goal_id: Optional related goal
            priority: Priority level
            recurrence_rule: Optional recurrence pattern
            
        Returns:
            reminder_id
        """
        reminder_id = str(uuid.uuid4())
        
        # Calculate urgency score
        urgency_score = self._calculate_urgency(scheduled_at, priority)
        
        # Check if should cluster
        cluster_id = self._find_or_create_cluster(user_id, scheduled_at)
        
        try:
            self.db.execute(
                """
                INSERT INTO agency_reminders (
                    reminder_id, user_id, goal_id, title, description,
                    scheduled_at, status, priority, urgency_score,
                    recurrence_rule, cluster_id, adaptation_data,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reminder_id,
                    user_id,
                    goal_id,
                    title,
                    description,
                    scheduled_at.isoformat(),
                    ReminderStatus.PENDING.value,
                    priority.value,
                    urgency_score,
                    json.dumps(recurrence_rule) if recurrence_rule else None,
                    cluster_id,
                    json.dumps({}),
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat()
                )
            )
            self.db.commit()
            
            # Update cluster count
            if cluster_id:
                self._update_cluster_count(cluster_id)
            
            if self.logger:
                self.logger.info(
                    f"[REMINDER] Created '{title}' for user {user_id} "
                    f"(scheduled: {scheduled_at.isoformat()}, priority: {priority.value})"
                )
            
            return reminder_id
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[REMINDER] Failed to create reminder: {e}")
            raise
    
    def _calculate_urgency(
        self,
        scheduled_at: datetime,
        priority: ReminderPriority
    ) -> float:
        """Calculate urgency score based on time and priority."""
        # Base score from priority
        priority_scores = {
            ReminderPriority.LOW: 0.25,
            ReminderPriority.NORMAL: 0.5,
            ReminderPriority.HIGH: 0.75,
            ReminderPriority.URGENT: 1.0
        }
        base_score = priority_scores.get(priority, 0.5)
        
        # Adjust based on time until delivery
        time_until = (scheduled_at - datetime.now(UTC)).total_seconds() / 3600  # hours
        
        if time_until < 1:  # Less than 1 hour
            time_multiplier = 1.5
        elif time_until < 24:  # Less than 1 day
            time_multiplier = 1.2
        elif time_until < 168:  # Less than 1 week
            time_multiplier = 1.0
        else:
            time_multiplier = 0.8
        
        return min(1.0, base_score * time_multiplier)
    
    def _find_or_create_cluster(
        self,
        user_id: str,
        scheduled_at: datetime
    ) -> Optional[str]:
        """Find existing cluster or create new one for batching."""
        # Get user preferences
        prefs = self._get_user_preferences(user_id)
        
        if not prefs.get("cluster_reminders", True):
            return None
        
        # Look for cluster within 30 minutes of scheduled time
        window_start = scheduled_at - timedelta(minutes=15)
        window_end = scheduled_at + timedelta(minutes=15)
        
        try:
            row = self.db.fetch_one(
                """
                SELECT cluster_id FROM reminder_clusters
                WHERE user_id = ? AND status = 'pending'
                  AND scheduled_delivery >= ? AND scheduled_delivery <= ?
                ORDER BY scheduled_delivery ASC LIMIT 1
                """,
                (user_id, window_start.isoformat(), window_end.isoformat())
            )
            
            if row:
                return row["cluster_id"]
            
            # Create new cluster
            cluster_id = str(uuid.uuid4())
            self.db.execute(
                """
                INSERT INTO reminder_clusters (
                    cluster_id, user_id, scheduled_delivery, status,
                    reminder_count, created_at
                ) VALUES (?, ?, ?, ?, 0, ?)
                """,
                (
                    cluster_id,
                    user_id,
                    scheduled_at.isoformat(),
                    "pending",
                    datetime.now(UTC).isoformat()
                )
            )
            self.db.commit()
            
            return cluster_id
            
        except Exception:
            return None
    
    def _update_cluster_count(self, cluster_id: str) -> None:
        """Update reminder count in cluster."""
        try:
            self.db.execute(
                """
                UPDATE reminder_clusters
                SET reminder_count = (
                    SELECT COUNT(*) FROM agency_reminders
                    WHERE cluster_id = ?
                )
                WHERE cluster_id = ?
                """,
                (cluster_id, cluster_id)
            )
            self.db.commit()
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[REMINDER] Failed to update cluster count: {e}")
    
    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user proactive preferences."""
        try:
            row = self.db.fetch_one(
                "SELECT * FROM user_proactive_preferences WHERE user_id = ?",
                (user_id,)
            )
            
            if row:
                return dict(row)
            
            return {
                "reminder_enabled": True,
                "cluster_reminders": True,
                "max_reminders_per_day": 5,
                "auto_snooze_duration_minutes": 60
            }
            
        except Exception:
            return {}
    
    def get_pending_reminders(
        self,
        user_id: str,
        before: Optional[datetime] = None
    ) -> List[Reminder]:
        """Get pending reminders ready for delivery."""
        before = before or datetime.now(UTC)
        
        try:
            rows = self.db.fetch_all(
                """
                SELECT * FROM agency_reminders
                WHERE user_id = ? AND status = ? AND scheduled_at <= ?
                ORDER BY urgency_score DESC, scheduled_at ASC
                """,
                (user_id, ReminderStatus.PENDING.value, before.isoformat())
            )
            
            return [self._row_to_reminder(row) for row in rows]
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[REMINDER] Failed to get pending reminders: {e}")
            return []
    
    def get_clustered_reminders(
        self,
        user_id: str,
        cluster_id: str
    ) -> List[Reminder]:
        """Get all reminders in a cluster."""
        try:
            rows = self.db.fetch_all(
                """
                SELECT * FROM agency_reminders
                WHERE user_id = ? AND cluster_id = ? AND status = ?
                ORDER BY urgency_score DESC
                """,
                (user_id, cluster_id, ReminderStatus.PENDING.value)
            )
            
            return [self._row_to_reminder(row) for row in rows]
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[REMINDER] Failed to get clustered reminders: {e}")
            return []
    
    def snooze_reminder(
        self,
        reminder_id: str,
        snooze_minutes: Optional[int] = None
    ) -> None:
        """Snooze a reminder."""
        # Get user preferences for default snooze duration
        try:
            row = self.db.fetch_one(
                "SELECT user_id FROM agency_reminders WHERE reminder_id = ?",
                (reminder_id,)
            )
            
            if not row:
                return
            
            prefs = self._get_user_preferences(row["user_id"])
            snooze_minutes = snooze_minutes or prefs.get("auto_snooze_duration_minutes", 60)
            
            snoozed_until = datetime.now(UTC) + timedelta(minutes=snooze_minutes)
            
            self.db.execute(
                """
                UPDATE agency_reminders
                SET status = ?, snoozed_until = ?, snooze_count = snooze_count + 1,
                    updated_at = ?
                WHERE reminder_id = ?
                """,
                (
                    ReminderStatus.SNOOZED.value,
                    snoozed_until.isoformat(),
                    datetime.now(UTC).isoformat(),
                    reminder_id
                )
            )
            self.db.commit()
            
            # Record analytics
            self._record_analytics(reminder_id, "snoozed")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[REMINDER] Failed to snooze reminder: {e}")
            raise
    
    def complete_reminder(self, reminder_id: str) -> None:
        """Mark reminder as completed."""
        try:
            self.db.execute(
                """
                UPDATE agency_reminders
                SET status = ?, updated_at = ?
                WHERE reminder_id = ?
                """,
                (
                    ReminderStatus.COMPLETED.value,
                    datetime.now(UTC).isoformat(),
                    reminder_id
                )
            )
            self.db.commit()
            
            # Record analytics
            self._record_analytics(reminder_id, "completed")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[REMINDER] Failed to complete reminder: {e}")
            raise
    
    def _row_to_reminder(self, row: Dict[str, Any]) -> Reminder:
        """Convert database row to Reminder object."""
        return Reminder(
            reminder_id=row["reminder_id"],
            user_id=row["user_id"],
            goal_id=row["goal_id"],
            title=row["title"],
            description=row["description"],
            scheduled_at=datetime.fromisoformat(row["scheduled_at"]).replace(tzinfo=UTC),
            delivered_at=datetime.fromisoformat(row["delivered_at"]).replace(tzinfo=UTC) if row["delivered_at"] else None,
            snoozed_until=datetime.fromisoformat(row["snoozed_until"]).replace(tzinfo=UTC) if row["snoozed_until"] else None,
            snooze_count=row["snooze_count"],
            status=ReminderStatus(row["status"]),
            priority=ReminderPriority(row["priority"]),
            urgency_score=row["urgency_score"],
            recurrence_rule=json.loads(row["recurrence_rule"]) if row["recurrence_rule"] else None,
            cluster_id=row["cluster_id"],
            adaptation_data=json.loads(row["adaptation_data"]) if row["adaptation_data"] else {},
            created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
            updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC)
        )
    
    def _record_analytics(self, reminder_id: str, action: str) -> None:
        """Record analytics for reminder interaction."""
        try:
            row = self.db.fetch_one(
                "SELECT user_id, delivered_at FROM agency_reminders WHERE reminder_id = ?",
                (reminder_id,)
            )
            
            if not row:
                return
            
            analytics_id = str(uuid.uuid4())
            
            self.db.execute(
                """
                INSERT INTO proactive_analytics (
                    analytics_id, user_id, behavior_type, item_id,
                    delivered_at, user_action, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analytics_id,
                    row["user_id"],
                    "reminder",
                    reminder_id,
                    row["delivered_at"] or datetime.now(UTC).isoformat(),
                    action,
                    datetime.now(UTC).isoformat()
                )
            )
            self.db.commit()
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[REMINDER] Failed to record analytics: {e}")
