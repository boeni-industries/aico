"""TenantMembershipsRepository - PostgreSQL implementation."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional, List, Any

from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.tenant.models import TenantMembership
from aico.data.tables import tenant_memberships
from aico.data.repositories.base import Repository


class PostgresTenantMembershipsRepository(Repository[TenantMembership]):
    """PostgreSQL implementation of tenant memberships repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, entity: TenantMembership) -> TenantMembership:
        stmt = tenant_memberships.insert().values(
            membership_id=entity.membership_id,
            tenant_id=entity.tenant_id,
            user_id=entity.user_id,
            role=entity.role,
            created_at=entity.created_at or datetime.now(UTC),
        )
        await self.session.execute(stmt)
        return entity

    async def get_by_id(self, id: str) -> Optional[TenantMembership]:
        stmt = select(tenant_memberships).where(tenant_memberships.c.membership_id == id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return TenantMembership(**dict(row._mapping)) if row else None

    async def update(self, entity: TenantMembership) -> TenantMembership:
        stmt = (
            update(tenant_memberships)
            .where(tenant_memberships.c.membership_id == entity.membership_id)
            .values(
                role=entity.role,
            )
        )
        await self.session.execute(stmt)
        return entity

    async def delete(self, id: str) -> Any:
        stmt = delete(tenant_memberships).where(tenant_memberships.c.membership_id == id)
        await self.session.execute(stmt)

    async def list(
        self,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TenantMembership]:
        stmt = select(tenant_memberships)

        if filters:
            conditions = []
            if "tenant_id" in filters:
                conditions.append(tenant_memberships.c.tenant_id == filters["tenant_id"])
            if "user_id" in filters:
                conditions.append(tenant_memberships.c.user_id == filters["user_id"])
            if "role" in filters:
                role_value = filters["role"]
                if isinstance(role_value, list):
                    conditions.append(tenant_memberships.c.role.in_(role_value))
                else:
                    conditions.append(tenant_memberships.c.role == role_value)
            if conditions:
                stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(tenant_memberships.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [TenantMembership(**dict(row._mapping)) for row in result.fetchall()]

    async def count(self, filters: Optional[dict] = None) -> int:
        stmt = select(func.count()).select_from(tenant_memberships)

        if filters:
            conditions = []
            if "tenant_id" in filters:
                conditions.append(tenant_memberships.c.tenant_id == filters["tenant_id"])
            if "user_id" in filters:
                conditions.append(tenant_memberships.c.user_id == filters["user_id"])
            if "role" in filters:
                role_value = filters["role"]
                if isinstance(role_value, list):
                    conditions.append(tenant_memberships.c.role.in_(role_value))
                else:
                    conditions.append(tenant_memberships.c.role == role_value)
            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return result.scalar() or 0
