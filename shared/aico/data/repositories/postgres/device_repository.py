"""
DeviceRepository - PostgreSQL implementation

Handles CRUD operations for auth devices.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.auth.models import Device
from aico.data.tables import auth_devices
from aico.data.repositories.base import Repository


class PostgresDeviceRepository(Repository[Device]):
    """PostgreSQL implementation of device repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: Device) -> Device:
        """Create a new device."""
        stmt = auth_devices.insert().values(
            uuid=entity.uuid,
            device_name=entity.device_name,
            device_type=entity.device_type,
            platform=entity.platform,
            is_active=entity.is_active,
            last_seen=entity.last_seen,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Device]:
        """Get device by ID."""
        stmt = select(auth_devices).where(auth_devices.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return Device(
            uuid=row.uuid,
            device_name=row.device_name,
            device_type=row.device_type,
            platform=row.platform,
            is_active=row.is_active,
            last_seen=row.last_seen,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    
    async def update(self, entity: Device) -> Device:
        """Update an existing device."""
        stmt = (
            update(auth_devices)
            .where(auth_devices.c.uuid == entity.uuid)
            .values(
                device_name=entity.device_name,
                device_type=entity.device_type,
                platform=entity.platform,
                is_active=entity.is_active,
                last_seen=entity.last_seen,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a device."""
        stmt = delete(auth_devices).where(auth_devices.c.uuid == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Device]:
        """List devices with optional filters."""
        stmt = select(auth_devices)
        
        if filters:
            conditions = []
            if 'is_active' in filters:
                conditions.append(auth_devices.c.is_active == filters['is_active'])
            if 'platform' in filters:
                conditions.append(auth_devices.c.platform == filters['platform'])
            if 'device_type' in filters:
                conditions.append(auth_devices.c.device_type == filters['device_type'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(auth_devices.c.last_seen.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            Device(
                uuid=row.uuid,
                device_name=row.device_name,
                device_type=row.device_type,
                platform=row.platform,
                is_active=row.is_active,
                last_seen=row.last_seen,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count devices with optional filters."""
        stmt = select(func.count()).select_from(auth_devices)
        
        if filters:
            conditions = []
            if 'is_active' in filters:
                conditions.append(auth_devices.c.is_active == filters['is_active'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_active_devices(self) -> List[Device]:
        """Get all active devices."""
        stmt = select(auth_devices).where(
            auth_devices.c.is_active == True
        ).order_by(auth_devices.c.last_seen.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            Device(
                uuid=row.uuid,
                device_name=row.device_name,
                device_type=row.device_type,
                platform=row.platform,
                is_active=row.is_active,
                last_seen=row.last_seen,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.fetchall()
        ]
    
    async def update_last_seen(self, device_id: str) -> bool:
        """Update device last_seen timestamp."""
        stmt = (
            update(auth_devices)
            .where(auth_devices.c.uuid == device_id)
            .values(
                last_seen=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def deactivate_device(self, device_id: str) -> bool:
        """Deactivate a device."""
        stmt = (
            update(auth_devices)
            .where(auth_devices.c.uuid == device_id)
            .values(
                is_active=False,
                updated_at=datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
