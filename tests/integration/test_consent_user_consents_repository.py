"""
Integration tests for ConsentUserConsentsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.consent.models import ConsentUserConsent
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
async def test_user(uow):
    user_id = "consent_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Consent Test User",
            nickname="consent_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestConsentUserConsentsRepository:
    
    @pytest.mark.asyncio
    async def test_create_consent(self, uow, test_user):
        consent = ConsentUserConsent(
            consent_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            consent_type="data_collection",
            scope="global",
            granted=1,
            granted_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.consent_user_consents.create(consent)
        await uow.commit()
        
        assert created.consent_id == consent.consent_id
        assert created.granted == 1
    
    @pytest.mark.asyncio
    async def test_get_consent_by_id(self, uow, test_user):
        consent = ConsentUserConsent(
            consent_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            consent_type="proactive_contact",
            scope="feature",
            granted=1,
            granted_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.consent_user_consents.create(consent)
        await uow.commit()
        
        found = await uow.consent_user_consents.get_by_id(consent.consent_id)
        assert found is not None
        assert found.consent_type == "proactive_contact"
    
    @pytest.mark.asyncio
    async def test_update_consent(self, uow, test_user):
        consent = ConsentUserConsent(
            consent_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            consent_type="curiosity_exploration",
            scope="global",
            granted=1,
            granted_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.consent_user_consents.create(consent)
        await uow.commit()
        
        consent.granted = 0
        consent.revoked_at = datetime.now(UTC).isoformat()
        updated = await uow.consent_user_consents.update(consent)
        await uow.commit()
        
        assert updated.granted == 0
        
        found = await uow.consent_user_consents.get_by_id(consent.consent_id)
        assert found.revoked_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_consent(self, uow, test_user):
        consent = ConsentUserConsent(
            consent_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            consent_type="test",
            scope="global",
            granted=1,
            granted_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.consent_user_consents.create(consent)
        await uow.commit()
        
        success = await uow.consent_user_consents.delete(consent.consent_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.consent_user_consents.get_by_id(consent.consent_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_consents(self, uow, test_user):
        for i in range(3):
            consent = ConsentUserConsent(
                consent_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                consent_type="data_collection",
                scope="global",
                granted=1 if i < 2 else 0,
                granted_at=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.consent_user_consents.create(consent)
        
        await uow.commit()
        
        all_consents = await uow.consent_user_consents.list(filters={"user_id": test_user.uuid})
        assert len(all_consents) >= 3
        
        granted = await uow.consent_user_consents.list(filters={"granted": 1})
        assert len(granted) >= 2
    
    @pytest.mark.asyncio
    async def test_count_consents(self, uow, test_user):
        for i in range(3):
            consent = ConsentUserConsent(
                consent_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                consent_type="count_test",
                scope="global",
                granted=1,
                granted_at=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
            await uow.consent_user_consents.create(consent)
        
        await uow.commit()
        
        count = await uow.consent_user_consents.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_consents(self, uow, test_user):
        for i in range(3):
            consent = ConsentUserConsent(
                consent_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                consent_type="active_test",
                scope="global",
                granted=1,
                granted_at=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
                revoked_at=datetime.now(UTC).isoformat() if i == 2 else None,
            )
            await uow.consent_user_consents.create(consent)
        
        await uow.commit()
        
        active = await uow.consent_user_consents.get_active_consents(test_user.uuid, "active_test")
        assert len(active) >= 2
        for c in active:
            assert c.granted == 1
            assert c.revoked_at is None
