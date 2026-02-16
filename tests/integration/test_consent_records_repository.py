"""
Integration tests for ConsentRecordsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC, timedelta

from aico.data.consent.models import ConsentRecord
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
    user_id = "consent_records_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Consent Records Test User",
            nickname="records_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestConsentRecordsRepository:
    
    @pytest.mark.asyncio
    async def test_create_consent_record(self, uow, test_user):
        record = ConsentRecord(
            consent_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            consent_scope="data_collection",
            decision="granted",
        )
        
        created = await uow.consent_records.create(record)
        await uow.commit()
        
        assert created.consent_id == record.consent_id
        assert created.decision == "granted"
    
    @pytest.mark.asyncio
    async def test_get_consent_record_by_id(self, uow, test_user):
        record = ConsentRecord(
            consent_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            consent_scope="proactive_contact",
            decision="denied",
        )
        
        await uow.consent_records.create(record)
        await uow.commit()
        
        found = await uow.consent_records.get_by_id(record.consent_id)
        assert found is not None
        assert found.decision == "denied"
    
    @pytest.mark.asyncio
    async def test_update_consent_record(self, uow, test_user):
        record = ConsentRecord(
            consent_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            consent_scope="analytics",
            decision="granted",
        )
        
        await uow.consent_records.create(record)
        await uow.commit()
        
        record.decision = "denied"
        record.expires_at = datetime.now(UTC) + timedelta(days=30)
        updated = await uow.consent_records.update(record)
        await uow.commit()
        
        assert updated.decision == "denied"
        
        found = await uow.consent_records.get_by_id(record.consent_id)
        assert found.decision == "denied"
    
    @pytest.mark.asyncio
    async def test_delete_consent_record(self, uow, test_user):
        record = ConsentRecord(
            consent_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            consent_scope="marketing",
            decision="granted",
        )
        
        await uow.consent_records.create(record)
        await uow.commit()
        
        success = await uow.consent_records.delete(record.consent_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.consent_records.get_by_id(record.consent_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_consent_records(self, uow, test_user):
        for i in range(3):
            record = ConsentRecord(
                consent_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                consent_scope=f"scope_{i}",
                decision="granted" if i < 2 else "denied",
            )
            await uow.consent_records.create(record)
        
        await uow.commit()
        
        all_records = await uow.consent_records.list(filters={"user_id": test_user.uuid})
        assert len(all_records) >= 3
        
        granted = await uow.consent_records.list(filters={"decision": "granted"})
        assert len(granted) >= 2
    
    @pytest.mark.asyncio
    async def test_count_consent_records(self, uow, test_user):
        for i in range(3):
            record = ConsentRecord(
                consent_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                consent_scope=f"count_scope_{i}",
                decision="granted",
            )
            await uow.consent_records.create(record)
        
        await uow.commit()
        
        count = await uow.consent_records.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_user_consents(self, uow, test_user):
        for i in range(3):
            record = ConsentRecord(
                consent_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                consent_scope=f"user_scope_{i}",
                decision="granted",
            )
            await uow.consent_records.create(record)
        
        await uow.commit()
        
        consents = await uow.consent_records.get_user_consents(test_user.uuid)
        assert len(consents) >= 3
        for c in consents:
            assert c.user_id == test_user.uuid
