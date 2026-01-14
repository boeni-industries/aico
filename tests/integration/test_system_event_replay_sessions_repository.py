"""
Integration tests for SystemEventReplaySessionsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.system.metrics_models import SystemEventReplaySession
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
    user_id = "replay_session_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Replay Session Test User",
            nickname="replay_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestSystemEventReplaySessionsRepository:
    
    @pytest.mark.asyncio
    async def test_create_session(self, uow, test_user):
        session = SystemEventReplaySession(
            session_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-01-01T01:00:00Z",
            status="pending",
            started_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
        )
        
        created = await uow.system_event_replay_sessions.create(session)
        await uow.commit()
        
        assert created.session_id == session.session_id
        assert created.status == "pending"
    
    @pytest.mark.asyncio
    async def test_get_session_by_id(self, uow, test_user):
        session = SystemEventReplaySession(
            session_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-01-01T01:00:00Z",
            status="running",
            started_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.system_event_replay_sessions.create(session)
        await uow.commit()
        
        found = await uow.system_event_replay_sessions.get_by_id(session.session_id)
        assert found is not None
        assert found.status == "running"
    
    @pytest.mark.asyncio
    async def test_update_session(self, uow, test_user):
        session = SystemEventReplaySession(
            session_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-01-01T01:00:00Z",
            status="running",
            started_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.system_event_replay_sessions.create(session)
        await uow.commit()
        
        session.status = "completed"
        session.events_replayed = 100
        updated = await uow.system_event_replay_sessions.update(session)
        await uow.commit()
        
        assert updated.status == "completed"
        
        found = await uow.system_event_replay_sessions.get_by_id(session.session_id)
        assert found.events_replayed == 100
    
    @pytest.mark.asyncio
    async def test_delete_session(self, uow, test_user):
        session = SystemEventReplaySession(
            session_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-01-01T01:00:00Z",
            status="pending",
            started_at=datetime.now(UTC).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
        )
        
        await uow.system_event_replay_sessions.create(session)
        await uow.commit()
        
        success = await uow.system_event_replay_sessions.delete(session.session_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.system_event_replay_sessions.get_by_id(session.session_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_sessions(self, uow, test_user):
        for i in range(3):
            session = SystemEventReplaySession(
                session_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                start_time="2026-01-01T00:00:00Z",
                end_time="2026-01-01T01:00:00Z",
                status="pending" if i < 2 else "completed",
                started_at=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.system_event_replay_sessions.create(session)
        
        await uow.commit()
        
        all_sessions = await uow.system_event_replay_sessions.list(filters={"user_id": test_user.uuid})
        assert len(all_sessions) >= 3
        
        pending = await uow.system_event_replay_sessions.list(filters={"status": "pending"})
        assert len(pending) >= 2
    
    @pytest.mark.asyncio
    async def test_count_sessions(self, uow, test_user):
        for i in range(3):
            session = SystemEventReplaySession(
                session_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                start_time="2026-01-01T00:00:00Z",
                end_time="2026-01-01T01:00:00Z",
                status="pending",
                started_at=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.system_event_replay_sessions.create(session)
        
        await uow.commit()
        
        count = await uow.system_event_replay_sessions.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_sessions(self, uow, test_user):
        for i in range(3):
            session = SystemEventReplaySession(
                session_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                start_time="2026-01-01T00:00:00Z",
                end_time="2026-01-01T01:00:00Z",
                status="running" if i < 2 else "completed",
                started_at=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
            )
            await uow.system_event_replay_sessions.create(session)
        
        await uow.commit()
        
        active = await uow.system_event_replay_sessions.get_active_sessions()
        assert len(active) >= 2
        for s in active:
            assert s.status == "running"
