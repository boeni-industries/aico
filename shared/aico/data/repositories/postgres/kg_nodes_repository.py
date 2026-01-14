"""
NodesRepository - PostgreSQL implementation

Handles CRUD operations for knowledge graph nodes.
"""

import json
from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.kg.models import KGNode as Node
from aico.data.tables import kg_nodes
from aico.data.repositories.base import Repository


class PostgresNodesRepository(Repository[Node]):
    """PostgreSQL implementation of KG nodes repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: Node) -> Node:
        """Create a new KG node."""
        from datetime import datetime
        now = datetime.now(UTC)
        
        # Handle datetime conversion - convert strings to datetime objects for DB
        created_at = entity.created_at if hasattr(entity, 'created_at') and entity.created_at else now
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        updated_at = entity.updated_at if hasattr(entity, 'updated_at') and entity.updated_at else now
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        
        # Convert valid_from/valid_until from ISO strings to datetime objects if needed
        valid_from = entity.valid_from
        if isinstance(valid_from, str):
            valid_from = datetime.fromisoformat(valid_from.replace('Z', '+00:00'))
        
        valid_until = entity.valid_until
        if isinstance(valid_until, str):
            valid_until = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))
        
        stmt = kg_nodes.insert().values(
            id=entity.id,
            user_id=entity.user_id,
            label=entity.label,
            properties=entity.properties if isinstance(entity.properties, str) else json.dumps(entity.properties),
            confidence=entity.confidence,
            source_text=entity.source_text,
            created_at=created_at,
            updated_at=updated_at,
            language=entity.language,
            valid_from=valid_from,
            valid_until=valid_until,
            is_current=entity.is_current,
            canonical_id=entity.canonical_id,
            aliases_json=entity.aliases_json if isinstance(entity.aliases_json, str) else (json.dumps(entity.aliases_json) if entity.aliases_json else None),
            reason=entity.reason,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[Node]:
        """Get KG node by ID."""
        stmt = select(kg_nodes).where(kg_nodes.c.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        # Construct Node directly to preserve database ID and timestamps
        return Node(
            id=row.id,
            user_id=row.user_id,
            label=row.label,
            properties=row.properties if isinstance(row.properties, str) else json.dumps(row.properties),
            confidence=row.confidence,
            source_text=row.source_text,
            created_at=row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else row.created_at,
            updated_at=row.updated_at.isoformat() if hasattr(row.updated_at, 'isoformat') else row.updated_at,
            language=row.language,
            valid_from=row.valid_from.isoformat() if hasattr(row.valid_from, 'isoformat') else row.valid_from,
            valid_until=row.valid_until.isoformat() if hasattr(row.valid_until, 'isoformat') else row.valid_until,
            is_current=row.is_current,
            canonical_id=row.canonical_id,
            aliases_json=row.aliases_json if isinstance(row.aliases_json, str) else (json.loads(row.aliases_json) if row.aliases_json else None),
            reason=row.reason,
        )
    
    async def update(self, entity: Node) -> Node:
        """Update an existing KG node."""
        from datetime import datetime as dt

        valid_until = entity.valid_until
        if isinstance(valid_until, str):
            valid_until = dt.fromisoformat(valid_until.replace('Z', '+00:00'))

        stmt = (
            update(kg_nodes)
            .where(kg_nodes.c.id == entity.id)
            .values(
                label=entity.label,
                properties=entity.properties if isinstance(entity.properties, str) else json.dumps(entity.properties),
                confidence=entity.confidence,
                source_text=entity.source_text,
                valid_until=valid_until,
                is_current=entity.is_current,
                canonical_id=entity.canonical_id,
                aliases_json=entity.aliases_json if isinstance(entity.aliases_json, str) else (json.dumps(entity.aliases_json) if entity.aliases_json else None),
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a KG node."""
        stmt = delete(kg_nodes).where(kg_nodes.c.id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[Node]:
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
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(kg_nodes.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            Node(
                id=row.id,
                user_id=row.user_id,
                label=row.label,
                properties=row.properties,
                confidence=row.confidence,
                source_text=row.source_text,
                created_at=row.created_at.isoformat() if row.created_at and hasattr(row.created_at, 'isoformat') else row.created_at,
                updated_at=row.updated_at.isoformat() if row.updated_at and hasattr(row.updated_at, 'isoformat') else row.updated_at,
                language=row.language,
                valid_from=row.valid_from.isoformat() if row.valid_from and hasattr(row.valid_from, 'isoformat') else row.valid_from,
                valid_until=row.valid_until.isoformat() if row.valid_until and hasattr(row.valid_until, 'isoformat') else row.valid_until,
                is_current=row.is_current,
                canonical_id=row.canonical_id,
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
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_nodes(self, user_id: str, label: Optional[str] = None) -> List[Node]:
        """Get current nodes for a user, optionally filtered by label."""
        conditions = [
            kg_nodes.c.user_id == user_id,
            kg_nodes.c.is_current == True
        ]
        
        if label:
            conditions.append(kg_nodes.c.label == label)
        
        stmt = select(kg_nodes).where(and_(*conditions)).order_by(kg_nodes.c.created_at.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            Node(
                id=row.id,
                user_id=row.user_id,
                label=row.label,
                properties=row.properties,
                confidence=row.confidence,
                source_text=row.source_text,
                created_at=row.created_at.isoformat() if row.created_at and hasattr(row.created_at, 'isoformat') else row.created_at,
                updated_at=row.updated_at.isoformat() if row.updated_at and hasattr(row.updated_at, 'isoformat') else row.updated_at,
                language=row.language,
                valid_from=row.valid_from.isoformat() if row.valid_from and hasattr(row.valid_from, 'isoformat') else row.valid_from,
                valid_until=row.valid_until.isoformat() if row.valid_until and hasattr(row.valid_until, 'isoformat') else row.valid_until,
                is_current=row.is_current,
                canonical_id=row.canonical_id,
            )
            for row in result.fetchall()
        ]
    
    async def get_by_label_for_user(self, user_id: str, label: str) -> List[Node]:
        """Get nodes by label for a specific user, ordered by confidence."""
        stmt = select(kg_nodes).where(
            and_(
                kg_nodes.c.user_id == user_id,
                kg_nodes.c.label == label,
                kg_nodes.c.is_current == True
            )
        ).order_by(kg_nodes.c.confidence.desc())
        
        result = await self.session.execute(stmt)
        
        return [
            Node(
                id=row.id,
                user_id=row.user_id,
                label=row.label,
                properties=row.properties if isinstance(row.properties, str) else json.dumps(row.properties),
                confidence=row.confidence,
                source_text=row.source_text,
                created_at=row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else row.created_at,
                updated_at=row.updated_at.isoformat() if hasattr(row.updated_at, 'isoformat') else row.updated_at,
                language=row.language,
                valid_from=row.valid_from.isoformat() if row.valid_from else None,
                valid_until=row.valid_until.isoformat() if row.valid_until else None,
                is_current=row.is_current,
                canonical_id=row.canonical_id,
                aliases_json=row.aliases_json if isinstance(row.aliases_json, str) else (json.dumps(row.aliases_json) if row.aliases_json else None),
                reason=row.reason,
            )
            for row in result.fetchall()
        ]
    
    async def mark_as_superseded(self, node_id: str, superseded_by: str) -> bool:
        """Mark a node as superseded by another node."""
        from datetime import datetime
        
        now = datetime.now(UTC)
        
        stmt = (
            update(kg_nodes)
            .where(kg_nodes.c.id == node_id)
            .values(
                is_current=False,
                valid_until=now,
                canonical_id=superseded_by,
                updated_at=now,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
