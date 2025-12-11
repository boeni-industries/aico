"""
Comprehensive Tests for Phase 6.7: Proactive Behaviors

Tests follow-up generation, reminder scheduling, clustering, and adaptation.
"""

import pytest
from datetime import datetime, timedelta

from aico.ai.agency.proactive import (
    FollowupSystem,
    ReminderSystem,
    FollowupType,
    FollowupStatus,
    ReminderPriority,
    ReminderStatus
)


# ============================================================================
# FOLLOW-UP SYSTEM TESTS
# ============================================================================

class TestFollowupSystem:
    """Test follow-up generation and management."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def followup_system(self, db):
        """Create followup system."""
        return FollowupSystem(db)
    
    @pytest.fixture
    def test_goal_id(self, db, test_user):
        """Create a test goal."""
        goal_id = "test-goal-followup-1"
        db.execute(
            """INSERT OR IGNORE INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, test_user, "user", "work", "Test goal", "Test", "normal", "active",
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
        )
        db.commit()
        return goal_id
    
    def test_create_followup(self, followup_system, test_user, test_goal_id):
        """Test creating a follow-up."""
        scheduled_at = datetime.utcnow() + timedelta(hours=2)
        
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CHECK_IN,
            content="How is your goal progressing?",
            scheduled_at=scheduled_at,
            goal_id=test_goal_id,
            priority=60
        )
        
        assert followup_id is not None
        assert len(followup_id) > 0
        
        # Verify in database
        row = followup_system.db.fetch_one(
            "SELECT * FROM agency_followups WHERE followup_id = ?",
            (followup_id,)
        )
        
        assert row is not None
        assert row["user_id"] == test_user
        assert row["followup_type"] == "check_in"
        assert row["status"] == "pending"
    
    def test_get_pending_followups(self, followup_system, test_user, test_goal_id):
        """Test retrieving pending follow-ups."""
        # Create multiple follow-ups
        now = datetime.utcnow()
        
        # Past - should be retrieved
        followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CHECK_IN,
            content="Past followup",
            scheduled_at=now - timedelta(hours=1),
            goal_id=test_goal_id
        )
        
        # Future - should not be retrieved
        followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.PROGRESS_UPDATE,
            content="Future followup",
            scheduled_at=now + timedelta(hours=2),
            goal_id=test_goal_id
        )
        
        pending = followup_system.get_pending_followups(test_user)
        
        assert len(pending) >= 1
        assert all(f.scheduled_at <= now for f in pending)
    
    def test_mark_followup_delivered(self, followup_system, test_user):
        """Test marking follow-up as delivered."""
        scheduled_at = datetime.utcnow() - timedelta(hours=1)
        
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.COMPLETION_PROMPT,
            content="Ready to complete?",
            scheduled_at=scheduled_at
        )
        
        followup_system.mark_delivered(followup_id)
        
        row = followup_system.db.fetch_one(
            "SELECT * FROM agency_followups WHERE followup_id = ?",
            (followup_id,)
        )
        
        assert row["status"] == "delivered"
        assert row["delivered_at"] is not None
    
    def test_record_followup_response(self, followup_system, test_user):
        """Test recording user response to follow-up."""
        scheduled_at = datetime.utcnow() - timedelta(hours=1)
        
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CLARIFICATION,
            content="Can you clarify?",
            scheduled_at=scheduled_at
        )
        
        followup_system.mark_delivered(followup_id)
        followup_system.record_response(
            followup_id=followup_id,
            response="Yes, here's more detail...",
            sentiment=0.8
        )
        
        row = followup_system.db.fetch_one(
            "SELECT * FROM agency_followups WHERE followup_id = ?",
            (followup_id,)
        )
        
        assert row["status"] == "responded"
        assert row["user_response"] is not None
        assert row["response_sentiment"] == 0.8
    
    def test_policy_approval_daily_limit(self, followup_system, test_user, db):
        """Test that daily limit is enforced."""
        # Set user preferences with low limit
        db.execute(
            """INSERT OR REPLACE INTO user_proactive_preferences 
               (user_id, followup_enabled, max_followups_per_day, updated_at)
               VALUES (?, 1, 2, ?)""",
            (test_user, datetime.utcnow().isoformat())
        )
        db.commit()
        
        scheduled_at = datetime.utcnow() + timedelta(hours=1)
        
        # Create and deliver 2 follow-ups (at limit)
        for i in range(2):
            fid = followup_system.create_followup(
                user_id=test_user,
                followup_type=FollowupType.CHECK_IN,
                content=f"Followup {i}",
                scheduled_at=scheduled_at
            )
            followup_system.mark_delivered(fid)
        
        # Try to create 3rd - should not be policy approved
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CHECK_IN,
            content="Followup 3",
            scheduled_at=scheduled_at
        )
        
        row = followup_system.db.fetch_one(
            "SELECT * FROM agency_followups WHERE followup_id = ?",
            (followup_id,)
        )
        
        assert row["policy_approved"] == 0


