"""
Integration tests for AMSService.

Tests AMS (Adaptive Memory System) service layer using actual repositories and database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.services.ams_service import AMSService
# AMSService test - checking basic functionality


@pytest.fixture
async def ams_service(uow):
    """Create AMSService with UnitOfWork."""
    return AMSService(uow)


class TestAMSService:
    """Test suite for AMSService."""

    @pytest.mark.asyncio
    async def test_create_trajectory(self, ams_service, test_user):
        """Test creating a trajectory."""
        from aico.ai.ams.models import AMSTrajectory
        from datetime import datetime, UTC
        
        trajectory_data = {
            "trajectory_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "conversation_id": str(uuid.uuid4()),
            "selected_skill_id": "skill_123",
            "context_bucket": "bucket_0",
            "feedback_reward": 1,
            "timestamp": datetime.now(UTC),
            "archived": False,
            "agency_context": "test context",
            "message_id": str(uuid.uuid4()),
            "turn_number": 1,
            "user_input": "Test user input",
            "ai_response": "Test AI response",
        }
        
        created = await ams_service.create_trajectory(trajectory_data)
        
        assert created.trajectory_id == trajectory_data["trajectory_id"]
        assert created.user_input == "Test user input"

    @pytest.mark.asyncio
    async def test_get_trajectory(self, ams_service, test_user):
        """Test retrieving a trajectory."""
        from datetime import datetime, UTC
        
        trajectory_data = {
            "trajectory_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "conversation_id": str(uuid.uuid4()),
            "selected_skill_id": "skill_123",
            "context_bucket": "bucket_0",
            "feedback_reward": 1,
            "timestamp": datetime.now(UTC),
            "archived": False,
            "agency_context": "test context",
            "message_id": str(uuid.uuid4()),
            "turn_number": 1,
            "user_input": "Test user input",
            "ai_response": "Test AI response",
        }
        
        created = await ams_service.create_trajectory(trajectory_data)
        retrieved = await ams_service.get_trajectory(created.trajectory_id)
        
        assert retrieved is not None
        assert retrieved.trajectory_id == created.trajectory_id

    @pytest.mark.asyncio
    async def test_list_user_trajectories(self, ams_service, test_user):
        """Test listing trajectories for a user."""
        from datetime import datetime, UTC
        
        trajectory_data = {
            "trajectory_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "conversation_id": str(uuid.uuid4()),
            "selected_skill_id": "skill_123",
            "context_bucket": "bucket_0",
            "feedback_reward": 1,
            "timestamp": datetime.now(UTC),
            "archived": False,
            "agency_context": "test context",
            "message_id": str(uuid.uuid4()),
            "turn_number": 1,
            "user_input": "Test user input",
            "ai_response": "Test AI response",
        }
        
        created = await ams_service.create_trajectory(trajectory_data)
        trajectories = await ams_service.list_user_trajectories(test_user.uuid)
        
        assert len(trajectories) >= 1
        assert any(t.trajectory_id == created.trajectory_id for t in trajectories)

    @pytest.mark.asyncio
    async def test_update_trajectory(self, ams_service, test_user):
        """Test updating a trajectory."""
        from aico.ai.ams.models import AMSTrajectory
        from datetime import datetime, UTC
        
        trajectory_data = {
            "trajectory_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "conversation_id": str(uuid.uuid4()),
            "selected_skill_id": "skill_123",
            "context_bucket": "bucket_0",
            "feedback_reward": 1,
            "timestamp": datetime.now(UTC),
            "archived": False,
            "agency_context": "original context",
            "message_id": str(uuid.uuid4()),
            "turn_number": 1,
            "user_input": "Original input",
            "ai_response": "Original response",
        }
        created = await ams_service.create_trajectory(trajectory_data)
        
        trajectory_data["agency_context"] = "updated context"
        trajectory_data["archived"] = True
        updated = await ams_service.update_trajectory(trajectory_data)
        
        assert updated.agency_context == "updated context"
        assert updated.archived is True

    @pytest.mark.asyncio
    async def test_delete_trajectory(self, ams_service, test_user):
        """Test deleting a trajectory."""
        from datetime import datetime, UTC
        
        trajectory_data = {
            "trajectory_id": str(uuid.uuid4()),
            "user_id": test_user.uuid,
            "conversation_id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC),
            "archived": False,
        }
        created = await ams_service.create_trajectory(trajectory_data)
        
        success = await ams_service.delete_trajectory(created.trajectory_id)
        assert success is True
        
        deleted = await ams_service.get_trajectory(created.trajectory_id)
        assert deleted is None
