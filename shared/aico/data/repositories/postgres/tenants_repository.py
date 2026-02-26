"""TenantsRepository - PostgreSQL implementation."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional, List, Any

from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.tenant.models import Tenant
from aico.data.tables import tenants
from aico.data.repositories.base import Repository


class PostgresTenantsRepository(Repository[Tenant]):
    """PostgreSQL implementation of tenants repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, entity: Tenant) -> Tenant:
        now = datetime.now(UTC)
        stmt = tenants.insert().values(
            tenant_id=entity.tenant_id,
            tenant_type=entity.tenant_type,
            display_name=entity.display_name,
            status=entity.status,
            primary_language=entity.primary_language,
            metadata_json=entity.metadata_json,
            created_at=entity.created_at or now,
            updated_at=entity.updated_at or now,
        )
        await self.session.execute(stmt)
        return entity

    async def get_by_id(self, id: str) -> Optional[Tenant]:
        stmt = select(tenants).where(tenants.c.tenant_id == id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return Tenant(**dict(row._mapping)) if row else None

    async def update(self, entity: Tenant) -> Tenant:
        now = datetime.now(UTC)
        stmt = (
            update(tenants)
            .where(tenants.c.tenant_id == entity.tenant_id)
            .values(
                tenant_type=entity.tenant_type,
                display_name=entity.display_name,
                status=entity.status,
                primary_language=entity.primary_language,
                metadata_json=entity.metadata_json,
                updated_at=now,
            )
        )
        await self.session.execute(stmt)
        entity.updated_at = now
        return entity

    async def delete(self, id: str) -> Any:
        stmt = delete(tenants).where(tenants.c.tenant_id == id)
        await self.session.execute(stmt)

    async def list(
        self,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Tenant]:
        stmt = select(tenants)

        if filters:
            conditions = []
            if "status" in filters:
                status_value = filters["status"]
                if isinstance(status_value, list):
                    conditions.append(tenants.c.status.in_(status_value))
                else:
                    conditions.append(tenants.c.status == status_value)
            if "tenant_type" in filters:
                tenant_type_value = filters["tenant_type"]
                if isinstance(tenant_type_value, list):
                    conditions.append(tenants.c.tenant_type.in_(tenant_type_value))
                else:
                    conditions.append(tenants.c.tenant_type == tenant_type_value)
            if conditions:
                stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(tenants.c.updated_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [Tenant(**dict(row._mapping)) for row in result.fetchall()]

    async def count(self, filters: Optional[dict] = None) -> int:
        stmt = select(func.count()).select_from(tenants)

        if filters:
            conditions = []
            if "status" in filters:
                status_value = filters["status"]
                if isinstance(status_value, list):
                    conditions.append(tenants.c.status.in_(status_value))
                else:
                    conditions.append(tenants.c.status == status_value)
            if "tenant_type" in filters:
                tenant_type_value = filters["tenant_type"]
                if isinstance(tenant_type_value, list):
                    conditions.append(tenants.c.tenant_type.in_(tenant_type_value))
                else:
                    conditions.append(tenants.c.tenant_type == tenant_type_value)
            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return result.scalar() or 0
