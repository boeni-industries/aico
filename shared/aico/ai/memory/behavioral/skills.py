"""
Skill Library Management

Manages skill definitions, storage, and retrieval for behavioral learning.
"""

import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from aico.core.logging import get_logger
from .models import Skill, UserSkillConfidence

logger = get_logger("shared.memory.behavioral.skills")


class SkillStore:
    """
    Manages skill library with CRUD operations.
    
    Skills are stored in PostgreSQL database via UoW pattern.
    """
    
    def __init__(self, uow_factory):
        """
        Initialize skill store.
        
        Args:
            uow_factory: Unit of Work factory for PostgreSQL access
        """
        self.uow_factory = uow_factory
    
    async def create_skill(self, skill: Skill) -> Skill:
        """
        Create new skill in database.
        
        Args:
            skill: Skill object to create
            
        Returns:
            Created skill with timestamps
        """
        async with self.uow_factory() as uow:
            await uow.ams_behavioral_skills.create(skill)
            await uow.commit()
        
        logger.info(f"Created skill: {skill.skill_id}", extra={
            "skill_id": skill.skill_id,
            "skill_type": skill.skill_type
        })
        
        return skill
    
    async def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID."""
        async with self.uow_factory() as uow:
            return await uow.ams_behavioral_skills.get_by_id(skill_id)
    
    async def list_skills(
        self,
        skill_type: Optional[str] = None,
        language: Optional[str] = None
    ) -> List[Skill]:
        """
        List skills with optional filters.
        
        Args:
            skill_type: Filter by skill type
            language: Filter by supported language
            
        Returns:
            List of matching skills
        """
        filters = {}
        if skill_type:
            filters['skill_type'] = skill_type
        
        async with self.uow_factory() as uow:
            skills = await uow.ams_behavioral_skills.list(filters=filters, limit=1000)
        
        # Filter by language if specified (done in Python since it's a JSON field)
        if language:
            skills = [s for s in skills if language in s.supported_languages]
        
        return skills
    
    async def update_skill(self, skill: Skill) -> Skill:
        """Update existing skill."""
        async with self.uow_factory() as uow:
            await uow.ams_behavioral_skills.update(skill)
            await uow.commit()
        
        logger.info(f"Updated skill: {skill.skill_id}")
        return skill
    
    async def delete_skill(self, skill_id: str) -> bool:
        """Delete skill by ID."""
        async with self.uow_factory() as uow:
            result = await uow.ams_behavioral_skills.delete(skill_id)
            await uow.commit()
        
        logger.info(f"Deleted skill: {skill_id}")
        return result
    
    async def initialize_base_skills(self) -> None:
        """
        Initialize base skills if they don't exist.
        
        This is called during MemoryManager initialization to ensure
        the skill library has default skills available.
        """
        # Check if any skills exist
        existing_skills = await self.list_skills()
        
        if existing_skills:
            logger.info(f"Skill library already initialized with {len(existing_skills)} skills")
            return
        
        logger.info("Initializing base skill library...")
        
        # Base skills can be added here if needed
        # For now, we just log that initialization is complete
        # Skills will be added dynamically as the system learns
        
        logger.info("Base skill library initialized (empty - skills will be learned)")
    
    async def get_user_skill_confidence(
        self,
        user_id: str,
        skill_id: str
    ) -> Optional[UserSkillConfidence]:
        """Get user's confidence level for a skill."""
        async with self.uow_factory() as uow:
            # Query user_skill_confidence table
            confidences = await uow.user_skill_confidence.list(
                filters={'user_id': user_id, 'skill_id': skill_id},
                limit=1
            )
            return confidences[0] if confidences else None
    
    async def update_user_skill_confidence(
        self,
        user_id: str,
        skill_id: str,
        confidence_score: float,
        execution_count: int
    ) -> UserSkillConfidence:
        """Update user's confidence level for a skill."""
        async with self.uow_factory() as uow:
            # Check if exists
            existing = await self.get_user_skill_confidence(user_id, skill_id)
            
            if existing:
                existing.confidence_score = confidence_score
                existing.execution_count = execution_count
                existing.updated_at = datetime.utcnow()
                await uow.user_skill_confidence.update(existing)
                await uow.commit()
                return existing
            else:
                # Create new
                new_confidence = UserSkillConfidence(
                    user_id=user_id,
                    skill_id=skill_id,
                    confidence_score=confidence_score,
                    execution_count=execution_count,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                await uow.user_skill_confidence.create(new_confidence)
                await uow.commit()
                return new_confidence
    
    async def get_recommended_skills(
        self,
        context: Dict[str, Any],
        user_id: str,
        top_k: int = 5
    ) -> List[Skill]:
        """
        Get recommended skills based on context.
        
        Args:
            context: Current context (intent, entities, etc.)
            user_id: User ID for personalization
            top_k: Number of skills to return
            
        Returns:
            List of recommended skills
        """
        # Get all skills
        all_skills = await self.list_skills()
        
        # Score skills based on context match
        scored_skills = []
        for skill in all_skills:
            score = self._score_skill_match(skill, context)
            scored_skills.append((score, skill))
        
        # Sort by score and return top_k
        scored_skills.sort(reverse=True, key=lambda x: x[0])
        return [skill for _, skill in scored_skills[:top_k]]
    
    def _score_skill_match(self, skill: Skill, context: Dict[str, Any]) -> float:
        """
        Score how well a skill matches the current context.
        
        Simple implementation - can be enhanced with ML later.
        """
        score = 0.0
        
        # Check if skill type matches intent
        if context.get('intent') == skill.skill_type:
            score += 1.0
        
        # Check if entities match trigger context
        context_entities = set(context.get('entities', []))
        trigger_entities = set(skill.trigger_context.get('entities', []))
        
        if context_entities & trigger_entities:
            score += 0.5
        
        return score
