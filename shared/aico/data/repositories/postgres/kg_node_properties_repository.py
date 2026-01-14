"""
KGNodePropertiesRepository - PostgreSQL implementation

Handles CRUD operations for KG node properties.
"""

from typing import Optional, List
from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.knowledge_graph.models import KGNodeProperty
from aico.data.tables import kg_node_properties
from aico.data.repositories.base import Repository


class PostgresKGNodePropertiesRepository(Repository[KGNodeProperty]):
    """PostgreSQL implementation of KG node properties repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: KGNodeProperty) -> KGNodeProperty:
        """Create a new node property."""
        stmt = kg_node_properties.insert().values(
            node_id=entity.node_id,
            key=entity.key,
            value=entity.value,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[KGNodeProperty]:
        """Not applicable for composite key table."""
        raise NotImplementedError("Use get_node_properties() instead")
    
    async def update(self, entity: KGNodeProperty) -> KGNodeProperty:
        """Not applicable - properties are immutable, delete and recreate instead."""
        raise NotImplementedError("Properties are immutable")
    
    async def delete(self, entity_id: str) -> bool:
        """Not applicable for composite key table."""
        raise NotImplementedError("Use delete_property() instead")
    
    async def delete_property(self, node_id: str, key: str, value: str) -> bool:
        """Delete a specific node property."""
        stmt = delete(kg_node_properties).where(
            and_(
                kg_node_properties.c.node_id == node_id,
                kg_node_properties.c.key == key,
                kg_node_properties.c.value == value
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[KGNodeProperty]:
        """List node properties with optional filters."""
        stmt = select(kg_node_properties)
        
        if filters:
            conditions = []
            if 'node_id' in filters:
                conditions.append(kg_node_properties.c.node_id == filters['node_id'])
            if 'key' in filters:
                conditions.append(kg_node_properties.c.key == filters['key'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            KGNodeProperty(
                node_id=row.node_id,
                key=row.key,
                value=row.value,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count node properties with optional filters."""
        stmt = select(func.count()).select_from(kg_node_properties)
        
        if filters:
            conditions = []
            if 'node_id' in filters:
                conditions.append(kg_node_properties.c.node_id == filters['node_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_node_properties(self, node_id: str) -> List[KGNodeProperty]:
        """Get all properties for a specific node."""
        stmt = select(kg_node_properties).where(kg_node_properties.c.node_id == node_id)
        result = await self.session.execute(stmt)
        
        return [
            KGNodeProperty(
                node_id=row.node_id,
                key=row.key,
                value=row.value,
            )
            for row in result.fetchall()
        ]
    
    async def find_by_property(self, key: str, value: str) -> List[KGNodeProperty]:
        """Find nodes by property key-value pair."""
        stmt = select(kg_node_properties).where(
            and_(
                kg_node_properties.c.key == key,
                kg_node_properties.c.value == value
            )
        )
        result = await self.session.execute(stmt)
        
        return [
            KGNodeProperty(
                node_id=row.node_id,
                key=row.key,
                value=row.value,
            )
            for row in result.fetchall()
        ]
