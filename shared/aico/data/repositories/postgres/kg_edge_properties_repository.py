"""
KGEdgePropertiesRepository - PostgreSQL implementation

Handles CRUD operations for KG edge properties.
"""

from typing import Optional, List
from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.kg.models import KGEdgeProperty
from aico.data.tables import kg_edge_properties
from aico.data.repositories.base import Repository


class PostgresKGEdgePropertiesRepository(Repository[KGEdgeProperty]):
    """PostgreSQL implementation of KG edge properties repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: KGEdgeProperty) -> KGEdgeProperty:
        """Create a new edge property."""
        stmt = kg_edge_properties.insert().values(
            edge_id=entity.edge_id,
            key=entity.key,
            value=entity.value,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[KGEdgeProperty]:
        """Not applicable for composite key table."""
        raise NotImplementedError("Use get_edge_properties() instead")
    
    async def update(self, entity: KGEdgeProperty) -> KGEdgeProperty:
        """Not applicable - properties are immutable, delete and recreate instead."""
        raise NotImplementedError("Properties are immutable")
    
    async def delete(self, entity_id: str) -> bool:
        """Not applicable for composite key table."""
        raise NotImplementedError("Use delete_property() instead")
    
    async def delete_property(self, edge_id: str, key: str, value: str) -> bool:
        """Delete a specific edge property."""
        stmt = delete(kg_edge_properties).where(
            and_(
                kg_edge_properties.c.edge_id == edge_id,
                kg_edge_properties.c.key == key,
                kg_edge_properties.c.value == value
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[KGEdgeProperty]:
        """List edge properties with optional filters."""
        stmt = select(kg_edge_properties)
        
        if filters:
            conditions = []
            if 'edge_id' in filters:
                conditions.append(kg_edge_properties.c.edge_id == filters['edge_id'])
            if 'key' in filters:
                conditions.append(kg_edge_properties.c.key == filters['key'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            KGEdgeProperty(
                edge_id=row.edge_id,
                key=row.key,
                value=row.value,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count edge properties with optional filters."""
        stmt = select(func.count()).select_from(kg_edge_properties)
        
        if filters:
            conditions = []
            if 'edge_id' in filters:
                conditions.append(kg_edge_properties.c.edge_id == filters['edge_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_edge_properties(self, edge_id: str) -> List[KGEdgeProperty]:
        """Get all properties for a specific edge."""
        stmt = select(kg_edge_properties).where(kg_edge_properties.c.edge_id == edge_id)
        result = await self.session.execute(stmt)
        
        return [
            KGEdgeProperty(
                edge_id=row.edge_id,
                key=row.key,
                value=row.value,
            )
            for row in result.fetchall()
        ]
    
    async def find_by_property(self, key: str, value: str) -> List[KGEdgeProperty]:
        """Find edges by property key-value pair."""
        stmt = select(kg_edge_properties).where(
            and_(
                kg_edge_properties.c.key == key,
                kg_edge_properties.c.value == value
            )
        )
        result = await self.session.execute(stmt)
        
        return [
            KGEdgeProperty(
                edge_id=row.edge_id,
                key=row.key,
                value=row.value,
            )
            for row in result.fetchall()
        ]
