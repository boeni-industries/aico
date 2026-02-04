"""
Coverage tests for proactive.py - targeting uncovered lines.

Focuses on error handling, edge cases, and conditional branches.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch
import json

from aico.ai.agency.proactive import (
    FollowupSystem,
    ReminderSystem,
    FollowupType,
    FollowupStatus,
    ReminderPriority,
    ReminderStatus
)


class _DB:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=None):
        q = query.replace("?", "%s")
        cur = self._conn.cursor()
        try:
            cur.execute(q, params or ())
            return cur
        except Exception:
            try:
                self._conn.rollback()
            except Exception:
                pass
            cur.close()
            raise

    def fetch_one(self, query, params=None):
        cur = self.execute(query, params)
        try:
            return cur.fetchone()
        finally:
            cur.close()

    def fetch_all(self, query, params=None):
        cur = self.execute(query, params)
        try:
            return cur.fetchall()
        finally:
            cur.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()


class TestFollowupSystemCoverage:
    """Tests targeting uncovered lines in FollowupSystem."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return _DB(test_db)
    
    @pytest.fixture
    def followup_system(self, db):
        """Create followup system with logger."""
        logger = Mock()
        return FollowupSystem(db, logger=logger)
    
    @pytest.fixture
    def test_goal_id(self, db, test_user):
        """Create a test goal."""
        goal_id = "test-goal-coverage-1"
        db.execute(
            """INSERT INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (goal_id) DO NOTHING""",
            (goal_id, test_user, "user", "work", "Test goal", "Test", "normal", "active",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        return goal_id
    
    # ========================================================================
    # Create Followup Tests
    # ========================================================================
    
    def test_create_followup_without_goal(self, followup_system, test_user):
        """Test creating followup without goal_id (covers optional parameter)."""
        scheduled_at = datetime.now(UTC) + timedelta(hours=2)
        
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CHECK_IN,
            content="General check-in",
            scheduled_at=scheduled_at,
            goal_id=None
        )
        
        row = followup_system.db.fetch_one(
            "SELECT * FROM agency_followups WHERE followup_id = ?",
            (followup_id,)
        )
        
        assert row["goal_id"] is None
    
    def test_create_followup_with_relationship_context(self, followup_system, test_user):
        """Test creating followup with relationship context."""
        scheduled_at = datetime.now(UTC) + timedelta(hours=2)
        relationship_context = {"context": "test", "source": "automated"}
        
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.PROGRESS_UPDATE,
            content="Update please",
            scheduled_at=scheduled_at,
            relationship_context=relationship_context
        )
        
        row = followup_system.db.fetch_one(
            "SELECT * FROM agency_followups WHERE followup_id = ?",
            (followup_id,)
        )
        
        stored_context = json.loads(row["relationship_context"]) if row["relationship_context"] else {}
        assert stored_context == relationship_context
    
    def test_create_followup_database_error(self, followup_system, test_user, db):
        """Test error handling when creating followup fails."""
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                followup_system.create_followup(
                    user_id=test_user,
                    followup_type=FollowupType.CHECK_IN,
                    content="Test",
                    scheduled_at=datetime.now(UTC)
                )
            
            assert followup_system.logger.error.called
    
    def test_create_followup_logging(self, followup_system, test_user):
        """Test that followup creation logs info message."""
        scheduled_at = datetime.now(UTC) + timedelta(hours=2)
        
        followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CHECK_IN,
            content="Test",
            scheduled_at=scheduled_at
        )
        
        assert followup_system.logger.info.called
    
    # ========================================================================
    # Get Pending Followups Tests
    # ========================================================================
    
    def test_get_pending_followups_before_time(self, followup_system, test_user):
        """Test getting pending followups before specific time."""
        now = datetime.now(UTC)
        
        # Create followups at different times
        for i in range(3):
            followup_system.create_followup(
                user_id=test_user,
                followup_type=FollowupType.CHECK_IN,
                content=f"Followup {i}",
                scheduled_at=now - timedelta(hours=i+1)
            )
        
        # Get pending before now
        pending = followup_system.get_pending_followups(test_user, before=now)
        
        assert len(pending) >= 1
    
    def test_get_pending_followups_database_error(self, followup_system, test_user, db):
        """Test error handling when fetching followups fails."""
        with patch.object(db, 'fetch_all', side_effect=Exception("DB error")):
            pending = followup_system.get_pending_followups(test_user)
            
            assert pending == []
            assert followup_system.logger.error.called
    
    # ========================================================================
    # Mark Delivered Tests
    # ========================================================================
    
    def test_mark_delivered_database_error(self, followup_system, test_user, db):
        """Test error handling when marking delivered fails."""
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CHECK_IN,
            content="Test",
            scheduled_at=datetime.now(UTC)
        )
        
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                followup_system.mark_delivered(followup_id)
            
            assert followup_system.logger.error.called
    
    # ========================================================================
    # Record Response Tests
    # ========================================================================
    
    def test_record_response_without_sentiment(self, followup_system, test_user):
        """Test recording response without sentiment (covers optional parameter)."""
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CLARIFICATION,
            content="Clarify please",
            scheduled_at=datetime.now(UTC)
        )
        
        followup_system.mark_delivered(followup_id)
        followup_system.record_response(
            followup_id=followup_id,
            response="Here's the clarification",
            sentiment=None
        )
        
        row = followup_system.db.fetch_one(
            "SELECT * FROM agency_followups WHERE followup_id = ?",
            (followup_id,)
        )
        
        assert row["status"] == "responded"
        assert row["response_sentiment"] is None
    
    def test_record_response_database_error(self, followup_system, test_user, db):
        """Test error handling when recording response fails."""
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CHECK_IN,
            content="Test",
            scheduled_at=datetime.now(UTC)
        )
        
        followup_system.mark_delivered(followup_id)
        
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                followup_system.record_response(followup_id, "Response")
            
            assert followup_system.logger.error.called
    
    # ========================================================================
    # Policy Approval Tests
    # ========================================================================
    
    def test_policy_approval_disabled_followups(self, followup_system, test_user, db):
        """Test that policy approval is checked during followup creation."""
        # Disable followups
        db.execute(
            """INSERT INTO user_proactive_preferences 
               (user_id, followup_enabled, updated_at)
               VALUES (?, FALSE, ?)
               ON CONFLICT (user_id) DO UPDATE SET
                   followup_enabled = EXCLUDED.followup_enabled,
                   updated_at = EXCLUDED.updated_at""",
            (test_user, datetime.now(UTC).isoformat())
        )
        db.commit()
        
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CHECK_IN,
            content="Test",
            scheduled_at=datetime.now(UTC)
        )
        
        row = followup_system.db.fetch_one(
            "SELECT policy_approved FROM agency_followups WHERE followup_id = ?",
            (followup_id,)
        )
        
        # Should be marked as not approved
        assert row["policy_approved"] == 0
    
    # ========================================================================
    # Values Alignment Tests
    # ========================================================================
    
    def test_create_followup_without_values_service(self, db, test_user, test_goal_id):
        """Test creating followup when values_service is None."""
        # Create followup system without values_service
        followup_system = FollowupSystem(db, values_service=None)
        
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CHECK_IN,
            content="Test",
            scheduled_at=datetime.now(UTC),
            goal_id=test_goal_id
        )
        
        row = followup_system.db.fetch_one(
            "SELECT values_alignment FROM agency_followups WHERE followup_id = ?",
            (followup_id,)
        )
        
        # Should be None when values_service not available
        assert row["values_alignment"] is None


