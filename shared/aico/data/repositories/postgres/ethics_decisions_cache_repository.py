"""
EthicsDecisionsCacheRepository - PostgreSQL implementation

Handles CRUD operations for ethics decisions cache.
"""

from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from aico.data.ethics.cache_models import EthicsDecisionsCache
from aico.data.tables import ethics_decisions_cache
from aico.data.repositories.base import Repository


class PostgresEthicsDecisionsCacheRepository(Repository[EthicsDecisionsCache]):
    """PostgreSQL implementation of ethics decisions cache repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: EthicsDecisionsCache) -> EthicsDecisionsCache:
        """Create a new cache entry."""
        stmt = ethics_decisions_cache.insert().values(
            cache_id=entity.cache_id,
            user_id=entity.user_id,
            target_type=entity.target_type,
            target_id=entity.target_id,
            decision=entity.decision,
            reasoning=entity.reasoning,
            policy_rules_applied=entity.policy_rules_applied,
            confidence=entity.confidence,
            cached_at=entity.cached_at,
            expires_at=entity.expires_at,
            hit_count=entity.hit_count,
            last_hit_at=entity.last_hit_at,
        )
        await self.session.execute(stmt)
        return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[EthicsDecisionsCache]:
        """Get cache entry by ID."""
        stmt = select(ethics_decisions_cache).where(ethics_decisions_cache.c.cache_id == entity_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return EthicsDecisionsCache(
            cache_id=row.cache_id,
            user_id=row.user_id,
            target_type=row.target_type,
            target_id=row.target_id,
            decision=row.decision,
            reasoning=row.reasoning,
            policy_rules_applied=row.policy_rules_applied,
            confidence=row.confidence,
            cached_at=row.cached_at,
            expires_at=row.expires_at,
            hit_count=row.hit_count,
            last_hit_at=row.last_hit_at,
        )
    
    async def update(self, entity: EthicsDecisionsCache) -> EthicsDecisionsCache:
        """Update an existing cache entry."""
        stmt = (
            update(ethics_decisions_cache)
            .where(ethics_decisions_cache.c.cache_id == entity.cache_id)
            .values(
                hit_count=entity.hit_count,
                last_hit_at=entity.last_hit_at,
                expires_at=entity.expires_at,
            )
        )
        await self.session.execute(stmt)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a cache entry."""
        stmt = delete(ethics_decisions_cache).where(ethics_decisions_cache.c.cache_id == entity_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def list(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[EthicsDecisionsCache]:
        """List cache entries with optional filters."""
        stmt = select(ethics_decisions_cache)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ethics_decisions_cache.c.user_id == filters['user_id'])
            if 'target_type' in filters:
                conditions.append(ethics_decisions_cache.c.target_type == filters['target_type'])
            if 'decision' in filters:
                conditions.append(ethics_decisions_cache.c.decision == filters['decision'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ethics_decisions_cache.c.cached_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        return [
            EthicsDecisionsCache(
                cache_id=row.cache_id,
                user_id=row.user_id,
                target_type=row.target_type,
                target_id=row.target_id,
                decision=row.decision,
                reasoning=row.reasoning,
                policy_rules_applied=row.policy_rules_applied,
                confidence=row.confidence,
                cached_at=row.cached_at,
                expires_at=row.expires_at,
                hit_count=row.hit_count,
                last_hit_at=row.last_hit_at,
            )
            for row in result.fetchall()
        ]
    
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count cache entries with optional filters."""
        stmt = select(func.count()).select_from(ethics_decisions_cache)
        
        if filters:
            conditions = []
            if 'user_id' in filters:
                conditions.append(ethics_decisions_cache.c.user_id == filters['user_id'])
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_cached_decision(self, user_id: str, target_type: str, target_id: str) -> Optional[EthicsDecisionsCache]:
        """Get cached decision for a specific target."""
        stmt = select(ethics_decisions_cache).where(
            and_(
                ethics_decisions_cache.c.user_id == user_id,
                ethics_decisions_cache.c.target_type == target_type,
                ethics_decisions_cache.c.target_id == target_id
            )
        )
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        return EthicsDecisionsCache(
            cache_id=row.cache_id,
            user_id=row.user_id,
            target_type=row.target_type,
            target_id=row.target_id,
            decision=row.decision,
            reasoning=row.reasoning,
            policy_rules_applied=row.policy_rules_applied,
            confidence=row.confidence,
            cached_at=row.cached_at,
            expires_at=row.expires_at,
            hit_count=row.hit_count,
            last_hit_at=row.last_hit_at,
        )
