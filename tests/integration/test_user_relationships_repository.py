"""
Integration tests for UserRelationshipsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.user.relationship_models import UserRelationship
from aico.data.user.models import UserProfile
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_users(uow):
    user1_id = "relationship_test_user1"
    user2_id = "relationship_test_user2"
    
    for user_id, name in [(user1_id, "User 1"), (user2_id, "User 2")]:
        existing = await uow.users.get_by_id(user_id)
        if not existing:
            user = UserProfile(
                uuid=user_id,
                full_name=name,
                nickname=name.lower().replace(" ", "_"),
                user_type="parent",
                is_active=True,
                primary_language="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.users.create(user)
    
    await uow.commit()
    return user1_id, user2_id


class TestUserRelationshipsRepository:
    
    @pytest.mark.asyncio
    async def test_create_relationship(self, uow, test_users):
        user1_id, user2_id = test_users
        relationship = UserRelationship(
            uuid=str(uuid.uuid4()),
            user_uuid=user1_id,
            related_user_uuid=user2_id,
            relationship_type="parent_child",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        created = await uow.user_relationships.create(relationship)
        await uow.commit()
        
        assert created.uuid == relationship.uuid
        assert created.relationship_type == "parent_child"
    
    @pytest.mark.asyncio
    async def test_get_relationship_by_id(self, uow, test_users):
        user1_id, user2_id = test_users
        relationship = UserRelationship(
            uuid=str(uuid.uuid4()),
            user_uuid=user1_id,
            related_user_uuid=user2_id,
            relationship_type="sibling",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.user_relationships.create(relationship)
        await uow.commit()
        
        found = await uow.user_relationships.get_by_id(relationship.uuid)
        assert found is not None
        assert found.relationship_type == "sibling"
    
    @pytest.mark.asyncio
    async def test_update_relationship(self, uow, test_users):
        user1_id, user2_id = test_users
        relationship = UserRelationship(
            uuid=str(uuid.uuid4()),
            user_uuid=user1_id,
            related_user_uuid=user2_id,
            relationship_type="friend",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.user_relationships.create(relationship)
        await uow.commit()
        
        relationship.is_active = False
        updated = await uow.user_relationships.update(relationship)
        await uow.commit()
        
        assert updated.is_active is False
        
        found = await uow.user_relationships.get_by_id(relationship.uuid)
        assert found.is_active is False
    
    @pytest.mark.asyncio
    async def test_delete_relationship(self, uow, test_users):
        user1_id, user2_id = test_users
        relationship = UserRelationship(
            uuid=str(uuid.uuid4()),
            user_uuid=user1_id,
            related_user_uuid=user2_id,
            relationship_type="colleague",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        
        await uow.user_relationships.create(relationship)
        await uow.commit()
        
        success = await uow.user_relationships.delete(relationship.uuid)
        await uow.commit()
        
        assert success is True
        
        found = await uow.user_relationships.get_by_id(relationship.uuid)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_relationships(self, uow, test_users):
        user1_id, user2_id = test_users
        
        for i in range(3):
            relationship = UserRelationship(
                uuid=str(uuid.uuid4()),
                user_uuid=user1_id,
                related_user_uuid=user2_id,
                relationship_type=f"type_{i}",
                is_active=True if i < 2 else False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_relationships.create(relationship)
        
        await uow.commit()
        
        all_relationships = await uow.user_relationships.list(filters={"user_uuid": user1_id})
        assert len(all_relationships) >= 3
        
        active = await uow.user_relationships.list(filters={"user_uuid": user1_id, "is_active": True})
        assert len(active) >= 2
    
    @pytest.mark.asyncio
    async def test_count_relationships(self, uow, test_users):
        user1_id, user2_id = test_users
        
        for i in range(3):
            relationship = UserRelationship(
                uuid=str(uuid.uuid4()),
                user_uuid=user1_id,
                related_user_uuid=user2_id,
                relationship_type=f"count_type_{i}",
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_relationships.create(relationship)
        
        await uow.commit()
        
        count = await uow.user_relationships.count(filters={"user_uuid": user1_id})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_user_relationships(self, uow, test_users):
        user1_id, user2_id = test_users
        
        for i in range(3):
            relationship = UserRelationship(
                uuid=str(uuid.uuid4()),
                user_uuid=user1_id,
                related_user_uuid=user2_id,
                relationship_type=f"user_type_{i}",
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_relationships.create(relationship)
        
        await uow.commit()
        
        relationships = await uow.user_relationships.get_user_relationships(user1_id)
        assert len(relationships) >= 3
        for rel in relationships:
            assert rel.user_uuid == user1_id
