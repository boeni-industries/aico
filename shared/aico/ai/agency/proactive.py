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
from sqlalchemy.ext.asyncio import async_sessionmaker

from aico.data.uow import UnitOfWork



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
        session_factory: async_sessionmaker,
        policy_service=None,
        values_service=None,
        logger=None
    ):
        self.session_factory = session_factory
        self.policy_service = policy_service
        self.values_service = values_service
        self.logger = logger
    
    async def create_followup(
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
            async with UnitOfWork(self.session_factory) as uow:
                from aico.ai.agency.models import AgencyFollowup
                
                followup = AgencyFollowup(
                    followup_id=followup_id,
                    user_id=user_id,
                    goal_id=goal_id,
                    related_message_id=related_message_id,
                    followup_type=followup_type.value,
                    content=content,
                    scheduled_at=scheduled_at,
                    status=FollowupStatus.PENDING.value,
                    priority=priority,
                    policy_approved=policy_approved,
                    relationship_context=relationship_context,
                    values_alignment=values_alignment,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                await uow.agency_followups.create(followup)
                await uow.commit()
            
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
        """Get user proactive preferences - legacy method, returns defaults."""
        return {
            "followup_enabled": True,
            "max_followups_per_day": 3,
            "min_hours_between_followups": 4
        }
    
    async def _check_followup_frequency(
        self,
        user_id: str,
        max_per_day: int = 3
    ) -> bool:
        """Check if user hasn't exceeded daily follow-up limit."""
        try:
            today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            
            async with UnitOfWork(self.session_factory) as uow:
                count = await uow.agency_followups.count_delivered_since(
                    user_id=user_id,
                    since=today_start
                )
                return count < max_per_day
            
        except Exception:
            return True
    
    async def _get_last_followup_time(self, user_id: str) -> Optional[datetime]:
        """Get timestamp of last delivered follow-up."""
        try:
            async with UnitOfWork(self.session_factory) as uow:
                followup = await uow.agency_followups.get_last_delivered(user_id)
                
                if followup and followup.delivered_at:
                    return followup.delivered_at
                
                return None
                
        except Exception:
            return None
    
    async def get_pending_followups(
        self,
        user_id: str,
        before: Optional[datetime] = None
    ) -> List[Followup]:
        """Get pending follow-ups ready for delivery."""
        before = before or datetime.now(UTC)
        
        try:
            async with UnitOfWork(self.session_factory) as uow:
                followups = await uow.agency_followups.get_pending(
                    user_id=user_id,
                    before=before,
                    policy_approved=True
                )
                return followups
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FOLLOWUP] Failed to get pending follow-ups: {e}")
            return []
    
    async def mark_delivered(
        self,
        followup_id: str,
        delivered_at: Optional[datetime] = None
    ) -> None:
        """Mark follow-up as delivered."""
        delivered_at = delivered_at or datetime.now(UTC)
        
        try:
            async with UnitOfWork(self.session_factory) as uow:
                await uow.agency_followups.update_status(
                    followup_id=followup_id,
                    status=FollowupStatus.DELIVERED.value,
                    delivered_at=delivered_at
                )
                await uow.commit()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FOLLOWUP] Failed to mark delivered: {e}")
            raise
    
    async def record_response(
        self,
        followup_id: str,
        response: str,
        sentiment: Optional[float] = None
    ) -> None:
        """Record user response to follow-up."""
        try:
            async with UnitOfWork(self.session_factory) as uow:
                await uow.agency_followups.record_response(
                    followup_id=followup_id,
                    response=response,
                    sentiment=sentiment
                )
                await uow.commit()
            
            # Record analytics
            await self._record_analytics(followup_id, "responded", sentiment)
            
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
            values_alignment=row.get("values_alignment"),
            created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
            updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC)
        )
    
    async def _record_analytics(
        self,
        followup_id: str,
        action: str,
        sentiment: Optional[float] = None
    ) -> None:
        """Record analytics for follow-up action."""
        try:
            async with UnitOfWork(self.session_factory) as uow:
                # Get followup details
                followup = await uow.agency_followups.get_by_id(followup_id)
                
                if not followup:
                    return
                
                from aico.ai.agency.models import ProactiveAnalytic
                
                event_data = {
                    "followup_id": followup_id,
                    "action": action,
                    "delivered_at": followup.delivered_at.isoformat() if followup.delivered_at else datetime.now(UTC).isoformat(),
                }
                if sentiment is not None:
                    event_data["sentiment_score"] = sentiment

                analytic = ProactiveAnalytic(
                    id=str(uuid.uuid4()),
                    user_id=followup.user_id,
                    event_type="followup",
                    event_data=event_data,
                    confidence_score=sentiment,
                    triggered_action=action,
                    created_at=datetime.now(UTC)
                )
                
                await uow.proactive_analytics.create(analytic)
                await uow.commit()
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[FOLLOWUP] Failed to record analytics: {e}")
                return


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
    
    def __init__(self, session_factory: async_sessionmaker, logger=None):
        self.session_factory = session_factory
        self.logger = logger
    
    async def create_reminder(
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
        cluster_id = await self._find_or_create_cluster(user_id, scheduled_at)
        
        try:
            async with UnitOfWork(self.session_factory) as uow:
                from aico.ai.agency.models import AgencyReminder
                
                reminder = AgencyReminder(
                    reminder_id=reminder_id,
                    user_id=user_id,
                    goal_id=goal_id,
                    title=title,
                    description=description,
                    scheduled_at=scheduled_at,
                    status=ReminderStatus.PENDING.value,
                    priority=priority.value,
                    urgency_score=urgency_score,
                    recurrence_rule=recurrence_rule,
                    cluster_id=cluster_id,
                    adaptation_data={},
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                await uow.agency_reminders.create(reminder)
                await uow.commit()
            
            # Update cluster count
            if cluster_id:
                await self._update_cluster_count(cluster_id)
            
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
    
    async def _find_or_create_cluster(
        self,
        user_id: str,
        scheduled_at: datetime
    ) -> Optional[str]:
        """Find existing cluster or create new one for batching."""
        # Get user preferences
        prefs = await self._get_user_preferences(user_id)
        
        if not prefs.get("cluster_reminders", True):
            return None
        
        # Look for cluster within 30 minutes of scheduled time
        window_start = scheduled_at - timedelta(minutes=15)
        window_end = scheduled_at + timedelta(minutes=15)
        
        try:
            async with UnitOfWork(self.session_factory) as uow:
                # Find existing cluster
                cluster = await uow.proactive_reminder_clusters.find_in_window(
                    user_id=user_id,
                    window_start=window_start,
                    window_end=window_end
                )

                if cluster:
                    return cluster.cluster_id

                # Create new cluster
                from aico.ai.agency.models import ProactiveReminderCluster
                
                cluster_id = str(uuid.uuid4())
                new_cluster = ProactiveReminderCluster(
                    cluster_id=cluster_id,
                    user_id=user_id,
                    cluster_name="Auto Cluster",
                    reminder_ids=[],
                    pattern_description=None,
                    confidence_score=None,
                    created_at=datetime.now(UTC)
                )
                
                await uow.proactive_reminder_clusters.create(new_cluster)
                await uow.commit()

                return cluster_id

        except Exception as e:
            if self.logger:
                self.logger.warning(f"[REMINDER] Failed to find/create cluster: {e}")
                return None
    
    async def _update_cluster_count(self, cluster_id: str) -> None:
        """Update reminder list in cluster."""
        try:
            async with UnitOfWork(self.session_factory) as uow:
                # Get all reminders in cluster
                reminders = await uow.agency_reminders.get_by_cluster(cluster_id)
                reminder_ids = [r.reminder_id for r in reminders]

                # Update cluster
                await uow.proactive_reminder_clusters.update_reminder_ids(
                    cluster_id=cluster_id,
                    reminder_ids=reminder_ids
                )
                await uow.commit()
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[REMINDER] Failed to update cluster count: {e}")
    
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user proactive preferences."""
        try:
            async with UnitOfWork(self.session_factory) as uow:
                prefs = await uow.user_proactive_preferences.get_by_user_id(user_id)
                
                if prefs:
                    return {
                        "reminder_enabled": prefs.reminder_enabled,
                        "cluster_reminders": prefs.cluster_reminders,
                        "preferred_times": prefs.preferred_times,
                        "max_daily_reminders": prefs.max_daily_reminders
                    }
                
                return {
                    "reminder_enabled": True,
                "cluster_reminders": True,
                "max_reminders_per_day": 5,
                "auto_snooze_duration_minutes": 60
            }
            
        except Exception:
            return {}
    
    async def get_pending_reminders(
        self,
        user_id: str,
        before: Optional[datetime] = None
    ) -> List[Reminder]:
        """Get pending reminders ready for delivery."""
        before = before or datetime.now(UTC)
        
        try:
            async with UnitOfWork(self.session_factory) as uow:
                reminders = await uow.agency_reminders.get_pending(
                    user_id=user_id,
                    before=before
                )
                return reminders
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"[REMINDER] Failed to get pending reminders: {e}")
            return []
    
    async def get_clustered_reminders(
        self,
        user_id: str,
        cluster_id: str
    ) -> List[Reminder]:
        """Get all reminders in a cluster."""
        try:
            async with UnitOfWork(self.session_factory) as uow:
                reminders = await uow.agency_reminders.get_by_cluster(
                    cluster_id=cluster_id,
                    user_id=user_id,
                    status=ReminderStatus.PENDING.value
                )
                return reminders
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"[REMINDER] Failed to get clustered reminders: {e}")
            return []
    
    async def snooze_reminder(
        self,
        reminder_id: str,
        snooze_minutes: int = 60
    ) -> None:
        """Snooze a reminder for specified duration."""
        try:
            # Validate snooze duration
            if snooze_minutes < 5 or snooze_minutes > 1440:  # 5 min to 24 hours
                raise ValueError("Snooze duration must be between 5 and 1440 minutes")
            
            snoozed_until = datetime.now(UTC) + timedelta(minutes=snooze_minutes)
            
            async with UnitOfWork(self.session_factory) as uow:
                await uow.agency_reminders.snooze(
                    reminder_id=reminder_id,
                    snoozed_until=snoozed_until
                )
                await uow.commit()
            
            # Record analytics
            await self._record_analytics(reminder_id, "snoozed")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[REMINDER] Failed to snooze reminder: {e}")
            raise
    
    async def complete_reminder(self, reminder_id: str) -> None:
        """Mark reminder as completed."""
        try:
            async with UnitOfWork(self.session_factory) as uow:
                await uow.agency_reminders.update_status(
                    reminder_id=reminder_id,
                    status=ReminderStatus.COMPLETED.value
                )
                await uow.commit()
            
            # Record analytics
            await self._record_analytics(reminder_id, "completed")
            
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
    
    async def _record_analytics(self, reminder_id: str, action: str) -> None:
        """Record analytics for reminder interaction."""
        try:
            async with UnitOfWork(self.session_factory) as uow:
                # Get reminder details
                reminder = await uow.agency_reminders.get_by_id(reminder_id)
                
                if not reminder:
                    return
                
                from aico.ai.agency.models import ProactiveAnalytic
                
                event_data = {
                    "reminder_id": reminder_id,
                    "action": action,
                    "delivered_at": reminder.delivered_at.isoformat() if reminder.delivered_at else datetime.now(UTC).isoformat(),
                }

                analytic = ProactiveAnalytic(
                    id=str(uuid.uuid4()),
                    user_id=reminder.user_id,
                    event_type="reminder",
                    event_data=event_data,
                    confidence_score=None,
                    triggered_action=action,
                    created_at=datetime.now(UTC)
                )
                
                await uow.proactive_analytics.create(analytic)
                await uow.commit()
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[REMINDER] Failed to record analytics: {e}")
                return
            raise