# ============================================================================
# REMINDER SYSTEM TESTS
# ============================================================================

class TestReminderSystem:
    """Test reminder scheduling and management."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def reminder_system(self, db):
        """Create reminder system."""
        return ReminderSystem(db)
    
    @pytest.fixture
    def test_goal_id(self, db, test_user):
        """Create a test goal."""
        goal_id = "test-goal-reminder-1"
        db.execute(
            """INSERT OR IGNORE INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, test_user, "user", "work", "Test goal", "Test", "normal", "active",
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
        )
        db.commit()
        return goal_id
    
    def test_create_reminder(self, reminder_system, test_user, test_goal_id):
        """Test creating a reminder."""
        scheduled_at = datetime.utcnow() + timedelta(hours=3)
        
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Complete task",
            scheduled_at=scheduled_at,
            description="Don't forget to finish this",
            goal_id=test_goal_id,
            priority=ReminderPriority.HIGH
        )
        
        assert reminder_id is not None
        assert len(reminder_id) > 0
        
        # Verify in database
        row = reminder_system.db.fetch_one(
            "SELECT * FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id,)
        )
        
        assert row is not None
        assert row["user_id"] == test_user
        assert row["title"] == "Complete task"
        assert row["priority"] == "high"
        assert row["status"] == "pending"
    
    def test_urgency_calculation(self, reminder_system, test_user):
        """Test urgency score calculation."""
        # Urgent priority + soon
        scheduled_soon = datetime.utcnow() + timedelta(minutes=30)
        reminder_id_urgent = reminder_system.create_reminder(
            user_id=test_user,
            title="Urgent soon",
            scheduled_at=scheduled_soon,
            priority=ReminderPriority.URGENT
        )
        
        # Low priority + far
        scheduled_far = datetime.utcnow() + timedelta(days=7)
        reminder_id_low = reminder_system.create_reminder(
            user_id=test_user,
            title="Low later",
            scheduled_at=scheduled_far,
            priority=ReminderPriority.LOW
        )
        
        row_urgent = reminder_system.db.fetch_one(
            "SELECT urgency_score FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id_urgent,)
        )
        
        row_low = reminder_system.db.fetch_one(
            "SELECT urgency_score FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id_low,)
        )
        
        assert row_urgent["urgency_score"] > row_low["urgency_score"]
    
    def test_get_pending_reminders(self, reminder_system, test_user):
        """Test retrieving pending reminders."""
        now = datetime.utcnow()
        
        # Past - should be retrieved
        reminder_system.create_reminder(
            user_id=test_user,
            title="Past reminder",
            scheduled_at=now - timedelta(hours=1)
        )
        
        # Future - should not be retrieved
        reminder_system.create_reminder(
            user_id=test_user,
            title="Future reminder",
            scheduled_at=now + timedelta(hours=2)
        )
        
        pending = reminder_system.get_pending_reminders(test_user)
        
        assert len(pending) >= 1
        assert all(r.scheduled_at <= now for r in pending)
    
    def test_snooze_reminder(self, reminder_system, test_user):
        """Test snoozing a reminder."""
        scheduled_at = datetime.utcnow() - timedelta(hours=1)
        
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Snoozable reminder",
            scheduled_at=scheduled_at
        )
        
        reminder_system.snooze_reminder(reminder_id, snooze_minutes=30)
        
        row = reminder_system.db.fetch_one(
            "SELECT * FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id,)
        )
        
        assert row["status"] == "snoozed"
        assert row["snoozed_until"] is not None
        assert row["snooze_count"] == 1
    
    def test_complete_reminder(self, reminder_system, test_user):
        """Test completing a reminder."""
        scheduled_at = datetime.utcnow() - timedelta(hours=1)
        
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Completable reminder",
            scheduled_at=scheduled_at
        )
        
        reminder_system.complete_reminder(reminder_id)
        
        row = reminder_system.db.fetch_one(
            "SELECT * FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id,)
        )
        
        assert row["status"] == "completed"


# ============================================================================
# CLUSTERING TESTS
# ============================================================================

