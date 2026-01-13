"""
KGEdgeRepository - PostgreSQL implementation

Handles CRUD operations for knowledge graph edges.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.kg.models import KGEdge
from aico.data.tables import kg_edges
from aico.data.repositories.base import Repository


class PostgresKGEdgeRepository(Repository[KGEdge]):
    """PostgreSQL implementation of KG edge repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: KGEdge) -> KGEdge:
        """Create a new KG edge."""
        stmt = kg_edges.insert().values(
            id=entity.id,
            user_id=entity.user_id,
            source_id=entity.source_id,
            target_id=entity.target_id,
            relation_type=entity.relation_type,
            properties=entity.properties,
            confidence=entity.confidence,
            source_text=entity.source_text,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
            valid_from=entity.valid_from,
            valid_until=entity.valid_until,
            is_current=entity.is_current,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[KGEdge]:
        """Get KG edge by ID."""
        stmt = select(kg_edges).where(kg_edges.c.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return KGEdge(
            id=row.id,
            user_id=row.user_id,
            source_id=row.source_id,
            target_id=row.target_id,
            relation_type=row.relation_type,
            properties=row.properties,
            confidence=row.confidence,
            source_text=row.source_text,
            created_at=row.created_at,
            updated_at=row.updated_at,
            valid_from=row.valid_from,
            valid_until=row.valid_until,
            is_current=row.is_current,
        )
    
    async def update(self, entity: KGEdge) -> KGEdge:
        """Update an existing KG edge."""
        stmt = (
            update(kg_edges)
            .where(kg_edges.c.id == entity.id)
            .values(
                properties=entity.properties,
                confidence=entity.confidence,
                source_text=entity.source_text,
                updated_at=datetime.now(UTC),
                valid_from=entity.valid_from,
                valid_until=entity.valid_until,
                is_current=entity.is_current,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a KG edge."""
        stmt = delete(kg_edges).where(kg_edges.c.id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[KGEdge]:
        """List KG edges with optional filters."""
        stmt = select(kg_edges)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(kg_edges.c.user_id == filters['user_id'])
            if 'source_id' in filters:
                conditions.append(kg_edges.c.source_id == filters['source_id'])
            if 'target_id' in filters:
                conditions.append(kg_edges.c.target_id == filters['target_id'])
            if 'relation_type' in filters:
                conditions.append(kg_edges.c.relation_type == filters['relation_type'])
            if 'is_current' in filters:
                conditions.append(kg_edges.c.is_current == filters['is_current'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(kg_edges.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            KGEdge(
                id=row.id,
                user_id=row.user_id,
                source_id=row.source_id,
                target_id=row.target_id,
                relation_type=row.relation_type,
                properties=row.properties,
                confidence=row.confidence,
                source_text=row.source_text,
                created_at=row.created_at,
                updated_at=row.updated_at,
                valid_from=row.valid_from,
                valid_until=row.valid_until,
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
            if 'source_id' in filters:
                conditions.append(kg_edges.c.source_id == filters['source_id'])
            if 'target_id' in filters:
                conditions.append(kg_edges.c.target_id == filters['target_id'])
            if 'is_current' in filters:
                conditions.append(kg_edges.c.is_current == filters['is_current'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_edges_for_node(self, node_id: str, direction: str = 'both') -> List[KGEdge]:
        """Get all edges connected to a node.
        
        Args:
            node_id: The node ID
            direction: 'outgoing', 'incoming', or 'both'
        """
        if direction == 'outgoing':
            conditions = [kg_edges.c.source_id == node_id]
        elif direction == 'incoming':
            conditions = [kg_edges.c.target_id == node_id]
        else:  # both
            conditions = [
                or_(
                    kg_edges.c.source_id == node_id,
                    kg_edges.c.target_id == node_id
                )
            ]
        
        conditions.append(kg_edges.c.is_current == True)
        
        stmt = select(kg_edges).where(and_(*conditions)).order_by(kg_edges.c.confidence.desc())
        result = await self.session.execute(stmt)
        
        return [
            KGEdge(
                id=row.id,
                user_id=row.user_id,
                source_id=row.source_id,
                target_id=row.target_id,
                relation_type=row.relation_type,
                properties=row.properties,
                confidence=row.confidence,
                source_text=row.source_text,
                created_at=row.created_at,
                updated_at=row.updated_at,
                valid_from=row.valid_from,
                valid_until=row.valid_until,
                is_current=row.is_current,
            )
            for row in result.fetchall()
        ]
    
    async def get_edges_by_relation_type(self, user_id: str, relation_type: str) -> List[KGEdge]:
        """Get all edges of a specific relation type for a user."""
        stmt = select(kg_edges).where(
            and_(
                kg_edges.c.user_id == user_id,
                kg_edges.c.relation_type == relation_type,
                kg_edges.c.is_current == True
            )
        ).order_by(kg_edges.c.confidence.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            KGEdge(
                id=row.id,
                user_id=row.user_id,
                source_id=row.source_id,
                target_id=row.target_id,
                relation_type=row.relation_type,
                properties=row.properties,
                confidence=row.confidence,
                source_text=row.source_text,
                created_at=row.created_at,
                updated_at=row.updated_at,
                valid_from=row.valid_from,
                valid_until=row.valid_until,
                is_current=row.is_current,
            )
            for row in result.fetchall()
        ]
    
    async def mark_as_superseded(self, edge_id: str) -> bool:
        """Mark an edge as no longer current."""
        stmt = (
            update(kg_edges)
            .where(kg_edges.c.id == edge_id)
            .values(
                is_current=False,
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
