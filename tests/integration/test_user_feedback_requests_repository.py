"""
Integration tests for UserFeedbackRequestsRepository.

Tests UserFeedbackRequestsRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.user.feedback_models import UserFeedbackRequest
from aico.data.user.models import UserProfile
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    """Create async session factory for tests."""
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    """Create Unit of Work for tests."""
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_user(uow):
    """Create a test user for feedback request tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Feedback Test User",
        nickname="feedback_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return user


class TestUserFeedbackRequestsRepository:
    """Test UserFeedbackRequestsRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_feedback_request(self, uow, test_user):
        """Test creating a new feedback request."""
        request = UserFeedbackRequest(
            request_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            feedback_type="goal_progress",
            question="How is your progress on the goal?",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.user_feedback_requests.create(request)
        await uow.commit()
        
        assert created.request_id == request.request_id
        assert created.feedback_type == "goal_progress"
        assert created.response is None
    
    @pytest.mark.asyncio
    async def test_get_feedback_request_by_id(self, uow, test_user):
        """Test retrieving feedback request by ID."""
        request = UserFeedbackRequest(
            request_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            feedback_type="skill_rating",
            question="How would you rate this skill?",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.user_feedback_requests.create(request)
        await uow.commit()
        
        found = await uow.user_feedback_requests.get_by_id(request.request_id)
        assert found is not None
        assert found.request_id == request.request_id
        assert found.feedback_type == "skill_rating"
    
    @pytest.mark.asyncio
    async def test_update_feedback_request(self, uow, test_user):
        """Test updating a feedback request."""
        request = UserFeedbackRequest(
            request_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            feedback_type="general",
            question="How are you feeling?",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.user_feedback_requests.create(request)
        await uow.commit()
        
        # Update the request
        request.response = "I'm feeling great!"
        request.rating = 4.5
        request.responded_at = datetime.now(UTC).isoformat()
        updated = await uow.user_feedback_requests.update(request)
        await uow.commit()
        
        assert updated.response == "I'm feeling great!"
        
        # Verify update persisted
        found = await uow.user_feedback_requests.get_by_id(request.request_id)
        assert found.rating == 4.5
        assert found.responded_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_feedback_request(self, uow, test_user):
        """Test deleting a feedback request."""
        request = UserFeedbackRequest(
            request_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            feedback_type="test",
            question="Test question",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.user_feedback_requests.create(request)
        await uow.commit()
        
        # Delete the request
        success = await uow.user_feedback_requests.delete(request.request_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.user_feedback_requests.get_by_id(request.request_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_feedback_requests(self, uow, test_user):
        """Test listing feedback requests with filters."""
        for i in range(3):
            request = UserFeedbackRequest(
                request_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                feedback_type="goal_progress" if i < 2 else "skill_rating",
                question=f"Question {i}",
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.user_feedback_requests.create(request)
        
        await uow.commit()
        
        # List all requests for user
        all_requests = await uow.user_feedback_requests.list(filters={"user_id": test_user.uuid})
        assert len(all_requests) >= 3
        
        # List by feedback type
        goal_requests = await uow.user_feedback_requests.list(filters={"feedback_type": "goal_progress"})
        assert len(goal_requests) >= 2
    
    @pytest.mark.asyncio
    async def test_count_feedback_requests(self, uow, test_user):
        """Test counting feedback requests."""
        for i in range(3):
            request = UserFeedbackRequest(
                request_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                feedback_type="count_test",
                question=f"Count question {i}",
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.user_feedback_requests.create(request)
        
        await uow.commit()
        
        count = await uow.user_feedback_requests.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_pending_for_user(self, uow, test_user):
        """Test getting pending feedback requests for user."""
        for i in range(3):
            request = UserFeedbackRequest(
                request_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                feedback_type="pending_test",
                question=f"Pending question {i}",
                created_at=datetime.now(UTC).isoformat(),
                responded_at=datetime.now(UTC).isoformat() if i == 2 else None,
            )
            await uow.user_feedback_requests.create(request)
        
        await uow.commit()
        
        pending = await uow.user_feedback_requests.get_pending_for_user(test_user.uuid)
        assert len(pending) >= 2
        for req in pending:
            assert req.responded_at is None
    
    @pytest.mark.asyncio
    async def test_mark_as_responded(self, uow, test_user):
        """Test marking a feedback request as responded."""
        request = UserFeedbackRequest(
            request_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            feedback_type="respond_test",
            question="Test response marking",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.user_feedback_requests.create(request)
        await uow.commit()
        
        # Mark as responded
        success = await uow.user_feedback_requests.mark_as_responded(
            request.request_id,
            "This is my response",
            4.0
        )
        await uow.commit()
        
        assert success is True
        
        # Verify it's marked
        found = await uow.user_feedback_requests.get_by_id(request.request_id)
        assert found.response == "This is my response"
        assert found.rating == 4.0
        assert found.responded_at is not None
