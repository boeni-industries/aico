"""
Integration tests for DeviceRepository.

Tests DeviceRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC, timedelta

from aico.data.auth.models import Device
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


class TestDeviceRepository:
    """Test DeviceRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_device(self, uow):
        """Test creating a new device."""
        device = Device(
            uuid=str(uuid.uuid4()),
            device_name="Test iPhone",
            device_type="mobile",
            platform="iOS",
            is_active=True,
        )
        
        created = await uow.devices.create(device)
        await uow.commit()
        
        assert created.uuid == device.uuid
        assert created.device_name == "Test iPhone"
        assert created.platform == "iOS"
    
    @pytest.mark.asyncio
    async def test_get_device_by_id(self, uow):
        """Test retrieving device by ID."""
        device = Device(
            uuid=str(uuid.uuid4()),
            device_name="Test Android",
            device_type="mobile",
            platform="Android",
        )
        
        await uow.devices.create(device)
        await uow.commit()
        
        found = await uow.devices.get_by_id(device.uuid)
        assert found is not None
        assert found.uuid == device.uuid
        assert found.device_name == "Test Android"
    
    @pytest.mark.asyncio
    async def test_update_device(self, uow):
        """Test updating a device."""
        device = Device(
            uuid=str(uuid.uuid4()),
            device_name="Old Name",
            device_type="mobile",
            platform="iOS",
        )
        
        await uow.devices.create(device)
        await uow.commit()
        
        # Update the device
        device.device_name = "New Name"
        device.platform = "iOS 17"
        updated = await uow.devices.update(device)
        await uow.commit()
        
        assert updated.device_name == "New Name"
        
        # Verify update persisted
        found = await uow.devices.get_by_id(device.uuid)
        assert found.device_name == "New Name"
        assert found.platform == "iOS 17"
    
    @pytest.mark.asyncio
    async def test_delete_device(self, uow):
        """Test deleting a device."""
        device = Device(
            uuid=str(uuid.uuid4()),
            device_name="Delete Me",
            device_type="mobile",
            platform="Android",
        )
        
        await uow.devices.create(device)
        await uow.commit()
        
        # Delete the device
        success = await uow.devices.delete(device.uuid)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.devices.get_by_id(device.uuid)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_devices(self, uow):
        """Test listing devices with filters."""
        for i in range(3):
            device = Device(
                uuid=str(uuid.uuid4()),
                device_name=f"Device {i}",
                device_type="mobile" if i < 2 else "desktop",
                platform="iOS" if i == 0 else "Android",
                is_active=i < 2,
            )
            await uow.devices.create(device)
        
        await uow.commit()
        
        # List all devices
        all_devices = await uow.devices.list()
        assert len(all_devices) >= 3
        
        # List only active devices
        active_devices = await uow.devices.list(filters={"is_active": True})
        assert len(active_devices) >= 2
        
        # List by platform
        ios_devices = await uow.devices.list(filters={"platform": "iOS"})
        assert len(ios_devices) >= 1
    
    @pytest.mark.asyncio
    async def test_count_devices(self, uow):
        """Test counting devices."""
        for i in range(3):
            device = Device(
                uuid=str(uuid.uuid4()),
                device_name=f"Count Device {i}",
                device_type="mobile",
                platform="iOS",
                is_active=True,
            )
            await uow.devices.create(device)
        
        await uow.commit()
        
        count = await uow.devices.count()
        assert count >= 3
        
        # Count active devices
        active_count = await uow.devices.count(filters={"is_active": True})
        assert active_count >= 3
    
    @pytest.mark.asyncio
    async def test_get_active_devices(self, uow):
        """Test getting all active devices."""
        for i in range(3):
            device = Device(
                uuid=str(uuid.uuid4()),
                device_name=f"Active Device {i}",
                device_type="mobile",
                platform="iOS",
                is_active=i < 2,
            )
            await uow.devices.create(device)
        
        await uow.commit()
        
        active_devices = await uow.devices.get_active_devices()
        assert len(active_devices) >= 2
        for device in active_devices:
            assert device.is_active is True
    
    @pytest.mark.asyncio
    async def test_update_last_seen(self, uow):
        """Test updating device last_seen timestamp."""
        device = Device(
            uuid=str(uuid.uuid4()),
            device_name="Last Seen Test",
            device_type="mobile",
            platform="iOS",
            last_seen=datetime.now(UTC) - timedelta(hours=1),
        )
        
        await uow.devices.create(device)
        await uow.commit()
        
        # Update last_seen
        success = await uow.devices.update_last_seen(device.uuid)
        await uow.commit()
        
        assert success is True
        
        # Verify last_seen was updated
        found = await uow.devices.get_by_id(device.uuid)
        assert found.last_seen is not None
        # Should be very recent (within last minute)
        time_diff = datetime.now(UTC) - found.last_seen
        assert time_diff.total_seconds() < 60
    
    @pytest.mark.asyncio
    async def test_deactivate_device(self, uow):
        """Test deactivating a device."""
        device = Device(
            uuid=str(uuid.uuid4()),
            device_name="Deactivate Test",
            device_type="mobile",
            platform="Android",
            is_active=True,
        )
        
        await uow.devices.create(device)
        await uow.commit()
        
        # Deactivate the device
        success = await uow.devices.deactivate_device(device.uuid)
        await uow.commit()
        
        assert success is True
        
        # Verify it's deactivated
        found = await uow.devices.get_by_id(device.uuid)
        assert found.is_active is False
