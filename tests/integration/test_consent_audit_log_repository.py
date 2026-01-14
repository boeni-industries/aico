"""
Integration tests for ConsentAuditLogRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.consent.audit_models import ConsentAuditLog
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
    user_id = "consent_audit_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Consent Audit Test User",
            nickname="audit_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestConsentAuditLogRepository:
    
    @pytest.mark.asyncio
    async def test_create_audit_log(self, uow, test_user, test_consent):
        audit = ConsentAuditLog(
            audit_id=str(uuid.uuid4()),
            consent_id=test_consent.consent_id,
            user_id=test_user.uuid,
            action="granted",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.consent_audit_log.create(audit)
        await uow.commit()
        
        assert created.audit_id == audit.audit_id
        assert created.action == "granted"
    
    @pytest.mark.asyncio
    async def test_get_audit_log_by_id(self, uow, test_user, test_consent):
        audit = ConsentAuditLog(
            audit_id=str(uuid.uuid4()),
            consent_id=test_consent.consent_id,
            user_id=test_user.uuid,
            action="revoked",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.consent_audit_log.create(audit)
        await uow.commit()
        
        found = await uow.consent_audit_log.get_by_id(audit.audit_id)
        assert found is not None
        assert found.action == "revoked"
    
    @pytest.mark.asyncio
    async def test_update_audit_log(self, uow, test_user, test_consent):
        audit = ConsentAuditLog(
            audit_id=str(uuid.uuid4()),
            consent_id=test_consent.consent_id,
            user_id=test_user.uuid,
            action="granted",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.consent_audit_log.create(audit)
        await uow.commit()
        
        audit.reason = "User requested"
        updated = await uow.consent_audit_log.update(audit)
        await uow.commit()
        
        assert updated.reason == "User requested"
        
        found = await uow.consent_audit_log.get_by_id(audit.audit_id)
        assert found.reason == "User requested"
    
    @pytest.mark.asyncio
    async def test_delete_audit_log(self, uow, test_user, test_consent):
        audit = ConsentAuditLog(
            audit_id=str(uuid.uuid4()),
            consent_id=test_consent.consent_id,
            user_id=test_user.uuid,
            action="expired",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.consent_audit_log.create(audit)
        await uow.commit()
        
        success = await uow.consent_audit_log.delete(audit.audit_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.consent_audit_log.get_by_id(audit.audit_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_audit_logs(self, uow, test_user, test_consent):
        for i in range(3):
            audit = ConsentAuditLog(
                audit_id=str(uuid.uuid4()),
                consent_id=test_consent.consent_id,
                user_id=test_user.uuid,
                action="granted" if i < 2 else "revoked",
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.consent_audit_log.create(audit)
        
        await uow.commit()
        
        all_audits = await uow.consent_audit_log.list(filters={"user_id": test_user.uuid})
        assert len(all_audits) >= 3
        
        granted = await uow.consent_audit_log.list(filters={"action": "granted"})
        assert len(granted) >= 2
    
    @pytest.mark.asyncio
    async def test_count_audit_logs(self, uow, test_user, test_consent):
        for i in range(3):
            audit = ConsentAuditLog(
                audit_id=str(uuid.uuid4()),
                consent_id=test_consent.consent_id,
                user_id=test_user.uuid,
                action="granted",
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.consent_audit_log.create(audit)
        
        await uow.commit()
        
        count = await uow.consent_audit_log.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_consent_history(self, uow, test_user, test_consent):
        for i in range(3):
            audit = ConsentAuditLog(
                audit_id=str(uuid.uuid4()),
                consent_id=test_consent.consent_id,
                user_id=test_user.uuid,
                action=["granted", "revoked", "expired"][i],
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.consent_audit_log.create(audit)
        
        await uow.commit()
        
        history = await uow.consent_audit_log.get_consent_history(test_consent.consent_id)
        assert len(history) >= 3
        for h in history:
            assert h.consent_id == test_consent.consent_id
