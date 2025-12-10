from __future__ import annotations

import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from collections import defaultdict

from aico.core.logging import get_logger

from .models import Goal, Plan, PlanStatus, PlanStep, StepStatus
from .templates import PLAN_SHAPES, PlanShape


logger = get_logger("shared", "ai.agency.planner")


class PlanStrategy(str, Enum):
    """Strategy used to generate a plan."""
    LLM_GENERATED = "llm_generated"
    TEMPLATE_BASED = "template_based"
    SIMPLE_FALLBACK = "simple_fallback"


class PlanQuality(str, Enum):
    """Quality assessment of generated plan."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


class Planner:
    """Production-grade planning system with LLM-backed generation.

    Implements a three-tier fallback strategy:
    1. LLM-generated plans (primary)
    2. Template-based plans (fallback)
    3. Simple two-step plans (last resort)
    
    Features:
    - LLM-based plan generation with validation
    - Plan quality assessment
    - Caching of successful plans
    - Automatic fallback on failures
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 3600,
        db_connection: Optional[Any] = None,
    ) -> None:
        """Initialize planner.
        
        Args:
            llm_client: Optional LLM client for plan generation
            enable_caching: Whether to cache generated plans
            cache_ttl_seconds: TTL for cached plans (default 1 hour)
            db_connection: Optional database connection for skill availability checks
        """
        self.llm_client = llm_client
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self.db = db_connection
        self._plan_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(
            f"[PLANNER] Initialized with LLM: {llm_client is not None}, "
            f"caching: {enable_caching}, DB: {db_connection is not None}"
        )

    async def generate_initial_plan(
        self,
        goal: Goal,
        context: Optional[Dict[str, Any]] = None,
    ) -> Plan:
        """Generate a plan for a goal using best available strategy.
        
        Implements three-tier fallback:
        1. Try LLM-generated plan (if LLM available)
        2. Fall back to template-based plan
        3. Fall back to simple two-step plan
        
        Args:
            goal: Goal to plan for
            context: Optional context (world model, personality, etc.)
            
        Returns:
            Plan with strategy and quality metadata
        """
        context = context or {}
        
        # Check cache first
        if self.enable_caching:
            cached_plan = self._get_cached_plan(goal)
            if cached_plan:
                logger.info(f"[PLANNER] Using cached plan for goal {goal.goal_id}")
                return cached_plan
        
        # Try pattern-based planning first (if user_id available)
        user_id = context.get('user_id')
        if user_id and self.db:
            pattern = self.get_pattern_suggestion(goal, user_id)
            if pattern:
                try:
                    plan = await self.generate_plan_from_pattern(goal, pattern)
                    if plan and self._validate_plan(plan, goal):
                        logger.info(
                            f"[PLANNER] Generated pattern-based plan for goal {goal.goal_id} "
                            f"(confidence: {pattern['confidence']:.2f})"
                        )
                        self._cache_plan(goal, plan)
                        return plan
                except Exception as e:
                    logger.error(f"[PLANNER] Pattern-based planning failed: {e}", exc_info=True)
        
        # Try LLM generation
        if self.llm_client:
            try:
                plan = await self._generate_llm_plan(goal, context)
                if plan and self._validate_plan(plan, goal):
                    logger.info(f"[PLANNER] Generated LLM plan for goal {goal.goal_id}")
                    self._cache_plan(goal, plan)
                    return plan
                else:
                    logger.warning(f"[PLANNER] LLM plan validation failed, falling back")
            except Exception as e:
                logger.error(f"[PLANNER] LLM plan generation failed: {e}", exc_info=True)
        
        # Fall back to template-based
        plan = await self._generate_template_plan(goal)
        if plan:
            logger.info(f"[PLANNER] Generated template plan for goal {goal.goal_id}")
            return plan
        
        # Last resort: simple fallback
        plan = self._generate_simple_fallback(goal)
        logger.info(f"[PLANNER] Generated simple fallback plan for goal {goal.goal_id}")
        return plan
    
    async def _generate_llm_plan(
        self,
        goal: Goal,
        context: Dict[str, Any],
    ) -> Optional[Plan]:
        """Generate plan using LLM.
        
        Args:
            goal: Goal to plan for
            context: Context including world model, personality, etc.
            
        Returns:
            Generated plan or None if generation fails
        """
        try:
            # Build prompt for LLM
            prompt = self._build_planning_prompt(goal, context)
            
            # Call LLM (implementation depends on LLM client interface)
            if hasattr(self.llm_client, 'generate_plan'):
                response = await self.llm_client.generate_plan(prompt)
            elif hasattr(self.llm_client, 'complete'):
                response = await self.llm_client.complete(prompt)
            else:
                logger.warning("[PLANNER] LLM client has no compatible method")
                return None
            
            # Parse LLM response into plan steps
            steps = self._parse_llm_response(response, goal)
            
            if not steps:
                return None
            
            plan = Plan(
                plan_id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                status=PlanStatus.DRAFT,
                steps=steps,
                metadata={
                    "generated_at": datetime.utcnow().isoformat(),
                    "strategy": PlanStrategy.LLM_GENERATED.value,
                    "llm_model": getattr(self.llm_client, 'model_name', 'unknown'),
                },
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"[PLANNER] LLM plan generation error: {e}", exc_info=True)
            return None
    
    async def _generate_template_plan(self, goal: Goal) -> Optional[Plan]:
        """Generate plan using templates (fallback strategy).
        
        Args:
            goal: Goal to plan for
            
        Returns:
            Template-based plan or None if no template matches
        """
        plan_id = str(uuid.uuid4())
        steps: List[PlanStep] = []
        selected_shape: Optional[PlanShape] = None

        # Try to find matching template
        for shape in PLAN_SHAPES.values():
            if goal.goal_type in shape["applicable_goal_types"]:
                selected_shape = shape
                break

        if not selected_shape:
            return None
        
        # Generate steps from template
        for index, abstract_step in enumerate(selected_shape["steps"], start=1):
            steps.append(
                PlanStep(
                    step_id=str(uuid.uuid4()),
                    order=index,
                    description=abstract_step["description"].replace("this goal", goal.title),
                    status=StepStatus.PENDING,
                    metadata={
                        "shape_id": selected_shape["id"],
                        "shape_role": abstract_step["role"],
                        "abstract_step_id": abstract_step["id"],
                    },
                )
            )

        plan = Plan(
            plan_id=plan_id,
            goal_id=goal.goal_id,
            status=PlanStatus.DRAFT,
            steps=steps,
            metadata={
                "generated_at": datetime.utcnow().isoformat(),
                "strategy": PlanStrategy.TEMPLATE_BASED.value,
                "template_id": selected_shape["id"],
            },
        )

        return plan
    
    def _generate_simple_fallback(self, goal: Goal) -> Plan:
        """Generate simple two-step fallback plan (last resort).
        
        Args:
            goal: Goal to plan for
            
        Returns:
            Simple two-step plan
        """
        steps = [
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=1,
                description=f"Clarify details and constraints for goal: {goal.title}",
                status=StepStatus.PENDING,
                metadata={"phase": "intake"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=2,
                description=f"Take first concrete action towards: {goal.title}",
                status=StepStatus.PENDING,
                metadata={"phase": "action"},
            ),
        ]

        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            status=PlanStatus.DRAFT,
            steps=steps,
            metadata={
                "generated_at": datetime.utcnow().isoformat(),
                "strategy": PlanStrategy.SIMPLE_FALLBACK.value,
            },
        )

        return plan
    
    def _build_planning_prompt(
        self,
        goal: Goal,
        context: Dict[str, Any],
    ) -> str:
        """Build prompt for LLM plan generation.
        
        Args:
            goal: Goal to plan for
            context: Context information
            
        Returns:
            Formatted prompt string
        """
        # Extract context elements
        world_context = context.get('world_model', {})
        
        prompt = f"""Generate a detailed action plan for the following goal:

Goal: {goal.title}
Description: {goal.description or 'No additional description'}
Type: {goal.goal_type}
Priority: {goal.priority.value}

Context:
{json.dumps(world_context, indent=2) if world_context else 'No world model context'}

Please generate a plan with 3-7 concrete, actionable steps. For each step:
1. Provide a clear description of what needs to be done
2. Identify any preconditions or dependencies
3. Suggest which skills or tools might be needed

Format your response as a JSON array of steps:
[
  {{
    "description": "Step description",
    "preconditions": ["condition1", "condition2"],
    "suggested_skills": ["skill1", "skill2"]
  }},
  ...
]
"""
        return prompt
    
    def _parse_llm_response(
        self,
        response: str,
        goal: Goal,
    ) -> List[PlanStep]:
        """Parse LLM response into plan steps.
        
        Args:
            response: LLM response text
            goal: Goal being planned for
            
        Returns:
            List of PlanStep objects
        """
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Find JSON array in response
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("[PLANNER] No JSON array found in LLM response")
                return []
            
            json_str = response[start_idx:end_idx]
            steps_data = json.loads(json_str)
            
            # Convert to PlanStep objects
            steps = []
            for index, step_data in enumerate(steps_data, start=1):
                step = PlanStep(
                    step_id=str(uuid.uuid4()),
                    order=index,
                    description=step_data.get('description', f'Step {index}'),
                    status=StepStatus.PENDING,
                    metadata={
                        'preconditions': step_data.get('preconditions', []),
                        'suggested_skills': step_data.get('suggested_skills', []),
                        'llm_generated': True,
                    },
                )
                steps.append(step)
            
            return steps
            
        except json.JSONDecodeError as e:
            logger.error(f"[PLANNER] Failed to parse LLM response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"[PLANNER] Error parsing LLM response: {e}", exc_info=True)
            return []
    
    def _validate_plan(self, plan: Plan, goal: Goal) -> bool:
        """Validate generated plan meets quality standards.
        
        Args:
            plan: Plan to validate
            goal: Goal the plan is for
            
        Returns:
            True if plan is valid, False otherwise
        """
        # Check basic requirements
        if not plan.steps:
            logger.warning("[PLANNER] Plan has no steps")
            return False
        
        if len(plan.steps) < 2:
            logger.warning("[PLANNER] Plan has too few steps")
            return False
        
        if len(plan.steps) > 15:
            logger.warning("[PLANNER] Plan has too many steps")
            return False
        
        # Check step quality
        for step in plan.steps:
            if not step.description or len(step.description) < 10:
                logger.warning(f"[PLANNER] Step {step.step_id} has poor description")
                return False
        
        # Assess overall quality
        quality = self._assess_plan_quality(plan)
        plan.metadata['quality'] = quality.value
        
        # Accept good or acceptable plans
        return quality in [PlanQuality.EXCELLENT, PlanQuality.GOOD, PlanQuality.ACCEPTABLE]
    
    def _assess_plan_quality(self, plan: Plan) -> PlanQuality:
        """Assess the quality of a generated plan.
        
        Args:
            plan: Plan to assess
            
        Returns:
            Quality rating
        """
        score = 0
        
        # Step count (3-7 is ideal)
        if 3 <= len(plan.steps) <= 7:
            score += 2
        elif 2 <= len(plan.steps) <= 10:
            score += 1
        
        # Step descriptions (longer is generally better)
        avg_length = sum(len(s.description) for s in plan.steps) / len(plan.steps)
        if avg_length > 50:
            score += 2
        elif avg_length > 30:
            score += 1
        
        # Metadata richness
        for step in plan.steps:
            if step.metadata.get('preconditions'):
                score += 1
                break
        
        for step in plan.steps:
            if step.metadata.get('suggested_skills'):
                score += 1
                break
        
        # Map score to quality
        if score >= 5:
            return PlanQuality.EXCELLENT
        elif score >= 3:
            return PlanQuality.GOOD
        elif score >= 2:
            return PlanQuality.ACCEPTABLE
        else:
            return PlanQuality.POOR
    
    def _get_cached_plan(self, goal: Goal) -> Optional[Plan]:
        """Get cached plan for similar goal.
        
        Args:
            goal: Goal to find cached plan for
            
        Returns:
            Cached plan or None
        """
        # Create cache key from goal type and title
        cache_key = f"{goal.goal_type}:{goal.title.lower()[:50]}"
        
        cached = self._plan_cache.get(cache_key)
        if not cached:
            return None
        
        # Check if cache is still valid
        cached_time = datetime.fromisoformat(cached['timestamp'])
        age_seconds = (datetime.utcnow() - cached_time).total_seconds()
        
        if age_seconds > self.cache_ttl_seconds:
            # Cache expired
            del self._plan_cache[cache_key]
            return None
        
        # Clone the cached plan for new goal
        cached_plan: Plan = cached['plan']
        new_plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            status=PlanStatus.DRAFT,
            steps=[
                PlanStep(
                    step_id=str(uuid.uuid4()),
                    order=step.order,
                    description=step.description,
                    status=StepStatus.PENDING,
                    metadata=step.metadata.copy(),
                )
                for step in cached_plan.steps
            ],
            metadata={
                **cached_plan.metadata,
                'cached_from': cache_key,
                'generated_at': datetime.utcnow().isoformat(),
            },
        )
        
        return new_plan
    
    def _cache_plan(self, goal: Goal, plan: Plan) -> None:
        """Cache a successfully generated plan.
        
        Args:
            goal: Goal the plan is for
            plan: Plan to cache
        """
        if not self.enable_caching:
            return
        
        cache_key = f"{goal.goal_type}:{goal.title.lower()[:50]}"
        
        self._plan_cache[cache_key] = {
            'plan': plan,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        # Limit cache size
        if len(self._plan_cache) > 100:
            # Remove oldest entry
            oldest_key = min(
                self._plan_cache.keys(),
                key=lambda k: self._plan_cache[k]['timestamp']
            )
            del self._plan_cache[oldest_key]
    
    def check_skill_availability(self, skill_ids: List[str]) -> Dict[str, bool]:
        """Check if required skills are available.
        
        Args:
            skill_ids: List of skill IDs to check
            
        Returns:
            Dictionary mapping skill_id to availability (True/False)
        """
        if not self.db or not skill_ids:
            # No DB connection or no skills to check - assume all available
            return {skill_id: True for skill_id in skill_ids}
        
        try:
            # Query database for skill availability
            placeholders = ','.join('?' * len(skill_ids))
            query = f"SELECT skill_id, status FROM skills WHERE skill_id IN ({placeholders})"
            
            rows = self.db.execute(query, skill_ids).fetchall()
            
            # Build availability map
            availability = {}
            found_skills = {row['skill_id']: row.get('status', 'active') for row in rows}
            
            for skill_id in skill_ids:
                if skill_id in found_skills:
                    # Skill exists - check if active
                    availability[skill_id] = found_skills[skill_id] == 'active'
                else:
                    # Skill not found - not available
                    availability[skill_id] = False
            
            return availability
            
        except Exception as e:
            logger.warning(f"[PLANNER] Failed to check skill availability: {e}")
            # On error, assume all skills available
            return {skill_id: True for skill_id in skill_ids}
    
    def filter_plan_by_skill_availability(self, plan: Plan) -> Plan:
        """Filter plan steps based on skill availability.
        
        Args:
            plan: Plan to filter
            
        Returns:
            Filtered plan with only steps using available skills
        """
        if not self.db:
            return plan
        
        # Collect all skill IDs from plan steps
        skill_ids = []
        for step in plan.steps:
            suggested_skills = step.metadata.get('suggested_skills', [])
            skill_ids.extend(suggested_skills)
        
        if not skill_ids:
            return plan
        
        # Check availability
        availability = self.check_skill_availability(skill_ids)
        
        # Filter steps
        filtered_steps = []
        for step in plan.steps:
            suggested_skills = step.metadata.get('suggested_skills', [])
            
            if not suggested_skills:
                # No skills required - keep step
                filtered_steps.append(step)
            else:
                # Check if at least one skill is available
                has_available_skill = any(
                    availability.get(skill_id, False) 
                    for skill_id in suggested_skills
                )
                
                if has_available_skill:
                    # Filter to only available skills
                    available_skills = [
                        skill_id for skill_id in suggested_skills
                        if availability.get(skill_id, False)
                    ]
                    step.metadata['suggested_skills'] = available_skills
                    step.metadata['unavailable_skills'] = [
                        skill_id for skill_id in suggested_skills
                        if not availability.get(skill_id, False)
                    ]
                    filtered_steps.append(step)
                else:
                    # No available skills - mark step as blocked
                    step.metadata['blocked'] = True
                    step.metadata['block_reason'] = 'No available skills'
                    filtered_steps.append(step)
        
        # Update plan with filtered steps
        plan.steps = filtered_steps
        plan.metadata['skill_availability_checked'] = True
        
        return plan
    
    def detect_plan_patterns(
        self,
        user_id: str,
        lookback_days: int = 90,
        min_occurrences: int = 3,
    ) -> List[Dict[str, Any]]:
        """Detect patterns from historical successful plans.
        
        Args:
            user_id: User to analyze plans for
            lookback_days: How many days back to analyze
            min_occurrences: Minimum times a pattern must occur
            
        Returns:
            List of detected patterns with metadata
        """
        if not self.db:
            return []
        
        try:
            # Query completed plans from the lookback period
            cutoff_date = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
            
            rows = self.db.execute(
                """SELECT p.plan_id, p.goal_id, p.metadata_json, g.goal_type, g.title
                   FROM agency_plans p
                   JOIN agency_goals g ON p.goal_id = g.goal_id
                   WHERE g.user_id = ? 
                   AND p.status = 'completed'
                   AND p.created_at >= ?
                   ORDER BY p.created_at DESC""",
                (user_id, cutoff_date)
            ).fetchall()
            
            if not rows:
                return []
            
            # Group plans by goal type
            patterns_by_type = defaultdict(list)
            
            for row in rows:
                goal_type = row['goal_type']
                metadata = json.loads(row['metadata_json']) if isinstance(row['metadata_json'], str) else row['metadata_json']
                
                # Extract pattern signature
                pattern = {
                    'goal_type': goal_type,
                    'strategy': metadata.get('strategy'),
                    'step_count': metadata.get('step_count', 0),
                    'quality': metadata.get('quality'),
                    'plan_id': row['plan_id'],
                }
                
                patterns_by_type[goal_type].append(pattern)
            
            # Detect recurring patterns
            detected_patterns = []
            
            for goal_type, plans in patterns_by_type.items():
                if len(plans) < min_occurrences:
                    continue
                
                # Find most common strategy for this goal type
                strategies = [p['strategy'] for p in plans if p['strategy']]
                if strategies:
                    most_common_strategy = max(set(strategies), key=strategies.count)
                    occurrence_count = strategies.count(most_common_strategy)
                    
                    if occurrence_count >= min_occurrences:
                        # Calculate average quality
                        qualities = [p['quality'] for p in plans if p['quality']]
                        avg_quality = None
                        if qualities:
                            quality_scores = {
                                'excellent': 4,
                                'good': 3,
                                'acceptable': 2,
                                'poor': 1
                            }
                            avg_score = sum(quality_scores.get(q, 0) for q in qualities) / len(qualities)
                            avg_quality = 'excellent' if avg_score >= 3.5 else 'good' if avg_score >= 2.5 else 'acceptable'
                        
                        detected_patterns.append({
                            'goal_type': goal_type,
                            'strategy': most_common_strategy,
                            'occurrences': occurrence_count,
                            'total_plans': len(plans),
                            'success_rate': occurrence_count / len(plans),
                            'avg_quality': avg_quality,
                            'confidence': min(1.0, occurrence_count / 10.0),  # Max confidence at 10 occurrences
                        })
            
            logger.info(
                f"[PLANNER] Detected {len(detected_patterns)} patterns from {len(rows)} historical plans"
            )
            
            return detected_patterns
            
        except Exception as e:
            logger.error(f"[PLANNER] Failed to detect patterns: {e}", exc_info=True)
            return []
    
    def get_pattern_suggestion(
        self,
        goal: Goal,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get pattern-based suggestion for a goal.
        
        Args:
            goal: Goal to get suggestion for
            user_id: User ID
            
        Returns:
            Pattern suggestion or None
        """
        patterns = self.detect_plan_patterns(user_id)
        
        # Find pattern matching this goal type
        for pattern in patterns:
            if pattern['goal_type'] == goal.goal_type:
                # Only suggest if confidence is high enough
                if pattern['confidence'] >= 0.5:
                    return pattern
        
        return None
    
    async def generate_plan_from_pattern(
        self,
        goal: Goal,
        pattern: Dict[str, Any],
    ) -> Optional[Plan]:
        """Generate a plan based on a detected pattern.
        
        Args:
            goal: Goal to plan for
            pattern: Pattern to use
            
        Returns:
            Generated plan or None
        """
        if not self.db:
            return None
        
        try:
            # Find a successful plan matching this pattern
            rows = self.db.execute(
                """SELECT p.plan_id, p.steps_json, p.metadata_json
                   FROM agency_plans p
                   JOIN agency_goals g ON p.goal_id = g.goal_id
                   WHERE g.goal_type = ?
                   AND p.status = 'completed'
                   AND json_extract(p.metadata_json, '$.strategy') = ?
                   ORDER BY p.created_at DESC
                   LIMIT 1""",
                (pattern['goal_type'], pattern['strategy'])
            ).fetchall()
            
            if not rows:
                return None
            
            # Parse the successful plan
            row = rows[0]
            steps_data = json.loads(row['steps_json']) if isinstance(row['steps_json'], str) else row['steps_json']
            
            # Adapt steps for new goal
            adapted_steps = []
            for i, step_data in enumerate(steps_data, start=1):
                # Replace goal-specific references
                description = step_data['description']
                # Simple adaptation: replace references to old goal with new goal
                # More sophisticated adaptation could use LLM
                
                adapted_step = PlanStep(
                    step_id=str(uuid.uuid4()),
                    order=i,
                    description=description,
                    status=StepStatus.PENDING,
                    metadata={
                        **step_data.get('metadata', {}),
                        'adapted_from_pattern': True,
                        'pattern_confidence': pattern['confidence'],
                    },
                )
                adapted_steps.append(adapted_step)
            
            plan = Plan(
                plan_id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                status=PlanStatus.DRAFT,
                steps=adapted_steps,
                metadata={
                    'generated_at': datetime.utcnow().isoformat(),
                    'strategy': PlanStrategy.TEMPLATE_BASED.value,  # Pattern-based is a form of template
                    'pattern_based': True,
                    'pattern_confidence': pattern['confidence'],
                    'pattern_occurrences': pattern['occurrences'],
                    'adapted_from_plan': row['plan_id'],
                },
            )
            
            logger.info(
                f"[PLANNER] Generated pattern-based plan for {goal.goal_type} "
                f"(confidence: {pattern['confidence']:.2f})"
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"[PLANNER] Failed to generate plan from pattern: {e}", exc_info=True)
            return None
    
    def record_plan_outcome(
        self,
        plan_id: str,
        success: bool,
        execution_time_seconds: Optional[float] = None,
    ) -> bool:
        """Record the outcome of a plan execution for learning.
        
        Args:
            plan_id: Plan ID
            success: Whether plan succeeded
            execution_time_seconds: How long execution took
            
        Returns:
            True if recorded successfully
        """
        if not self.db:
            return False
        
        try:
            # Update plan metadata with outcome
            self.db.execute(
                """UPDATE agency_plans
                   SET metadata_json = json_set(
                       metadata_json,
                       '$.outcome', ?,
                       '$.execution_time', ?,
                       '$.completed_at', ?
                   ),
                   status = ?
                   WHERE plan_id = ?""",
                (
                    'success' if success else 'failure',
                    execution_time_seconds,
                    datetime.utcnow().isoformat(),
                    'completed' if success else 'failed',
                    plan_id
                )
            )
            self.db.commit()
            
            logger.info(
                f"[PLANNER] Recorded plan outcome: {plan_id} = "
                f"{'success' if success else 'failure'}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"[PLANNER] Failed to record plan outcome: {e}", exc_info=True)
            return False
