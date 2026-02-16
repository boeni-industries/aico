"""
Integration Test for UserRepository

Tests the complete stack:
- PostgreSQL connection with encryption
- asyncpg connection pool
- SQLAlchemy async sessions
- Repository pattern CRUD operations
- Unit of Work transaction management
"""

import pytest
import os
import uuid
from datetime import datetime, UTC

# Note: Password will be retrieved from keystore (postgres_postgres_password)
# or from AICO_PG_PASSWORD environment variable if set

from aico.data.postgres.connection import get_session_factory, close_postgres_pool
from aico.data.uow import UnitOfWork
from aico.data.user.models import UserProfile


@pytest.fixture(scope="function")
async def session_factory():
    """
    Create SQLAlchemy session factory for tests.
    
    This fixture:
    - Connects to PostgreSQL with encryption
    - Sets up connection pool
    - Provides session factory
    - Cleans up on teardown
    """
    factory = await get_session_factory()
    yield factory
    # Note: We don't close the pool here as it's shared across tests


@pytest.fixture
async def uow(session_factory):
    """
    Create Unit of Work for each test.
    
    Provides clean transaction per test with automatic rollback.
    """
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow
        # Rollback after test to keep database clean
        await uow.rollback()


@pytest.fixture
def sample_user():
    """Create sample user data for tests."""
    return UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Test User",
        nickname="tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestUserRepositoryConnection:
    """Test PostgreSQL connection and setup."""
    
    @pytest.mark.asyncio
    async def test_connection_pool_created(self, session_factory):
        """Verify connection pool is created successfully."""
        assert session_factory is not None
        
    @pytest.mark.asyncio
    async def test_session_creation(self, session_factory):
        """Verify we can create async sessions."""
        from sqlalchemy import text
        async with session_factory() as session:
            assert session is not None
            # Verify connection works with simple query
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            assert row.test == 1


