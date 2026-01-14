"""
KGNodeRepository - PostgreSQL implementation

Handles CRUD operations for knowledge graph nodes.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.kg.models import KGNode
from aico.data.tables import kg_nodes
from aico.data.repositories.base import Repository


class PostgresKGNodeRepository(Repository[KGNode]):
    """PostgreSQL implementation of KG node repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: KGNode) -> KGNode:
        """Create a new KG node."""
        from datetime import datetime as dt
        
        # Parse string timestamps to datetime objects if needed
        created_at = entity.created_at
        if isinstance(created_at, str):
            created_at = dt.fromisoformat(created_at.replace('Z', '+00:00'))
        elif not created_at:
            created_at = datetime.now(UTC)
            
        updated_at = entity.updated_at
        if isinstance(updated_at, str):
            updated_at = dt.fromisoformat(updated_at.replace('Z', '+00:00'))
        elif not updated_at:
            updated_at = datetime.now(UTC)
            
        valid_from = entity.valid_from
        if isinstance(valid_from, str):
            valid_from = dt.fromisoformat(valid_from.replace('Z', '+00:00'))
            
        valid_until = entity.valid_until
        if isinstance(valid_until, str):
            valid_until = dt.fromisoformat(valid_until.replace('Z', '+00:00'))
        
        stmt = kg_nodes.insert().values(
            id=entity.id,
            user_id=entity.user_id,
            label=entity.label,
            properties=entity.properties,
            confidence=entity.confidence,
            source_text=entity.source_text,
            created_at=created_at,
            updated_at=updated_at,
            language=entity.language,
            valid_from=valid_from,
            valid_until=valid_until,
            is_current=entity.is_current,
            canonical_id=entity.canonical_id,
            aliases_json=entity.aliases_json,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[KGNode]:
        """Get KG node by ID."""
        stmt = select(kg_nodes).where(kg_nodes.c.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return KGNode(
            id=row.id,
            user_id=row.user_id,
            label=row.label,
            properties=row.properties,
            confidence=row.confidence,
            source_text=row.source_text,
            created_at=row.created_at.isoformat() if row.created_at else None,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
            language=row.language,
            valid_from=row.valid_from.isoformat() if row.valid_from else None,
            valid_until=row.valid_until.isoformat() if row.valid_until else None,
            is_current=row.is_current,
            canonical_id=row.canonical_id,
            aliases_json=row.aliases_json,
        )
    
    async def update(self, entity: KGNode) -> KGNode:
        """Update an existing KG node."""
        from datetime import datetime as dt
        
        # Parse string timestamps to datetime objects if needed
        valid_from = entity.valid_from
        if isinstance(valid_from, str):
            valid_from = dt.fromisoformat(valid_from.replace('Z', '+00:00'))
        
        valid_until = entity.valid_until
        if isinstance(valid_until, str):
            valid_until = dt.fromisoformat(valid_until.replace('Z', '+00:00'))
        
        stmt = (
            update(kg_nodes)
            .where(kg_nodes.c.id == entity.id)
            .values(
                properties=entity.properties,
                confidence=entity.confidence,
                source_text=entity.source_text,
                updated_at=datetime.now(UTC),
                language=entity.language,
                valid_from=valid_from,
                valid_until=valid_until,
                is_current=entity.is_current,
                canonical_id=entity.canonical_id,
                aliases_json=entity.aliases_json,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a KG node."""
        stmt = delete(kg_nodes).where(kg_nodes.c.id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[KGNode]:
        """List KG nodes with optional filters."""
        stmt = select(kg_nodes)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(kg_nodes.c.user_id == filters['user_id'])
            if 'label' in filters:
                conditions.append(kg_nodes.c.label == filters['label'])
            if 'is_current' in filters:
                conditions.append(kg_nodes.c.is_current == filters['is_current'])
            if 'language' in filters:
                conditions.append(kg_nodes.c.language == filters['language'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(kg_nodes.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            KGNode(
                id=row.id,
                user_id=row.user_id,
                label=row.label,
                properties=row.properties,
                confidence=row.confidence,
                source_text=row.source_text,
                created_at=row.created_at.isoformat() if row.created_at else None,
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
                language=row.language,
                valid_from=row.valid_from.isoformat() if row.valid_from else None,
                valid_until=row.valid_until.isoformat() if row.valid_until else None,
                is_current=row.is_current,
                canonical_id=row.canonical_id,
                aliases_json=row.aliases_json,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count KG nodes with optional filters."""
        stmt = select(func.count()).select_from(kg_nodes)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(kg_nodes.c.user_id == filters['user_id'])
            if 'label' in filters:
                conditions.append(kg_nodes.c.label == filters['label'])
            if 'is_current' in filters:
                conditions.append(kg_nodes.c.is_current == filters['is_current'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_by_label_for_user(self, user_id: str, label: str) -> List[KGNode]:
        """Get all nodes with a specific label for a user."""
        stmt = select(kg_nodes).where(
            and_(
                kg_nodes.c.user_id == user_id,
                kg_nodes.c.label == label,
                kg_nodes.c.is_current == True
            )
        ).order_by(kg_nodes.c.confidence.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            KGNode(
                id=row.id,
                user_id=row.user_id,
                label=row.label,
                properties=row.properties,
                confidence=row.confidence,
                source_text=row.source_text,
                created_at=row.created_at,
                updated_at=row.updated_at,
                language=row.language,
                valid_from=row.valid_from,
                valid_until=row.valid_until,
                is_current=row.is_current,
                canonical_id=row.canonical_id,
                aliases_json=row.aliases_json,
            )
            for row in result.fetchall()
        ]
    
    async def mark_as_superseded(self, node_id: str) -> bool:
        """Mark a node as no longer current."""
        stmt = (
            update(kg_nodes)
            .where(kg_nodes.c.id == node_id)
            .values(
                is_current=False,
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
