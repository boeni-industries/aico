"""
AMS Feedback Classification Task

Scheduled task for processing user feedback events with multilingual classification.
Runs daily at 3 AM to classify free-text feedback into categories.

Schedule: Daily at 3 AM (configurable via cron)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

from aico.core.logging import get_logger
from .base import BaseTask, TaskContext, TaskResult

logger = get_logger("backend", "scheduler.tasks.ams_feedback_classification")


class FeedbackClassificationTask(BaseTask):
    """
    Scheduled task for AMS feedback classification.
    
    Processes unclassified feedback events using embedding-based similarity
    to categorize free-text feedback into predefined categories.
    
    Configuration:
    - Schedule: core.memory.behavioral.contextual_bandit.update_interval_hours
    - Min feedback: core.memory.behavioral.contextual_bandit.min_trajectories
    """
    
    task_id = "ams.feedback_classification"
    default_config = {
        "enabled": False,  # Disabled until Phase 3 fully integrated
        "schedule": "0 3 * * *",  # Daily at 3 AM
        "batch_size": 100,
        "similarity_threshold": 0.6
    }
    
    # Feedback category templates for embedding comparison
    CATEGORY_TEMPLATES = {
        "too_verbose": [
            "too long", "too verbose", "too detailed", "too wordy", 
            "make it shorter", "be more concise", "brevity"
        ],
        "too_brief": [
            "too short", "too brief", "not enough detail", 
            "more explanation", "elaborate", "expand"
        ],
        "wrong_tone": [
            "too formal", "too casual", "wrong tone", 
            "be more friendly", "be more professional"
        ],
        "not_helpful": [
            "not helpful", "doesn't answer", "irrelevant", 
            "didn't help", "not what I asked"
        ],
        "incorrect_info": [
            "incorrect", "wrong", "inaccurate", "false", 
            "mistake", "error", "not true"
        ]
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute feedback classification task.
        
        Returns:
            TaskResult with classification statistics
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info("🧠 [AMS_FEEDBACK] Starting feedback classification task")
            
            # Check if behavioral learning is enabled
            behavioral_config = context.config_manager.get("core.memory.behavioral", {})
            enabled = behavioral_config.get("enabled", False)
            
            if not enabled:
                logger.info("🧠 [AMS_FEEDBACK] Behavioral learning disabled in configuration")
                return TaskResult(
                    success=False,
                    skipped=True,
                    message="Behavioral learning disabled",
                    data={"enabled": False}
                )
            
            # Get unprocessed feedback events
            batch_size = context.get_config("batch_size", 100)
            
            unprocessed_feedback = context.db_connection.execute(
                """SELECT event_id, user_id, free_text 
                   FROM feedback_events 
                   WHERE processed = FALSE AND free_text IS NOT NULL
                   LIMIT ?""",
                (batch_size,)
            ).fetchall()
            
            if not unprocessed_feedback:
                logger.info("🧠 [AMS_FEEDBACK] No unprocessed feedback to classify")
                return TaskResult(
                    success=True,
                    message="No feedback to process",
                    data={"processed": 0}
                )
            
            logger.info(f"🧠 [AMS_FEEDBACK] Processing {len(unprocessed_feedback)} feedback events")
            
            # Get modelservice for embeddings
            try:
                from backend.services import get_modelservice_client
                modelservice = get_modelservice_client(context.config_manager)
            except Exception as e:
                logger.error(f"🧠 [AMS_FEEDBACK] Failed to get modelservice: {e}")
                return TaskResult(
                    success=False,
                    message="Modelservice not available",
                    error=str(e)
                )
            
            # Process each feedback event
            classified_count = 0
            similarity_threshold = context.get_config("similarity_threshold", 0.6)
            
            for event_id, user_id, free_text in unprocessed_feedback:
                try:
                    # Classify feedback using embedding similarity
                    categories = await self._classify_feedback(
                        free_text, 
                        modelservice,
                        similarity_threshold
                    )
                    
                    # Update feedback event with classifications
                    import json
                    context.db_connection.execute(
                        """UPDATE feedback_events 
                           SET classified_categories = ?, processed = TRUE
                           WHERE event_id = ?""",
                        (json.dumps(categories), event_id)
                    )
                    
                    classified_count += 1
                    
                    logger.debug(f"🧠 [AMS_FEEDBACK] Classified feedback {event_id}: {categories}")
                    
                except Exception as e:
                    logger.error(f"🧠 [AMS_FEEDBACK] Failed to classify {event_id}: {e}")
            
            context.db_connection.commit()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"🧠 [AMS_FEEDBACK] Classification complete: {classified_count}/{len(unprocessed_feedback)} events")
            
            return TaskResult(
                success=True,
                message=f"Classified {classified_count} feedback events",
                duration_seconds=execution_time,
                data={
                    "total_feedback": len(unprocessed_feedback),
                    "classified": classified_count,
                    "failed": len(unprocessed_feedback) - classified_count
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"🧠 [AMS_FEEDBACK] Task execution failed: {e}")
            
            return TaskResult(
                success=False,
                message=f"Task execution failed: {str(e)}",
                error=str(e),
                duration_seconds=execution_time
            )
    
    async def _classify_feedback(
        self,
        feedback_text: str,
        modelservice,
        threshold: float
    ) -> Dict[str, float]:
        """
        Classify feedback text using embedding similarity.
        
        Args:
            feedback_text: User's free text feedback
            modelservice: Modelservice client for embeddings
            threshold: Minimum similarity threshold
            
        Returns:
            Dict of category -> similarity score
        """
        import numpy as np
        
        # Get embedding for feedback text
        feedback_embedding = await modelservice.get_embedding(feedback_text)
        
        # Calculate similarity to each category
        categories = {}
        
        for category, templates in self.CATEGORY_TEMPLATES.items():
            # Get embeddings for category templates
            template_embeddings = []
            for template in templates:
                emb = await modelservice.get_embedding(template)
                template_embeddings.append(emb)
            
            # Calculate max similarity to any template
            max_similarity = 0.0
            for template_emb in template_embeddings:
                similarity = self._cosine_similarity(feedback_embedding, template_emb)
                max_similarity = max(max_similarity, similarity)
            
            # Only include if above threshold
            if max_similarity >= threshold:
                categories[category] = round(max_similarity, 3)
        
        return categories
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np
        
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