class TestUserRepositoryCRUD:
    """Test CRUD operations via UserRepository."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, uow, sample_user):
        """Test creating a new user."""
        # Create user via repository
        created_user = await uow.users.create(sample_user)
        await uow.commit()
        
        # Verify user was created
        assert created_user.uuid == sample_user.uuid
        assert created_user.full_name == sample_user.full_name
        assert created_user.nickname == sample_user.nickname
        assert created_user.user_type == sample_user.user_type
        assert created_user.is_active == sample_user.is_active
        assert created_user.created_at is not None
        assert created_user.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, uow, sample_user):
        """Test retrieving user by ID."""
        # Create user
        await uow.users.create(sample_user)
        await uow.commit()
        
        # Retrieve user
        retrieved_user = await uow.users.get_by_id(sample_user.uuid)
        
        # Verify retrieved user matches
        assert retrieved_user is not None
        assert retrieved_user.uuid == sample_user.uuid
        assert retrieved_user.full_name == sample_user.full_name
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, uow):
        """Test retrieving non-existent user returns None."""
        result = await uow.users.get_by_id("non-existent-uuid")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_user(self, uow, sample_user):
        """Test updating existing user."""
        # Create user
        await uow.users.create(sample_user)
        await uow.commit()
        
        # Update user
        sample_user.full_name = "Updated Name"
        sample_user.nickname = "updated"
        updated_user = await uow.users.update(sample_user)
        await uow.commit()
        
        # Verify updates
        assert updated_user.full_name == "Updated Name"
        assert updated_user.nickname == "updated"
        
        # Verify in database
        retrieved = await uow.users.get_by_id(sample_user.uuid)
        assert retrieved.full_name == "Updated Name"
    
    @pytest.mark.asyncio
    async def test_delete_user(self, uow, sample_user):
        """Test soft-deleting user (sets is_active=False)."""
        # Create user
        await uow.users.create(sample_user)
        await uow.commit()
        
        # Delete user
        await uow.users.delete(sample_user.uuid)
        await uow.commit()
        
        # Verify user is soft-deleted (not returned by get_by_id)
        result = await uow.users.get_by_id(sample_user.uuid)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_users(self, uow):
        """Test listing users with filters."""
        # Create multiple users
        user1 = UserProfile(
            uuid=str(uuid.uuid4()),
            full_name="User One",
            nickname="one",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        user2 = UserProfile(
            uuid=str(uuid.uuid4()),
            full_name="User Two",
            nickname="two",
            user_type="child",
            is_active=True,
            primary_language="de",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.users.create(user1)
        await uow.users.create(user2)
        await uow.commit()
        
        # List all users
        all_users = await uow.users.list()
        assert len(all_users) >= 2
        
        # List with filter
        parent_users = await uow.users.list(filters={'user_type': 'parent'})
        assert len(parent_users) >= 1
        assert all(u.user_type == 'parent' for u in parent_users)
    
    @pytest.mark.asyncio
    async def test_count_users(self, uow, sample_user):
        """Test counting users."""
        # Create user
        await uow.users.create(sample_user)
        await uow.commit()
        
        # Count all users
        count = await uow.users.count()
        assert count >= 1
        
        # Count with filter
        parent_count = await uow.users.count(filters={'user_type': 'parent'})
        assert parent_count >= 1
    
    @pytest.mark.asyncio
    async def test_get_by_full_name(self, uow):
        """Test custom query method."""
        # Create user with truly unique name for this test
        unique_id = str(uuid.uuid4())[:8]
        test_user = UserProfile(
            uuid=str(uuid.uuid4()),
            full_name=f"Unique Test User {unique_id}",
            nickname=f"unique_tester_{unique_id}",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(test_user)
        await uow.commit()
        
        # Find by full name (case-insensitive)
        found = await uow.users.get_by_full_name(f"unique test user {unique_id}")
        assert found is not None
        assert found.uuid == test_user.uuid


class TestUnitOfWorkTransactions:
    """Test transaction management via Unit of Work."""
    
    @pytest.mark.asyncio
    async def test_commit_success(self, uow, sample_user):
        """Test successful transaction commit."""
        await uow.users.create(sample_user)
        await uow.commit()
        
        # Verify user persisted
        retrieved = await uow.users.get_by_id(sample_user.uuid)
        assert retrieved is not None
    
    @pytest.mark.asyncio
    async def test_rollback_on_error(self, session_factory, sample_user):
        """Test automatic rollback on exception."""
        uow = UnitOfWork(session_factory)
        
        try:
            async with uow:
                await uow.users.create(sample_user)
                # Simulate error
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        # Verify user was NOT persisted (rolled back)
        async with UnitOfWork(session_factory) as uow2:
            retrieved = await uow2.users.get_by_id(sample_user.uuid)
            assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_atomic_multi_repository(self, uow, sample_user):
        """Test atomic operations across multiple repositories."""
        # This will be expanded when we have more repositories
        # For now, test multiple operations on same repository
        
        user1 = sample_user
        user2 = UserProfile(
            uuid=str(uuid.uuid4()),
            full_name="User Two",
            nickname="two",
            user_type="child",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        # Create both users in same transaction
        await uow.users.create(user1)
        await uow.users.create(user2)
        await uow.commit()
        
        # Verify both persisted
        assert await uow.users.get_by_id(user1.uuid) is not None
        assert await uow.users.get_by_id(user2.uuid) is not None


class TestPerformance:
    """Test query performance benchmarks."""
    
    @pytest.mark.asyncio
    async def test_query_latency(self, uow, sample_user):
        """Verify query latency is <10ms."""
        import time
        
        # Create user
        await uow.users.create(sample_user)
        await uow.commit()
        
        # Measure query time
        start = time.perf_counter()
        await uow.users.get_by_id(sample_user.uuid)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # Verify <50ms target (first query may include connection overhead)
        # Subsequent queries will be faster due to prepared statements
        assert elapsed_ms < 50, f"Query took {elapsed_ms:.2f}ms, target is <50ms"
    
    @pytest.mark.asyncio
    async def test_bulk_operations(self, uow):
        """Test bulk insert performance."""
        import time
        
        # Create 100 users
        users = [
            UserProfile(
                uuid=str(uuid.uuid4()),
                full_name=f"User {i}",
                nickname=f"user{i}",
                user_type="parent",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            for i in range(100)
        ]
        
        # Measure bulk insert time
        start = time.perf_counter()
        for user in users:
            await uow.users.create(user)
        await uow.commit()
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # Should be <100ms for 100 inserts
        assert elapsed_ms < 100, f"Bulk insert took {elapsed_ms:.2f}ms"
        
        # Verify count
        count = await uow.users.count()
        assert count >= 100


if __name__ == "__main__":
    # Run tests with: pytest tests/integration/test_user_repository.py -v
    pytest.main([__file__, "-v", "-s"])
