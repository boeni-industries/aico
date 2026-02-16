"""
Integration tests for AuthDevicesRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.auth.device_models import Device
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


class TestAuthDevicesRepository:
    
    @pytest.mark.asyncio
    async def test_create_device(self, uow):
        device = Device(
            uuid=str(uuid.uuid4()),
            device_name="Test Device",
            device_type="mobile",
            platform="iOS",
            is_active=True,
        )
        
        created = await uow.auth_devices.create(device)
        await uow.commit()
        
        assert created.uuid == device.uuid
        assert created.device_name == "Test Device"
    
    @pytest.mark.asyncio
    async def test_get_device_by_id(self, uow):
        device = Device(
            uuid=str(uuid.uuid4()),
            device_name="Get Test Device",
            device_type="tablet",
            platform="Android",
            is_active=True,
        )
        
        await uow.auth_devices.create(device)
        await uow.commit()
        
        found = await uow.auth_devices.get_by_id(device.uuid)
        assert found is not None
        assert found.platform == "Android"
    
    @pytest.mark.asyncio
    async def test_update_device(self, uow):
        device = Device(
            uuid=str(uuid.uuid4()),
            device_name="Update Test",
            device_type="desktop",
            platform="Windows",
            is_active=True,
        )
        
        await uow.auth_devices.create(device)
        await uow.commit()
        
        device.is_active = False
        device.last_seen = datetime.now(UTC)
        updated = await uow.auth_devices.update(device)
        await uow.commit()
        
        assert updated.is_active is False
        
        found = await uow.auth_devices.get_by_id(device.uuid)
        assert found.is_active is False
    
    @pytest.mark.asyncio
    async def test_delete_device(self, uow):
        device = Device(
            uuid=str(uuid.uuid4()),
            device_name="Delete Test",
            device_type="mobile",
            platform="iOS",
            is_active=True,
        )
        
        await uow.auth_devices.create(device)
        await uow.commit()
        
        success = await uow.auth_devices.delete(device.uuid)
        await uow.commit()
        
        assert success is True
        
        found = await uow.auth_devices.get_by_id(device.uuid)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_devices(self, uow):
        for i in range(3):
            device = Device(
                uuid=str(uuid.uuid4()),
                device_name=f"List Device {i}",
                device_type="mobile",
                platform="iOS",
                is_active=True if i < 2 else False,
            )
            await uow.auth_devices.create(device)
        
        await uow.commit()
        
        all_devices = await uow.auth_devices.list()
        assert len(all_devices) >= 3
        
        active = await uow.auth_devices.list(filters={"is_active": True})
        assert len(active) >= 2
    
    @pytest.mark.asyncio
    async def test_count_devices(self, uow):
        for i in range(3):
            device = Device(
                uuid=str(uuid.uuid4()),
                device_name=f"Count Device {i}",
                device_type="mobile",
                platform="Android",
                is_active=True,
            )
            await uow.auth_devices.create(device)
        
        await uow.commit()
        
        count = await uow.auth_devices.count(filters={"is_active": True})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_devices(self, uow):
        for i in range(3):
            device = Device(
                uuid=str(uuid.uuid4()),
                device_name=f"Active Device {i}",
                device_type="mobile",
                platform="iOS",
                is_active=True if i < 2 else False,
                last_seen=datetime.now(UTC) if i < 2 else None,
            )
            await uow.auth_devices.create(device)
        
        await uow.commit()
        
        active = await uow.auth_devices.get_active_devices()
        assert len(active) >= 2
        for dev in active:
            assert dev.is_active is True
