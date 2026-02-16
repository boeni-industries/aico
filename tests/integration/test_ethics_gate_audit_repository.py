"""
Integration tests for EthicsGateAuditRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ethics.audit_models import EthicsGateAudit
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
    user_id = "ethics_audit_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Ethics Audit Test User",
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


class TestEthicsGateAuditRepository:
    
    @pytest.mark.asyncio
    async def test_create_audit(self, uow, test_user):
        audit = EthicsGateAudit(
            audit_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            target_type="goal",
            target_id=str(uuid.uuid4()),
            decision="approved",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.ethics_gate_audit.create(audit)
        await uow.commit()
        
        assert created.audit_id == audit.audit_id
        assert created.decision == "approved"
    
    @pytest.mark.asyncio
    async def test_get_audit_by_id(self, uow, test_user):
        audit = EthicsGateAudit(
            audit_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            target_type="plan",
            target_id=str(uuid.uuid4()),
            decision="blocked",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.ethics_gate_audit.create(audit)
        await uow.commit()
        
        found = await uow.ethics_gate_audit.get_by_id(audit.audit_id)
        assert found is not None
        assert found.decision == "blocked"
    
    @pytest.mark.asyncio
    async def test_update_audit(self, uow, test_user):
        audit = EthicsGateAudit(
            audit_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            target_type="skill",
            target_id=str(uuid.uuid4()),
            decision="approved",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.ethics_gate_audit.create(audit)
        await uow.commit()
        
        audit.reasoning = "Updated reasoning"
        audit.processing_time_ms = 150
        updated = await uow.ethics_gate_audit.update(audit)
        await uow.commit()
        
        assert updated.reasoning == "Updated reasoning"
        
        found = await uow.ethics_gate_audit.get_by_id(audit.audit_id)
        assert found.processing_time_ms == 150
    
    @pytest.mark.asyncio
    async def test_delete_audit(self, uow, test_user):
        audit = EthicsGateAudit(
            audit_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            target_type="goal",
            target_id=str(uuid.uuid4()),
            decision="needs_review",
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.ethics_gate_audit.create(audit)
        await uow.commit()
        
        success = await uow.ethics_gate_audit.delete(audit.audit_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.ethics_gate_audit.get_by_id(audit.audit_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_audits(self, uow, test_user):
        for i in range(3):
            audit = EthicsGateAudit(
                audit_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                target_type="goal",
                target_id=str(uuid.uuid4()),
                decision="approved" if i < 2 else "blocked",
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.ethics_gate_audit.create(audit)
        
        await uow.commit()
        
        all_audits = await uow.ethics_gate_audit.list(filters={"user_id": test_user.uuid})
        assert len(all_audits) >= 3
        
        approved = await uow.ethics_gate_audit.list(filters={"decision": "approved"})
        assert len(approved) >= 2
    
    @pytest.mark.asyncio
    async def test_count_audits(self, uow, test_user):
        for i in range(3):
            audit = EthicsGateAudit(
                audit_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                target_type="plan",
                target_id=str(uuid.uuid4()),
                decision="approved",
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.ethics_gate_audit.create(audit)
        
        await uow.commit()
        
        count = await uow.ethics_gate_audit.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_user_audit_trail(self, uow, test_user):
        for i in range(3):
            audit = EthicsGateAudit(
                audit_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                target_type="goal",
                target_id=str(uuid.uuid4()),
                decision="approved",
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.ethics_gate_audit.create(audit)
        
        await uow.commit()
        
        trail = await uow.ethics_gate_audit.get_user_audit_trail(test_user.uuid)
        assert len(trail) >= 3
        for a in trail:
            assert a.user_id == test_user.uuid
