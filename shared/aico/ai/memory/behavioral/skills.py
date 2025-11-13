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

logger = get_logger("shared", "memory.behavioral.skills")


class SkillStore:
    """
    Manages skill library with CRUD operations.
    
    Skills are stored in libSQL database. No vector search needed for small skill sets.
    """
    
    def __init__(self, db_connection):
        """
        Initialize skill store.
        
        Args:
            db_connection: Encrypted libSQL database connection
        """
        self.db = db_connection
    
    async def create_skill(self, skill: Skill) -> Skill:
        """
        Create new skill in database.
        
        Args:
            skill: Skill object to create
            
        Returns:
            Created skill with timestamps
        """
        self.db.execute(
            """INSERT INTO skills (
                skill_id, skill_name, skill_type, trigger_context,
                procedure_template, dimension_vector, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                skill.skill_id,
                skill.skill_name,
                skill.skill_type,
                json.dumps(skill.trigger_context),
                skill.procedure_template,
                json.dumps(skill.dimension_vector),
                skill.created_at.isoformat(),
                skill.updated_at.isoformat()
            )
        )
        self.db.commit()
        
        logger.info(f"Created skill: {skill.skill_id}", extra={
            "skill_id": skill.skill_id,
            "skill_type": skill.skill_type
        })
        
        return skill
    
    async def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID."""
        row = self.db.execute(
            "SELECT * FROM skills WHERE skill_id = ?",
            (skill_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return Skill(
            skill_id=row[0],
            skill_name=row[1],
            skill_type=row[2],
            trigger_context=json.loads(row[3]),
            procedure_template=row[4],
            dimension_vector=json.loads(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7])
        )
    
    async def list_skills(
        self,
        skill_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Skill]:
        """
        List skills with optional filtering.
        
        Args:
            skill_type: Filter by 'base' or 'user_created'
            limit: Maximum number of skills to return
            
        Returns:
            List of skills
        """
        if skill_type:
            rows = self.db.execute(
                "SELECT * FROM skills WHERE skill_type = ? LIMIT ?",
                (skill_type, limit)
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM skills LIMIT ?",
                (limit,)
            ).fetchall()
        
        return [
            Skill(
                skill_id=row[0],
                skill_name=row[1],
                skill_type=row[2],
                trigger_context=json.loads(row[3]),
                procedure_template=row[4],
                dimension_vector=json.loads(row[5]),
                created_at=datetime.fromisoformat(row[6]),
                updated_at=datetime.fromisoformat(row[7])
            )
            for row in rows
        ]
    
    async def get_user_confidence(
        self,
        user_id: str,
        skill_id: str
    ) -> Optional[UserSkillConfidence]:
        """Get user's confidence score for a skill."""
        row = self.db.execute(
            "SELECT * FROM user_skill_confidence WHERE user_id = ? AND skill_id = ?",
            (user_id, skill_id)
        ).fetchone()
        
        if not row:
            return None
        
        return UserSkillConfidence(
            user_id=row[0],
            skill_id=row[1],
            confidence_score=row[2],
            usage_count=row[3],
            positive_count=row[4],
            negative_count=row[5],
            last_used_at=datetime.fromisoformat(row[6]) if row[6] else None
        )
    
    async def update_confidence(
        self,
        user_id: str,
        skill_id: str,
        reward: int,
        learning_rate: float = 0.1
    ) -> float:
        """
        Update skill confidence based on feedback using adaptive EMA.
        
        Args:
            user_id: User ID
            skill_id: Skill ID
            reward: Feedback reward (-1, 0, 1)
            learning_rate: Base learning rate
            
        Returns:
            New confidence score
        """
        # Get current confidence or create new entry
        confidence = await self.get_user_confidence(user_id, skill_id)
        
        if not confidence:
            # Initialize with default confidence
            self.db.execute(
                """INSERT INTO user_skill_confidence (
                    user_id, skill_id, confidence_score, usage_count,
                    positive_count, negative_count, last_used_at
                ) VALUES (?, ?, 0.5, 0, 0, 0, ?)""",
                (user_id, skill_id, datetime.utcnow().isoformat())
            )
            self.db.commit()
            confidence = await self.get_user_confidence(user_id, skill_id)
        
        # Adaptive learning rate: faster for new skills, slower for established
        feedback_count = confidence.positive_count + confidence.negative_count
        alpha = learning_rate * (1.0 + 5.0 / (1.0 + feedback_count))
        
        # Calculate target based on reward
        if reward > 0:
            target = 1.0
        elif reward < 0:
            target = 0.0
        else:
            return confidence.confidence_score  # No update for neutral
        
        # EMA update
        new_confidence = alpha * target + (1 - alpha) * confidence.confidence_score
        new_confidence = max(0.2, min(0.9, new_confidence))  # Clamp to [0.2, 0.9]
        
        # Update database
        self.db.execute(
            """UPDATE user_skill_confidence
               SET confidence_score = ?,
                   usage_count = usage_count + 1,
                   positive_count = positive_count + ?,
                   negative_count = negative_count + ?,
                   last_used_at = ?
               WHERE user_id = ? AND skill_id = ?""",
            (
                new_confidence,
                1 if reward > 0 else 0,
                1 if reward < 0 else 0,
                datetime.utcnow().isoformat(),
                user_id,
                skill_id
            )
        )
        self.db.commit()
        
        logger.info(f"Updated confidence: {confidence.confidence_score:.3f} → {new_confidence:.3f}", extra={
            "user_id": user_id,
            "skill_id": skill_id,
            "reward": reward,
            "alpha": alpha
        })
        
        return new_confidence
    
    async def initialize_base_skills(self) -> None:
        """Initialize foundational base skills if not present."""
        base_skills = [
            Skill(
                skill_id="concise_response",
                skill_name="Concise Response",
                skill_type="base",
                trigger_context={"intent": ["question", "request"], "time_of_day": "any"},
                procedure_template="Provide brief, bullet-point answers. Be concise and direct.",
                dimension_vector=[0.2, 0.5, 0.5, 0.5, 0.3, 0.8, 0.3, 0.3, 0.5, 0.5, 0.7, 0.5, 0.6, 0.4, 0.5, 0.5]
            ),
            Skill(
                skill_id="detailed_explanation",
                skill_name="Detailed Explanation",
                skill_type="base",
                trigger_context={"intent": ["learning", "understanding"], "time_of_day": "any"},
                procedure_template="Provide in-depth explanations with examples. Be thorough and educational.",
                dimension_vector=[0.8, 0.5, 0.7, 0.5, 0.5, 0.6, 0.8, 0.8, 0.5, 0.6, 0.6, 0.6, 0.8, 0.6, 0.5, 0.5]
            ),
            Skill(
                skill_id="casual_chat",
                skill_name="Casual Chat",
                skill_type="base",
                trigger_context={"intent": ["chat", "social"], "time_of_day": "any"},
                procedure_template="Use informal, conversational tone. Be friendly and relaxed.",
                dimension_vector=[0.6, 0.2, 0.3, 0.6, 0.7, 0.3, 0.5, 0.5, 0.6, 0.6, 0.5, 0.7, 0.6, 0.7, 0.5, 0.5]
            ),
            Skill(
                skill_id="technical_precision",
                skill_name="Technical Precision",
                skill_type="base",
                trigger_context={"intent": ["technical", "code"], "time_of_day": "any"},
                procedure_template="Use formal, precise language for technical topics. Be accurate and detailed.",
                dimension_vector=[0.5, 0.8, 0.9, 0.4, 0.2, 0.7, 0.7, 0.6, 0.4, 0.5, 0.8, 0.4, 0.7, 0.5, 0.5, 0.5]
            )
        ]
        
        for skill in base_skills:
            existing = await self.get_skill(skill.skill_id)
            if not existing:
                await self.create_skill(skill)
                logger.info(f"Initialized base skill: {skill.skill_id}")