class TestReminderClustering:
    """Test reminder clustering and batching."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def reminder_system(self, db):
        """Create reminder system."""
        return ReminderSystem(db)
    
    def test_automatic_clustering(self, reminder_system, test_user, db):
        """Test that reminders are automatically clustered."""
        # Enable clustering
        db.execute(
            """INSERT OR REPLACE INTO user_proactive_preferences 
               (user_id, cluster_reminders, updated_at)
               VALUES (?, 1, ?)""",
            (test_user, datetime.utcnow().isoformat())
        )
        db.commit()
        
        scheduled_at = datetime.utcnow() + timedelta(hours=2)
        
        # Create multiple reminders at similar times
        reminder_ids = []
        for i in range(3):
            rid = reminder_system.create_reminder(
                user_id=test_user,
                title=f"Reminder {i}",
                scheduled_at=scheduled_at + timedelta(minutes=i*5)
            )
            reminder_ids.append(rid)
        
        # Check if they share a cluster
        rows = reminder_system.db.fetch_all(
            "SELECT cluster_id FROM agency_reminders WHERE reminder_id IN (?, ?, ?)",
            tuple(reminder_ids)
        )
        
        cluster_ids = [row["cluster_id"] for row in rows if row["cluster_id"]]
        
        # At least some should be clustered
        assert len(cluster_ids) > 0
    
    def test_get_clustered_reminders(self, reminder_system, test_user, db):
        """Test retrieving reminders from a cluster."""
        # Enable clustering
        db.execute(
            """INSERT OR REPLACE INTO user_proactive_preferences 
               (user_id, cluster_reminders, updated_at)
               VALUES (?, 1, ?)""",
            (test_user, datetime.utcnow().isoformat())
        )
        db.commit()
        
        scheduled_at = datetime.utcnow() + timedelta(hours=2)
        
        # Create reminders that will cluster
        reminder_ids = []
        for i in range(2):
            rid = reminder_system.create_reminder(
                user_id=test_user,
                title=f"Clustered {i}",
                scheduled_at=scheduled_at + timedelta(minutes=i*3)
            )
            reminder_ids.append(rid)
        
        # Get cluster_id from first reminder
        row = reminder_system.db.fetch_one(
            "SELECT cluster_id FROM agency_reminders WHERE reminder_id = ?",
            (reminder_ids[0],)
        )
        
        if row and row["cluster_id"]:
            clustered = reminder_system.get_clustered_reminders(
                test_user,
                row["cluster_id"]
            )
            
            assert len(clustered) >= 1


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestProactiveIntegration:
    """Test integration between follow-ups and reminders."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def followup_system(self, db):
        """Create followup system."""
        return FollowupSystem(db)
    
    @pytest.fixture
    def reminder_system(self, db):
        """Create reminder system."""
        return ReminderSystem(db)
    
    @pytest.fixture
    def test_goal_id(self, db, test_user):
        """Create a test goal."""
        goal_id = "test-goal-integration-1"
        db.execute(
            """INSERT OR IGNORE INTO agency_goals 
               (goal_id, user_id, origin, goal_type, title, description, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, test_user, "user", "work", "Test goal", "Test", "normal", "active",
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
        )
        db.commit()
        return goal_id
    
    def test_followup_and_reminder_for_goal(
        self,
        followup_system,
        reminder_system,
        test_user,
        test_goal_id
    ):
        """Test creating both follow-up and reminder for same goal."""
        scheduled_at = datetime.utcnow() + timedelta(hours=4)
        
        # Create follow-up
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.PROGRESS_UPDATE,
            content="How's it going?",
            scheduled_at=scheduled_at,
            goal_id=test_goal_id
        )
        
        # Create reminder
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Complete goal",
            scheduled_at=scheduled_at + timedelta(hours=1),
            goal_id=test_goal_id
        )
        
        assert followup_id is not None
        assert reminder_id is not None
        
        # Verify both link to same goal
        followup_row = followup_system.db.fetch_one(
            "SELECT goal_id FROM agency_followups WHERE followup_id = ?",
            (followup_id,)
        )
        
        reminder_row = reminder_system.db.fetch_one(
            "SELECT goal_id FROM agency_reminders WHERE reminder_id = ?",
            (reminder_id,)
        )
        
        assert followup_row["goal_id"] == test_goal_id
        assert reminder_row["goal_id"] == test_goal_id
    
    def test_analytics_recording(self, followup_system, reminder_system, test_user, db):
        """Test that analytics are recorded for both systems."""
        # Create and respond to follow-up
        followup_id = followup_system.create_followup(
            user_id=test_user,
            followup_type=FollowupType.CHECK_IN,
            content="Check in",
            scheduled_at=datetime.utcnow() - timedelta(hours=1)
        )
        followup_system.mark_delivered(followup_id)
        followup_system.record_response(followup_id, "All good!", 0.9)
        
        # Create and snooze reminder
        reminder_id = reminder_system.create_reminder(
            user_id=test_user,
            title="Reminder",
            scheduled_at=datetime.utcnow() - timedelta(hours=1)
        )
        reminder_system.snooze_reminder(reminder_id)
        
        # Check analytics
        analytics = db.fetch_all(
            "SELECT * FROM proactive_analytics WHERE user_id = ?",
            (test_user,)
        )
        
        assert len(analytics) >= 2
        behavior_types = [a["behavior_type"] for a in analytics]
        assert "followup" in behavior_types
        assert "reminder" in behavior_types
