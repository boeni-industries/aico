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
        "enabled": True,
        "schedule": "0 3 * * *",  # Daily at 3 AM
        "batch_size": 100,
        "similarity_threshold": 0.20  # Lower threshold for label-only comparison
    }
    
    # Zero-shot classification: Direct label embeddings (language-agnostic)
    # The multilingual embedding model naturally understands these concepts
    # across 50+ languages without needing explicit translations
    CATEGORY_LABELS = {
        "too_verbose": "the response is too long and contains too much detail",
        "too_brief": "the response is too short and lacks sufficient detail",
        "wrong_tone": "the response has an inappropriate communication style or tone",
        "not_helpful": "the response does not answer the question or help with the request",
        "incorrect_info": "the response contains factually incorrect or inaccurate information"
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute feedback classification task.
        
        Returns:
            TaskResult with classification statistics
        """
        start_time = datetime.utcnow()
        
        try:
            print("\n" + "="*60)
            print("🧠 [AMS_FEEDBACK] Starting feedback classification task")
            print("="*60)
            logger.info("🧠 [AMS_FEEDBACK] Starting feedback classification task")
            
            # Check if behavioral learning is enabled
            behavioral_config = context.config_manager.get("core.memory.behavioral", {})
            enabled = behavioral_config.get("enabled", False)
            
            print(f"🧠 [AMS_FEEDBACK] Behavioral learning enabled: {enabled}")
            
            if not enabled:
                print("⚠️  [AMS_FEEDBACK] Behavioral learning disabled - skipping task")
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
                   WHERE processed = FALSE 
                   AND free_text IS NOT NULL 
                   AND free_text != ''
                   AND (reason IS NULL OR reason = '')
                   LIMIT ?""",
                (batch_size,)
            ).fetchall()
            
            if not unprocessed_feedback:
                print("ℹ️  [AMS_FEEDBACK] No unprocessed feedback to classify")
                logger.info("🧠 [AMS_FEEDBACK] No unprocessed feedback to classify")
                return TaskResult(
                    success=True,
                    message="No feedback to process",
                    data={"processed": 0}
                )
            
            print(f"📊 [AMS_FEEDBACK] Found {len(unprocessed_feedback)} feedback events to process")
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
            similarity_threshold = context.get_config("similarity_threshold", 0.4)  # Lowered from 0.6 for better matching
            
            print(f"   Using similarity threshold: {similarity_threshold}")
            
            for idx, (event_id, user_id, free_text) in enumerate(unprocessed_feedback, 1):
                try:
                    print(f"  [{idx}/{len(unprocessed_feedback)}] Classifying: {event_id[:8]}... - '{free_text[:50]}...'")
                    
                    # Classify feedback using embedding similarity
                    categories = await self._classify_feedback(
                        free_text, 
                        modelservice,
                        similarity_threshold
                    )
                    
                    # Debug: show all category scores
                    print(f"    Category scores: {categories}")
                    
                    # Get the top category (highest similarity)
                    if categories:
                        top_category = max(categories.items(), key=lambda x: x[1])[0]
                        
                        # Update feedback event with top category as reason
                        context.db_connection.execute(
                            """UPDATE feedback_events 
                               SET reason = ?, processed = TRUE
                               WHERE event_id = ?""",
                            (top_category, event_id)
                        )
                        
                        classified_count += 1
                        print(f"    ✅ Classified as: {top_category} (confidence: {categories[top_category]:.2f})")
                        
                        logger.debug(f"🧠 [AMS_FEEDBACK] Classified feedback {event_id}: {top_category} from {categories}")
                    else:
                        print(f"    ⚠️  No category matched (threshold: {similarity_threshold})")
                        print(f"    Try lowering the threshold in config or check category templates")
                        logger.warning(f"🧠 [AMS_FEEDBACK] No category matched for {event_id}")
                    
                except Exception as e:
                    print(f"    ❌ Error: {type(e).__name__}: {e}")
                    import traceback
                    print(f"    Traceback: {traceback.format_exc()}")
                    logger.error(f"🧠 [AMS_FEEDBACK] Failed to classify {event_id}: {e}", extra={"traceback": traceback.format_exc()})
            
            context.db_connection.commit()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            print(f"\n✅ [AMS_FEEDBACK] Classified {classified_count}/{len(unprocessed_feedback)} events in {duration:.2f}s")
            print("="*60 + "\n")
            logger.info(f"🧠 [AMS_FEEDBACK] ✅ Classified {classified_count} feedback events in {duration:.2f}s")
            
            return TaskResult(
                success=True,
                message=f"Classified {classified_count} feedback events",
                duration_seconds=duration,
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
        
        # Get embedding model from config
        embedding_model = "paraphrase-multilingual"  # Default embedding model
        
        print(f"      Getting embedding for: '{feedback_text[:50]}...'")
        
        # Get embedding for feedback text
        feedback_result = await modelservice.get_embeddings(embedding_model, feedback_text)
        
        # Extract embedding from nested response structure
        # Response format: {'success': True, 'data': {'embedding': [...]}}
        if feedback_result.get('success') and feedback_result.get('data'):
            feedback_embedding = feedback_result['data'].get('embedding', [])
        else:
            feedback_embedding = []
        
        print(f"      Feedback embedding length: {len(feedback_embedding)}")
        print(f"      Feedback embedding type: {type(feedback_embedding)}")
        
        # Calculate similarity to each category label
        categories = {}
        all_scores = {}  # Track all scores for debugging
        
        for category, label_text in self.CATEGORY_LABELS.items():
            print(f"      Processing category: {category}")
            
            # Get embedding for category label
            result = await modelservice.get_embeddings(embedding_model, label_text)
            # Extract from nested structure: {'success': True, 'data': {'embedding': [...]}}
            if result.get('success') and result.get('data'):
                label_embedding = result['data'].get('embedding', [])
            else:
                label_embedding = []
            
            # Calculate similarity to label
            similarity = self._cosine_similarity(feedback_embedding, label_embedding)
            print(f"        Label similarity: {similarity:.3f}")
            
            all_scores[category] = round(similarity, 3)
            
            # Only include if above threshold
            if similarity >= threshold:
                categories[category] = round(similarity, 3)
        
        print(f"      All scores (before threshold): {all_scores}")
        print(f"      Matched categories (>= {threshold}): {categories}")
        
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