class TestReminderSystemCoverage:
    """Tests targeting uncovered lines in ReminderSystem."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return _DB(test_db)
    
    @pytest.fixture
    def reminder_system(self, db):
        """Create reminder system with logger."""
        logger = Mock()
        return ReminderSystem(db, logger=logger)
    
    @pytest.fixture
    def test_goal_id(self, db, test_user):
        """Create a test goal."""
        goal_id = "test-goal-reminder-coverage-1"
        db.execute(
            """INSERT INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (goal_id) DO NOTHING""",
            (goal_id, test_user, "user", "work", "Test goal", "Test", "normal", "active",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        db.commit()
        return goal_id
    
    # ========================================================================
    # Create Reminder Tests
    # ========================================================================
    
    def test_create_reminder_without_description(self, reminder_system, test_user):
        """Test creating reminder without description (covers optional parameter)."""
        scheduled_at = datetime.now(UTC) + timedelta(hours=2)
        
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Simple reminder",
            scheduled_at=scheduled_at,
            description=None
        )
        
        row = reminder_system.db.fetch_one(
            "SELECT * FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id,)
        )
        
        assert row["description"] is None
    
    def test_create_reminder_without_goal(self, reminder_system, test_user):
        """Test creating reminder without goal_id."""
        scheduled_at = datetime.now(UTC) + timedelta(hours=2)
        
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="General reminder",
            scheduled_at=scheduled_at,
            goal_id=None
        )
        
        row = reminder_system.db.fetch_one(
            "SELECT * FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id,)
        )
        
        assert row["goal_id"] is None
    
    def test_create_reminder_with_priority(self, reminder_system, test_user):
        """Test creating reminder with explicit priority."""
        scheduled_at = datetime.now(UTC) + timedelta(hours=2)
        
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="High priority",
            scheduled_at=scheduled_at,
            priority=ReminderPriority.HIGH
        )
        
        row = reminder_system.db.fetch_one(
            "SELECT * FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id,)
        )
        
        assert row["priority"] == "high"
    
    def test_create_reminder_with_recurrence_rule(self, reminder_system, test_user):
        """Test creating reminder with recurrence rule."""
        scheduled_at = datetime.now(UTC) + timedelta(hours=2)
        recurrence_rule = {"frequency": "daily", "interval": 1}
        
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Recurring reminder",
            scheduled_at=scheduled_at,
            recurrence_rule=recurrence_rule
        )
        
        row = reminder_system.db.fetch_one(
            "SELECT * FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id,)
        )
        
        stored_rule = json.loads(row["recurrence_rule"]) if row["recurrence_rule"] else None
        assert stored_rule == recurrence_rule
    
    def test_create_reminder_database_error(self, reminder_system, test_user, db):
        """Test error handling when creating reminder fails."""
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                reminder_system.create_reminder(
                    user_id=test_user,
                    title="Test",
                    scheduled_at=datetime.now(UTC)
                )
            
            assert reminder_system.logger.error.called
    
    def test_create_reminder_logging(self, reminder_system, test_user):
        """Test that reminder creation logs info message."""
        scheduled_at = datetime.now(UTC) + timedelta(hours=2)
        
        reminder_system.create_reminder(
            user_id=test_user,
            title="Test",
            scheduled_at=scheduled_at
        )
        
        assert reminder_system.logger.info.called
    
    # ========================================================================
    # Urgency Calculation Tests
    # ========================================================================
    
    def test_calculate_urgency_overdue(self, reminder_system):
        """Test urgency calculation for overdue reminder."""
        scheduled_at = datetime.now(UTC) - timedelta(hours=2)
        
        urgency = reminder_system._calculate_urgency(
            scheduled_at=scheduled_at,
            priority=ReminderPriority.HIGH
        )
        
        # Overdue should have high urgency
        assert urgency > 0.8
    
    def test_calculate_urgency_far_future(self, reminder_system):
        """Test urgency calculation for far future reminder."""
        scheduled_at = datetime.now(UTC) + timedelta(days=30)
        
        urgency = reminder_system._calculate_urgency(
            scheduled_at=scheduled_at,
            priority=ReminderPriority.LOW
        )
        
        # Far future + low priority should have low urgency
        assert urgency < 0.3
    
    # ========================================================================
    # Get Pending Reminders Tests
    # ========================================================================
    
    def test_get_pending_reminders_before_time(self, reminder_system, test_user):
        """Test getting pending reminders before specific time."""
        now = datetime.now(UTC)
        
        # Create reminders at different times
        for i in range(3):
            reminder_system.create_reminder(
                user_id=test_user,
                title=f"Reminder {i}",
                scheduled_at=now - timedelta(hours=i+1)
            )
        
        # Get pending before now
        pending = reminder_system.get_pending_reminders(test_user, before=now)
        
        assert len(pending) >= 1
    
    def test_get_pending_reminders_excludes_snoozed(self, reminder_system, test_user):
        """Test that snoozed reminders are excluded from pending."""
        now = datetime.now(UTC)
        
        # Create and snooze a reminder
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Snoozed",
            scheduled_at=now - timedelta(hours=1)
        )
        reminder_system.snooze_reminder(reminder_id, snooze_minutes=60)
        
        # Get pending
        pending = reminder_system.get_pending_reminders(test_user)
        
        # Snoozed reminder should not be in pending
        pending_ids = [r.reminder_id for r in pending]
        assert reminder_id not in pending_ids
    
    def test_get_pending_reminders_database_error(self, reminder_system, test_user, db):
        """Test error handling when fetching reminders fails."""
        with patch.object(db, 'fetch_all', side_effect=Exception("DB error")):
            pending = reminder_system.get_pending_reminders(test_user)
            
            assert pending == []
            assert reminder_system.logger.error.called
    
    # ========================================================================
    # Snooze Reminder Tests
    # ========================================================================
    
    def test_snooze_reminder_multiple_times(self, reminder_system, test_user):
        """Test snoozing reminder multiple times increments count."""
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Multi-snooze",
            scheduled_at=datetime.now(UTC)
        )
        
        # Snooze twice
        reminder_system.snooze_reminder(reminder_id, snooze_minutes=30)
        reminder_system.snooze_reminder(reminder_id, snooze_minutes=30)
        
        row = reminder_system.db.fetch_one(
            "SELECT snooze_count FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id,)
        )
        
        assert row["snooze_count"] >= 2
    
    def test_snooze_reminder_database_error(self, reminder_system, test_user, db):
        """Test error handling when snoozing reminder fails."""
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Test",
            scheduled_at=datetime.now(UTC)
        )
        
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                reminder_system.snooze_reminder(reminder_id)
            
            assert reminder_system.logger.error.called
    
    # ========================================================================
    # Complete Reminder Tests
    # ========================================================================
    
    def test_complete_reminder_database_error(self, reminder_system, test_user, db):
        """Test error handling when completing reminder fails."""
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Test",
            scheduled_at=datetime.now(UTC)
        )
        
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                reminder_system.complete_reminder(reminder_id)
            
            assert reminder_system.logger.error.called
    
    # ========================================================================
    # Clustering Tests
    # ========================================================================
    
    def test_clustering_respects_user_preferences(self, reminder_system, test_user, db):
        """Test that clustering respects user preferences."""
        # Disable clustering
        db.execute(
            """INSERT INTO user_proactive_preferences 
               (user_id, cluster_reminders, updated_at)
               VALUES (?, 0, ?)
               ON CONFLICT (user_id) DO UPDATE SET
                   cluster_reminders = EXCLUDED.cluster_reminders,
                   updated_at = EXCLUDED.updated_at""",
            (test_user, datetime.now(UTC).isoformat())
        )
        db.commit()
        
        # Create reminder
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="No cluster",
            scheduled_at=datetime.now(UTC) + timedelta(hours=2)
        )
        
        row = reminder_system.db.fetch_one(
            "SELECT cluster_id FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id,)
        )
        
        # Should not be clustered when disabled
        assert row["cluster_id"] is None
    
    def test_get_clustered_reminders_database_error(self, reminder_system, test_user, db):
        """Test error handling when fetching clustered reminders fails."""
        with patch.object(db, 'fetch_all', side_effect=Exception("DB error")):
            clustered = reminder_system.get_clustered_reminders(test_user, "cluster-id")
            
            assert clustered == []
            assert reminder_system.logger.error.called
    
    # ========================================================================
    # Adaptation Data Tests
    # ========================================================================
    
    def test_create_reminder_with_adaptation_data(self, reminder_system, test_user):
        """Test that reminders are created with adaptation data."""
        scheduled_at = datetime.now(UTC) + timedelta(hours=2)
        
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Adaptive reminder",
            scheduled_at=scheduled_at
        )
        
        row = reminder_system.db.fetch_one(
            "SELECT adaptation_data FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id,)
        )
        
        # Should have adaptation data (even if empty dict)
        adaptation_data = json.loads(row["adaptation_data"]) if row["adaptation_data"] else {}
        assert isinstance(adaptation_data, dict)
