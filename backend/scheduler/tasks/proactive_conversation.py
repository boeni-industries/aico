"""
Proactive Conversation Initiation Task

Periodically checks if AICO should initiate conversations with users based on
learned patterns and contextual features using state-of-the-art learning algorithms.
"""

from datetime import datetime
from typing import Any, Dict, List
import uuid

from .base import BaseTask, TaskContext, TaskResult, TaskPriority, TaskQueue
from aico.core.logging import get_logger

logger = get_logger("backend", "scheduler.tasks.proactive_conversation")


class ProactiveConversationTask(BaseTask):
    """Scheduled task to check for proactive conversation opportunities.
    
    Uses state-of-the-art learning system:
    - Contextual Multi-Armed Bandit with Thompson Sampling
    - Human-centered PCA dimensions (Adaptivity, Civility)
    - 11-dimensional contextual feature extraction
    - Real-time decision making
    
    Multi-layer duplicate prevention:
    1. Batch pre-filter: Skip users with pending initiations (single DB query)
    2. Question content matching: Detect semantic duplicates via text similarity
    3. In-memory cache: Ultra-fast lookup for recent initiations across runs
    
    Runs periodically to:
    1. Extract contextual features for each active user
    2. Use learning system to decide if now is a good time
    3. Select optimal strategy (time/topic/urgency)
    4. Initiate conversation if conditions are met
    """
    
    task_id = "agency.proactive_conversation"
    priority = TaskPriority.NORMAL
    queue = TaskQueue.BACKGROUND_LIGHT
    
    # LAYER 3: In-memory cache for recent initiations (class-level, shared across runs)
    # Format: {user_id: [(strategy_id, question_prefix, timestamp), ...]}
    _recent_initiations_cache: Dict[str, List[tuple]] = {}
    
    default_config = {
        "enabled": True,
        "schedule": "*/30 * * * *",  # Every 30 minutes
        "description": "Check for proactive conversation opportunities using learned patterns",
        "requires_idle": False,  # Can run anytime
        "max_duration_seconds": 120,
        "min_time_between_checks_hours": 0.5,  # Don't spam
    }
    
    resource_profile = {
        "cpu": "low",
        "memory": "low",
        "battery": "low",
        "duration_hint": "short",
        "io_intensity": "low"
    }
    
    runtime_context = {
        "foreground": False,
        "network_required": False,
        "power_required": False
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute proactive conversation check.
        
        Args:
            context: Task execution context with services
            
        Returns:
            TaskResult with initiation statistics
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info("🗣️ [PROACTIVE] Starting proactive conversation check")
            
            # Import here to avoid circular dependencies
            from aico.ai.agency.skills.communication.learning import (
                ContextualBanditLearner,
                AdaptivityScorer,
                CivilityScorer,
                extract_contextual_features
            )
            
            # Get database connection
            db = context.db_connection
            
            # Initialize learning components
            bandit = ContextualBanditLearner(db)
            adaptivity_scorer = AdaptivityScorer()
            civility_scorer = CivilityScorer()
            
            # Get all active users
            cursor = db.execute("SELECT uuid FROM user_profiles WHERE is_active = 1")
            all_user_ids = [row[0] for row in cursor.fetchall()]
            
            if not all_user_ids:
                logger.info("🗣️ [PROACTIVE] No active users found")
                return TaskResult(
                    success=True,
                    message="No active users",
                    skipped=True,
                )
            
            # LAYER 1: Batch pre-filter users with recent pending initiations
            # This prevents expensive feature extraction for users we'll skip anyway
            placeholders = ','.join('?' * len(all_user_ids))
            users_with_pending = db.execute(
                f"""SELECT DISTINCT user_id
                   FROM conversation_initiations
                   WHERE user_id IN ({placeholders})
                   AND resolution_status = 'pending'
                   AND datetime(initiated_at) > datetime('now', '-24 hours')""",
                all_user_ids
            ).fetchall()
            
            users_to_skip = {row[0] for row in users_with_pending}
            user_ids = [uid for uid in all_user_ids if uid not in users_to_skip]
            
            logger.info(
                f"🗣️ [PROACTIVE] Pre-filtered {len(all_user_ids)} users: "
                f"{len(user_ids)} eligible, {len(users_to_skip)} skipped (recent pending)"
            )
            
            initiations_created = 0
            users_checked = 0
            decisions = []
            
            for user_id in user_ids:
                try:
                    users_checked += 1
                    
                    # Extract contextual features (only for eligible users)
                    context_features = extract_contextual_features(db, user_id)
                    
                    # Score on Adaptivity dimension
                    patience_score = adaptivity_scorer.calculate_patience_score(
                        context_features, 
                        context_features.time_since_last_interaction
                    )
                    timing_score = adaptivity_scorer.calculate_timing_sensitivity(context_features)
                    adaptivity = (patience_score + timing_score) / 2
                    
                    # Score on Civility dimension
                    # Load user preferences
                    try:
                        from aico.ai.agency.skills.communication.user_preferences import load_user_preferences
                        user_prefs = load_user_preferences(db, user_id)
                    except Exception as pref_error:
                        logger.warning(f"🗣️ [PROACTIVE] Failed to load preferences: {pref_error}")
                        user_prefs = {}
                    
                    boundary_score = civility_scorer.calculate_boundary_respect(
                        context_features, 
                        user_prefs
                    )
                    emotional_score = civility_scorer.calculate_emotional_intelligence(
                        context_features, 
                        "curiosity"  # Default topic
                    )
                    civility = (boundary_score + emotional_score) / 2
                    
                    # Combined score
                    overall_score = adaptivity * 0.6 + civility * 0.4
                    
                    # Use bandit to select strategy
                    strategy_id, expected_reward = bandit.select_strategy(context_features)
                    
                    # Decision thresholds
                    threshold = 0.5
                    reward_threshold = 0.3
                    should_initiate = overall_score > threshold and expected_reward > reward_threshold
                    
                    logger.info(
                        f"🗣️ [PROACTIVE] User {user_id[:8]}: "
                        f"adaptivity={adaptivity:.2f}, civility={civility:.2f}, "
                        f"overall={overall_score:.2f}, reward={expected_reward:.2f}, "
                        f"decision={'INITIATE' if should_initiate else 'SKIP'}"
                    )
                    
                    decisions.append({
                        'user_id': user_id[:8],
                        'decision': 'initiate' if should_initiate else 'skip',
                        'adaptivity': round(adaptivity, 2),
                        'civility': round(civility, 2),
                        'overall_score': round(overall_score, 2),
                        'expected_reward': round(expected_reward, 2),
                        'strategy': strategy_id
                    })
                    
                    if should_initiate:
                        # Determine topic and message based on strategy
                        topic, message = self._generate_message_for_strategy(strategy_id, context_features)
                        
                        # LAYER 3: Check in-memory cache first (fastest)
                        question_prefix = message[:50]
                        now = datetime.utcnow()
                        cache_hit = False
                        
                        if user_id in self._recent_initiations_cache:
                            # Clean expired entries (>24h old)
                            self._recent_initiations_cache[user_id] = [
                                (s, q, t) for s, q, t in self._recent_initiations_cache[user_id]
                                if (now - t).total_seconds() < 86400  # 24 hours
                            ]
                            
                            # Check for duplicates
                            for cached_strategy, cached_question, _ in self._recent_initiations_cache[user_id]:
                                if cached_strategy == strategy_id or cached_question == question_prefix:
                                    cache_hit = True
                                    logger.debug(
                                        f"🗣️ [PROACTIVE] ⚡ Cache hit: User {user_id[:8]} has recent similar initiation, skipping"
                                    )
                                    decisions.append({
                                        'user_id': user_id[:8],
                                        'decision': 'skip',
                                        'reason': 'duplicate_cache_hit'
                                    })
                                    break
                        
                        if cache_hit:
                            continue
                        
                        # LAYER 2: Check database for duplicate strategy AND question content
                        # Only if cache miss (most runs will hit cache, saving DB queries)
                        duplicate = db.execute(
                            """SELECT COUNT(*) as count
                               FROM conversation_initiations
                               WHERE user_id = ?
                               AND (
                                   trigger_reason = ?
                                   OR question LIKE ?
                               )
                               AND datetime(initiated_at) > datetime('now', '-24 hours')""",
                            (user_id, f"proactive_check_strategy_{strategy_id}", f"%{question_prefix}%")
                        ).fetchone()
                        
                        if duplicate and duplicate['count'] > 0:
                            logger.debug(
                                f"🗣️ [PROACTIVE] User {user_id[:8]} already has similar initiation "
                                f"(strategy {strategy_id} or matching question), skipping"
                            )
                            decisions.append({
                                'user_id': user_id[:8],
                                'decision': 'skip',
                                'reason': 'duplicate_strategy_or_question'
                            })
                            continue
                        
                        # Create initiation record
                        initiation_id = str(uuid.uuid4())
                        conversation_id = f"{user_id}_{int(datetime.utcnow().timestamp())}"
                        
                        db.execute(
                            """INSERT INTO conversation_initiations (
                                initiation_id, user_id, conversation_id,
                                trigger_source, trigger_reason, question,
                                context, urgency, expected_answer_type,
                                initiated_at, resolution_status, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                initiation_id,
                                user_id,
                                conversation_id,
                                "scheduler",
                                f"proactive_check_strategy_{strategy_id}",
                                message,
                                f"Adaptivity: {adaptivity:.2f}, Civility: {civility:.2f}, Strategy: {strategy_id}",
                                "medium",
                                "text",
                                datetime.utcnow().isoformat(),
                                "pending",
                                datetime.utcnow().isoformat()
                            )
                        )
                        db.commit()
                        
                        # Update in-memory cache
                        if user_id not in self._recent_initiations_cache:
                            self._recent_initiations_cache[user_id] = []
                        self._recent_initiations_cache[user_id].append(
                            (strategy_id, question_prefix, now)
                        )
                        
                        initiations_created += 1
                        
                        print(f"🗣️ [PROACTIVE] ✅ Created initiation {initiation_id[:8]} for user {user_id[:8]}")
                        logger.info(
                            f"🗣️ [PROACTIVE] Created initiation {initiation_id[:8]} "
                            f"for user {user_id[:8]} with strategy {strategy_id}"
                        )
                        
                        # Broadcast to WebSocket clients for real-time notification
                        try:
                            await self._broadcast_new_initiation(
                                user_id=user_id,
                                initiation_id=initiation_id,
                                question=message,
                                initiated_at=datetime.utcnow().isoformat(),
                                trigger_reason=f"proactive_check_strategy_{strategy_id}"
                            )
                        except Exception as ws_error:
                            logger.warning(f"🗣️ [PROACTIVE] Failed to broadcast WebSocket notification: {ws_error}")
                        
                        # Publish to message bus for ConversationEngine
                        try:
                            from aico.core.bus import MessageBusClient
                            
                            bus_client = MessageBusClient(client_id=f"proactive_scheduler_{initiation_id[:8]}")
                            
                            # Create initiation message
                            initiation_message = {
                                'initiation_id': initiation_id,
                                'user_id': user_id,
                                'conversation_id': conversation_id,
                                'topic': topic,
                                'message': message,
                                'context': f"Adaptivity: {adaptivity:.2f}, Civility: {civility:.2f}, Strategy: {strategy_id}",
                                'urgency': 'medium',
                                'expected_answer_type': 'text',
                                'initiated_at': datetime.utcnow().isoformat(),
                                'strategy_id': strategy_id,
                                'scores': {
                                    'adaptivity': adaptivity,
                                    'civility': civility,
                                    'overall': overall_score,
                                    'expected_reward': expected_reward
                                }
                            }
                            
                            # Publish to conversation initiation topic
                            bus_client.publish(
                                topic='conversation/aico/initiate/v1',
                                message=initiation_message
                            )
                            
                            print(f"🗣️ [PROACTIVE] 📤 Published initiation to message bus")
                            logger.info(
                                f"🗣️ [PROACTIVE] Published initiation {initiation_id[:8]} "
                                f"to message bus topic 'conversation/aico/initiate/v1'"
                            )
                            
                        except Exception as bus_error:
                            # Don't fail the task if message bus publish fails
                            print(f"🗣️ [PROACTIVE] ⚠️ Failed to publish to message bus: {bus_error}")
                            logger.warning(
                                f"🗣️ [PROACTIVE] Failed to publish initiation to message bus: {bus_error}"
                            )
                    
                except Exception as e:
                    logger.error(f"🗣️ [PROACTIVE] Error checking user {user_id[:8]}: {e}")
                    continue
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            message = (
                f"Checked {users_checked} users, created {initiations_created} initiations"
            )
            
            logger.info(f"🗣️ [PROACTIVE] {message} in {duration:.1f}s")
            
            return TaskResult(
                success=True,
                message=message,
                data={
                    "users_checked": users_checked,
                    "initiations_created": initiations_created,
                    "decisions": decisions,
                },
                duration_seconds=duration
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"🗣️ [PROACTIVE] Task failed: {e}", exc_info=True)
            
            return TaskResult(
                success=False,
                message=f"Proactive conversation check failed: {str(e)}",
                error=str(e),
                duration_seconds=duration
            )
    
    def _generate_message_for_strategy(
        self, 
        strategy_id: str, 
        context_features
    ) -> tuple[str, str]:
        """Generate topic and message based on selected strategy.
        
        Args:
            strategy_id: Selected bandit arm strategy
            context_features: User's contextual features
            
        Returns:
            (topic, message) tuple
        """
        # Parse strategy ID (format: "time_morning", "topic_curiosity", etc.)
        parts = strategy_id.split('_', 1)
        if len(parts) != 2:
            return "general", "I've been thinking about our recent conversations. How are things going?"
        
        strategy_type, strategy_value = parts
        
        if strategy_type == "time":
            # Time-based messages
            messages = {
                "morning": ("morning_checkin", "Good morning! How are you feeling today?"),
                "afternoon": ("afternoon_checkin", "How's your day going so far?"),
                "evening": ("evening_reflection", "How was your day? Anything interesting happen?"),
                "night": ("night_reflection", "Hope you had a good day. Anything on your mind?"),
            }
            return messages.get(strategy_value, ("general", "How are you doing?"))
        
        elif strategy_type == "topic":
            # Topic-based messages
            messages = {
                "information_gap": ("clarification", "I've been thinking about something we discussed. Could you tell me more about it?"),
                "concern": ("concern", "I noticed something that made me curious. Is everything okay?"),
                "curiosity": ("curiosity", "I've been wondering about something. Do you have a moment to chat?"),
                "approval": ("approval", "I wanted to check in about something we talked about. What do you think?"),
            }
            return messages.get(strategy_value, ("general", "I wanted to chat. How are things?"))
        
        elif strategy_type == "urgency":
            # Urgency-based messages
            messages = {
                "low": ("casual_chat", "No rush, but I was thinking about you. How are things?"),
                "medium": ("checkin", "I wanted to check in with you. How are you doing?"),
                "high": ("important_checkin", "I have something I'd like to discuss with you. Do you have a moment?"),
            }
            return messages.get(strategy_value, ("general", "How are you?"))
        
        return "general", "I wanted to reach out. How are you doing?"
    
    async def _broadcast_new_initiation(
        self,
        user_id: str,
        initiation_id: str,
        question: str,
        initiated_at: str,
        trigger_reason: str
    ) -> None:
        """Broadcast new proactive initiation via WebSocket to user.
        
        Args:
            user_id: User UUID
            initiation_id: Initiation UUID
            question: Question text
            initiated_at: ISO timestamp
            trigger_reason: Trigger reason
        """
        from aico.core.bus import MessageBusClient
        
        bus_client = MessageBusClient("proactive_scheduler_ws")
        await bus_client.connect()
        
        try:
            # Publish to user-specific WebSocket topic
            await bus_client.publish(
                f"proactive.notifications.{user_id}",
                {
                    "type": "new_initiation",
                    "initiation_id": initiation_id,
                    "question": question,
                    "initiated_at": initiated_at,
                    "trigger_reason": trigger_reason,
                    "resolution_status": "pending"
                }
            )
            
            logger.info(
                f"🗣️ [PROACTIVE] 📡 Broadcasted WebSocket notification for initiation {initiation_id[:8]}"
            )
        finally:
            await bus_client.disconnect()
