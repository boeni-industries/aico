"""
EdgesRepository - PostgreSQL implementation

Handles CRUD operations for knowledge graph edges.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.ai.knowledge_graph.models import Edge
from aico.data.tables import kg_edges
from aico.data.repositories.base import Repository


class PostgresEdgesRepository(Repository[Edge]):
    """PostgreSQL implementation of KG edges repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: Edge) -> Edge:
        """Create a new KG edge."""
        from datetime import datetime
        
        # Convert ISO string timestamps to datetime objects
        created_at = datetime.fromisoformat(entity.created_at) if isinstance(entity.created_at, str) else entity.created_at
        updated_at = datetime.fromisoformat(entity.updated_at) if isinstance(entity.updated_at, str) else entity.updated_at
        valid_from = datetime.fromisoformat(entity.valid_from) if entity.valid_from and isinstance(entity.valid_from, str) else entity.valid_from
        valid_until = datetime.fromisoformat(entity.valid_until) if entity.valid_until and isinstance(entity.valid_until, str) else entity.valid_until
        
        stmt = kg_edges.insert().values(
            id=entity.id,
            user_id=entity.user_id,
            source_id=entity.source_id,
            target_id=entity.target_id,
            relation_type=entity.relation_type,
            properties=entity.properties,
            confidence=entity.confidence,
            source_text=entity.source_text,
            created_at=created_at,
            updated_at=updated_at,
            valid_from=valid_from,
            valid_until=valid_until,
            is_current=entity.is_current,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Edge]:
        """Get KG edge by ID."""
        stmt = select(kg_edges).where(kg_edges.c.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        # Construct Edge directly to preserve database ID and timestamps
        return Edge(
            id=row.id,
            user_id=row.user_id,
            source_id=row.source_id,
            target_id=row.target_id,
            relation_type=row.relation_type,
            properties=row.properties,
            confidence=row.confidence,
            source_text=row.source_text,
            created_at=row.created_at.isoformat() if row.created_at and hasattr(row.created_at, 'isoformat') else row.created_at,
            updated_at=row.updated_at.isoformat() if row.updated_at and hasattr(row.updated_at, 'isoformat') else row.updated_at,
            valid_from=row.valid_from.isoformat() if row.valid_from and hasattr(row.valid_from, 'isoformat') else row.valid_from,
            valid_until=row.valid_until.isoformat() if row.valid_until and hasattr(row.valid_until, 'isoformat') else row.valid_until,
            is_current=row.is_current,
        )
    
    async def update(self, entity: Edge) -> Edge:
        """Update an existing KG edge."""
        stmt = (
            update(kg_edges)
            .where(kg_edges.c.id == entity.id)
            .values(
                properties=entity.properties,
                confidence=entity.confidence,
                updated_at=entity.updated_at,
                valid_until=entity.valid_until,
                is_current=entity.is_current,
                reason=entity.reason,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a KG edge."""
        stmt = delete(kg_edges).where(kg_edges.c.id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Edge]:
        """List KG edges with optional filters."""
        stmt = select(kg_edges)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(kg_edges.c.user_id == filters['user_id'])
            if 'relation_type' in filters:
                conditions.append(kg_edges.c.relation_type == filters['relation_type'])
            if 'is_current' in filters:
                conditions.append(kg_edges.c.is_current == filters['is_current'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(kg_edges.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            Edge(
                id=row.id,
                user_id=row.user_id,
                source_id=row.source_id,
                target_id=row.target_id,
                relation_type=row.relation_type,
                properties=row.properties,
                confidence=row.confidence,
                source_text=row.source_text,
                created_at=row.created_at.isoformat() if row.created_at else None,
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
                valid_from=row.valid_from.isoformat() if row.valid_from else None,
                valid_until=row.valid_until.isoformat() if row.valid_until else None,
                is_current=row.is_current,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count KG edges with optional filters."""
        stmt = select(func.count()).select_from(kg_edges)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(kg_edges.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_node_edges(self, node_id: str, direction: str = 'both') -> List[Edge]:
        """Get edges connected to a node."""
        if direction == 'outgoing':
            conditions = [kg_edges.c.source_id == node_id, kg_edges.c.is_current == True]
        elif direction == 'incoming':
            conditions = [kg_edges.c.target_id == node_id, kg_edges.c.is_current == True]
        else:  # both
            conditions = [
                and_(
                    (kg_edges.c.source_id == node_id) | (kg_edges.c.target_id == node_id),
                    kg_edges.c.is_current == True
                )
            ]
        
        stmt = select(kg_edges).where(and_(*conditions)).order_by(kg_edges.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            Edge(
                id=row.id,
                user_id=row.user_id,
                source_id=row.source_id,
                target_id=row.target_id,
                relation_type=row.relation_type,
                properties=row.properties,
                confidence=row.confidence,
                source_text=row.source_text,
                created_at=row.created_at.isoformat() if row.created_at else None,
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
                valid_from=row.valid_from.isoformat() if row.valid_from else None,
                valid_until=row.valid_until.isoformat() if row.valid_until else None,
                is_current=row.is_current,
            )
            for row in result.fetchall()
        ]
