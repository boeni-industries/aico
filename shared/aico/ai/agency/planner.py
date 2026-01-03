from __future__ import annotations

import uuid
import json
from datetime import datetime, timedelta, UTC
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from collections import defaultdict

from aico.core.logging import get_logger
from aico.core.json_sanitizer import sanitize_llm_json
from aico.ai.agency.models import (
    Goal,
    Plan,
    PlanStep,
    PlanStatus,
    StepStatus,
)
from aico.ai.agency.templates import PLAN_SHAPES, PlanShape
from aico.ai.agency.skills.matcher import SkillMatcher


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
        llm_client: Any,
        skill_registry: Optional[Any] = None,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 3600,
    ):
        """Initialize planner.
        
        Args:
            llm_client: LLM client for plan generation
            skill_registry: Optional skill registry for skill assignment
            enable_caching: Whether to cache generated plans
            cache_ttl_seconds: Cache TTL in seconds
        """
        self.llm_client = llm_client
        self.skill_registry = skill_registry
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self._plan_cache: Dict[str, Dict[str, Any]] = {}
        
        # Initialize skill matcher if registry available
        self.skill_matcher = None
        if skill_registry:
            self.skill_matcher = SkillMatcher(skill_registry)
            logger.info("[PLANNER] Initialized with SkillMatcher for robust skill assignment")
        
        logger.debug(
            f"[PLANNER] Initialized with LLM: {llm_client is not None}, "
            f"caching: {enable_caching}, "
            f"skill_registry: {skill_registry is not None}"
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
                    logger.exception(f"[PLANNER] Pattern-based planning failed: {e}")
        
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
                logger.exception(f"[PLANNER] LLM plan generation failed: {e}")
        
        # Fall back to template-based
        plan = await self._generate_template_plan(goal)
        if plan:
            logger.info(f"[PLANNER] Generated template plan for goal {goal.goal_id}")
            # Assign skills to template plan steps
            if self.skill_registry:
                plan.steps = await self._assign_skills_to_steps(plan.steps)
                logger.debug(f"[PLANNER] Assigned skills to {len(plan.steps)} template plan steps")
            return plan
        
        # Last resort: simple fallback
        plan = self._generate_simple_fallback(goal)
        logger.info(f"[PLANNER] Generated simple fallback plan for goal {goal.goal_id}")
        # Assign skills to fallback plan steps
        if self.skill_registry:
            plan.steps = await self._assign_skills_to_steps(plan.steps)
            logger.debug(f"[PLANNER] Assigned skills to {len(plan.steps)} fallback plan steps")
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
            
            # Call LLM using ModelServiceClient API
            if hasattr(self.llm_client, 'get_chat_completions'):
                # Use chat completions API with system + user message
                messages = [
                    {"role": "system", "content": "You are a helpful planning assistant."},
                    {"role": "user", "content": prompt}
                ]
                model = getattr(self.llm_client, 'model_name', 'eve')
                # Request structured JSON output with schema for variable-length array
                json_schema = {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "preconditions": {"type": "array", "items": {"type": "string"}},
                                    "suggested_skills": {"type": "array", "items": {"type": "string"}}
                                },
                                "required": ["description", "preconditions", "suggested_skills"]
                            }
                        }
                    },
                    "required": ["steps"]
                }
                options = {"response_format": json_schema}
                result = await self.llm_client.get_chat_completions(model, messages, options=options)
                logger.debug(f"[PLANNER] LLM result structure: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")
                logger.debug(f"[PLANNER] LLM result content: {result}")
                # Extract content from modelservice_client response structure
                response = result.get("data", {}).get("content", "")
                logger.debug(f"[PLANNER] Extracted response length: {len(response)}, first 100 chars: {response[:100] if response else 'EMPTY'}")
            elif hasattr(self.llm_client, 'get_completions'):
                # Use completions API with just prompt
                model = getattr(self.llm_client, 'model_name', 'eve')
                result = await self.llm_client.get_completions(model, prompt)
                logger.debug(f"[PLANNER] LLM result structure: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")
                logger.debug(f"[PLANNER] LLM result content: {result}")
                # Extract content from modelservice_client response structure
                response = result.get("data", {}).get("content", "")
                logger.debug(f"[PLANNER] Extracted response length: {len(response)}, first 100 chars: {response[:100] if response else 'EMPTY'}")
            else:
                logger.warning("[PLANNER] LLM client has no compatible method")
                return None
            
            # Parse LLM response into plan steps
            steps = self._parse_llm_response(response, goal)
            
            if not steps:
                return None
            
            # Assign skills to steps based on their descriptions and metadata
            if self.skill_registry:
                steps = await self._assign_skills_to_steps(steps)
                logger.debug(f"[PLANNER] Assigned skills to {len(steps)} steps")
            
            plan = Plan(
                plan_id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                status=PlanStatus.DRAFT,
                steps=steps,
                metadata={
                    "generated_at": datetime.now(UTC).isoformat(),
                    "strategy": PlanStrategy.LLM_GENERATED.value,
                    "llm_model": getattr(self.llm_client, 'model_name', 'unknown'),
                },
            )
            
            return plan
            
        except Exception as e:
            logger.exception(f"[PLANNER] LLM plan generation error: {e}")
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
                "generated_at": datetime.now(UTC).isoformat(),
                "strategy": PlanStrategy.TEMPLATE_BASED.value,
                "template_id": selected_shape["id"],
            },
        )

        return plan
    
    def _generate_simple_fallback(self, goal: Goal) -> Plan:
        """Generate goal-specific fallback plan with actionable steps.
        
        Args:
            goal: Goal to plan for
            
        Returns:
            Plan with 5-7 concrete steps based on goal type
        """
        # Generate goal-specific steps based on common patterns
        steps = self._generate_goal_specific_steps(goal)
        
        plan = Plan(
            plan_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            status=PlanStatus.DRAFT,
            steps=steps,
            metadata={
                "generated_at": datetime.now(UTC).isoformat(),
                "strategy": PlanStrategy.SIMPLE_FALLBACK.value,
            },
        )

        return plan
    
    def _generate_goal_specific_steps(self, goal: Goal) -> List[PlanStep]:
        """Generate actionable steps based on goal content.
        
        Args:
            goal: Goal to generate steps for
            
        Returns:
            List of 5-7 concrete, actionable steps
        """
        title_lower = goal.title.lower()
        description_lower = (goal.description or "").lower()
        combined = f"{title_lower} {description_lower}"
        
        # Learning goals (language, skill, subject)
        if any(word in combined for word in ["learn", "study", "practice", "master", "improve"]):
            if any(word in combined for word in ["language", "spanish", "french", "german", "english"]):
                return [
                    PlanStep(
                        step_id=str(uuid.uuid4()),
                        order=1,
                        description=f"Research and compare learning platforms (Duolingo, Babbel, iTalki, etc.) for {goal.title}",
                        status=StepStatus.PENDING,
                        skill_id="initiate_conversation",
                        metadata={"phase": "research", "conversation_topic": "language_learning_platforms"},
                    ),
                    PlanStep(
                        step_id=str(uuid.uuid4()),
                        order=2,
                        description="Set specific proficiency goal (conversational, academic, travel, or business level)",
                        status=StepStatus.PENDING,
                        skill_id="ask_user",
                        metadata={"phase": "planning", "question_type": "proficiency_goal"},
                    ),
                    PlanStep(
                        step_id=str(uuid.uuid4()),
                        order=3,
                        description="Create study schedule (daily time commitment, weekly goals)",
                        status=StepStatus.PENDING,
                        skill_id="ask_user",
                        metadata={"phase": "planning", "question_type": "schedule"},
                    ),
                    PlanStep(
                        step_id=str(uuid.uuid4()),
                        order=4,
                        description="Choose platform and create account or enroll in course",
                        status=StepStatus.PENDING,
                        skill_id="initiate_conversation",
                        metadata={"phase": "setup", "conversation_topic": "platform_selection"},
                    ),
                    PlanStep(
                        step_id=str(uuid.uuid4()),
                        order=5,
                        description="Complete first lesson or module (vocabulary, grammar basics)",
                        status=StepStatus.PENDING,
                        skill_id="initiate_conversation",
                        metadata={"phase": "action", "conversation_topic": "first_lesson_check_in"},
                    ),
                    PlanStep(
                        step_id=str(uuid.uuid4()),
                        order=6,
                        description="Find conversation partner or language exchange group",
                        status=StepStatus.PENDING,
                        skill_id="initiate_conversation",
                        metadata={"phase": "action", "conversation_topic": "conversation_partner"},
                    ),
                    PlanStep(
                        step_id=str(uuid.uuid4()),
                        order=7,
                        description="Schedule first practice conversation session",
                        status=StepStatus.PENDING,
                        skill_id="ask_user",
                        metadata={"phase": "action", "question_type": "practice_scheduling"},
                    ),
                ]
            else:
                return self._generate_generic_learning_steps(goal)
        
        # Project/creation goals
        elif any(word in combined for word in ["build", "create", "make", "develop", "write"]):
            return self._generate_project_steps(goal)
        
        # Health/fitness goals
        elif any(word in combined for word in ["exercise", "fitness", "health", "workout", "diet"]):
            return self._generate_health_steps(goal)
        
        # Generic fallback (5 steps)
        else:
            return self._generate_generic_steps(goal)
    
    def _generate_generic_learning_steps(self, goal: Goal) -> List[PlanStep]:
        """Generic learning goal steps."""
        return [
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=1,
                description=f"Research learning resources and methods for {goal.title}",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "research", "conversation_topic": "learning_resources"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=2,
                description="Define learning objectives and success criteria",
                status=StepStatus.PENDING,
                skill_id="ask_user",
                metadata={"phase": "planning", "question_type": "learning_objectives"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=3,
                description="Create study plan with timeline and milestones",
                status=StepStatus.PENDING,
                skill_id="ask_user",
                metadata={"phase": "planning", "question_type": "study_plan"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=4,
                description="Gather necessary materials or enroll in course",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "setup", "conversation_topic": "materials_enrollment"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=5,
                description="Complete first learning session or module",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "action", "conversation_topic": "first_session"},
            ),
        ]
    
    def _generate_project_steps(self, goal: Goal) -> List[PlanStep]:
        """Project/creation goal steps."""
        return [
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=1,
                description=f"Define project scope and requirements for {goal.title}",
                status=StepStatus.PENDING,
                skill_id="ask_user",
                metadata={"phase": "planning", "question_type": "project_scope"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=2,
                description="Break down project into major components or phases",
                status=StepStatus.PENDING,
                skill_id="ask_user",
                metadata={"phase": "planning", "question_type": "project_breakdown"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=3,
                description="Gather necessary tools, materials, or resources",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "setup", "conversation_topic": "project_resources"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=4,
                description="Complete first major component or milestone",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "action", "conversation_topic": "first_milestone"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=5,
                description="Review progress and refine remaining work",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "review", "conversation_topic": "progress_review"},
            ),
        ]
    
    def _generate_health_steps(self, goal: Goal) -> List[PlanStep]:
        """Health/fitness goal steps."""
        return [
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=1,
                description=f"Define specific health/fitness objectives for {goal.title}",
                status=StepStatus.PENDING,
                skill_id="ask_user",
                metadata={"phase": "planning", "question_type": "health_objectives"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=2,
                description="Research appropriate methods and best practices",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "research", "conversation_topic": "health_methods"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=3,
                description="Create weekly schedule with specific activities",
                status=StepStatus.PENDING,
                skill_id="ask_user",
                metadata={"phase": "planning", "question_type": "schedule"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=4,
                description="Complete first session or day of new routine",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "action", "conversation_topic": "first_session"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=5,
                description="Track progress and adjust approach as needed",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "review", "conversation_topic": "progress_tracking"},
            ),
        ]
    
    def _generate_generic_steps(self, goal: Goal) -> List[PlanStep]:
        """Generic goal steps (last resort)."""
        return [
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=1,
                description=f"Clarify specific objectives and constraints for {goal.title}",
                status=StepStatus.PENDING,
                skill_id="ask_user",
                metadata={"phase": "planning", "question_type": "objectives"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=2,
                description="Research approaches and gather necessary information",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "research", "conversation_topic": "approaches"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=3,
                description="Create action plan with timeline and milestones",
                status=StepStatus.PENDING,
                skill_id="ask_user",
                metadata={"phase": "planning", "question_type": "action_plan"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=4,
                description="Take first concrete action towards goal",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "action", "conversation_topic": "first_action"},
            ),
            PlanStep(
                step_id=str(uuid.uuid4()),
                order=5,
                description="Review progress and adjust plan as needed",
                status=StepStatus.PENDING,
                skill_id="initiate_conversation",
                metadata={"phase": "review", "conversation_topic": "progress_review"},
            ),
        ]
    
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
        
        prompt = f"""Create a detailed action plan for this goal:

Goal: {goal.title}
Description: {goal.description or 'No additional description'}
Type: {goal.goal_type}
Priority: {goal.priority.value}

Generate 3-7 concrete, actionable steps to achieve this goal.

CRITICAL REQUIREMENTS FOR EACH STEP:
- Must be a DISCRETE, EXECUTABLE action (not an ongoing process or abstract strategy)
- Must be something a specific software skill/function can perform
- Must have clear inputs and outputs
- Avoid meta-planning concepts like "set goals", "track progress", "adjust plan", "create schedule"
- Instead, break these down into specific actions like:
  * "Query user's calendar for available time slots"
  * "Search knowledge base for user's current skill level in X"
  * "Generate a list of online communities for topic Y"
  * "Ask user to specify their weekly time commitment"
  * "Analyze past learning patterns from user history"

EXAMPLES OF GOOD STEPS:
✓ "Search the web for top-rated Spanish language learning apps"
✓ "Query user's memory for previous Python projects completed"
✓ "Generate a personalized study plan template with daily tasks"
✓ "Find and list 5 Spanish-English language exchange groups in user's city"

EXAMPLES OF BAD STEPS (DO NOT GENERATE THESE):
✗ "Set clear, prioritized goals" (too abstract, not executable)
✗ "Track progress weekly" (ongoing process, not a discrete action)
✗ "Adjust the plan based on feedback" (meta-planning, not actionable)
✗ "Use active learning techniques" (strategy, not a specific action)

For each step provide:
- description: Clear, specific action that can be executed by a software skill
- preconditions: What information or state is needed before this step
- suggested_skills: Specific skill names that could perform this action (e.g., "web_search", "query_memory", "ask_user", "analyze_data")

Return your plan as a JSON object with a "steps" array."""
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
            # Use the robust JSON sanitizer
            response = response.strip()
            logger.debug(f"[PLANNER] Parsing LLM response (length: {len(response)}, first 200 chars: {response[:200]})")
            
            # Sanitize and parse JSON using the reusable utility
            # Expecting an object with "steps" array due to JSON Schema
            result = sanitize_llm_json(response, expected_type=dict, strict=False)
            
            if not result.success:
                logger.error(f"[PLANNER] JSON sanitization failed: {result.error}")
                if result.strategy:
                    logger.debug(f"[PLANNER] Failed after trying strategy: {result.strategy.value}")
                return []
            
            # Extract steps array from the response object
            response_obj = result.data
            if not isinstance(response_obj, dict) or "steps" not in response_obj:
                logger.error(f"[PLANNER] Response missing 'steps' array: {response_obj}")
                return []
            
            steps_data = response_obj["steps"]
            if not isinstance(steps_data, list):
                logger.error(f"[PLANNER] 'steps' is not an array: {type(steps_data)}")
                return []
            
            logger.info(f"[PLANNER] Successfully parsed JSON using strategy: {result.strategy.value}, got {len(steps_data)} steps")
            
            # Convert to PlanStep objects
            steps = []
            for index, step_data in enumerate(steps_data, start=1):
                if not isinstance(step_data, dict):
                    logger.warning(f"[PLANNER] Step {index} is not a dict, skipping")
                    continue
                    
                description = step_data.get('description', '').strip()
                if not description:
                    logger.warning(f"[PLANNER] Step {index} has no description, skipping")
                    continue
                
                step = PlanStep(
                    step_id=str(uuid.uuid4()),
                    order=index,
                    description=description,
                    status=StepStatus.PENDING,
                    metadata={
                        'preconditions': step_data.get('preconditions', []),
                        'suggested_skills': step_data.get('suggested_skills', []),
                        'llm_generated': True,
                    },
                )
                steps.append(step)
            
            if not steps:
                logger.warning("[PLANNER] No valid steps extracted from LLM response")
                return []
            
            logger.info(f"[PLANNER] Successfully created {len(steps)} plan steps")
            return steps
            
        except Exception as e:
            logger.exception(f"[PLANNER] Error parsing LLM response: {e}")
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
        cached_time = datetime.fromisoformat(cached['timestamp']).replace(tzinfo=UTC)
        age_seconds = (datetime.now(UTC) - cached_time).total_seconds()
        
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
                'generated_at': datetime.now(UTC).isoformat(),
            },
        )
        
        return new_plan
    
    async def _assign_skills_to_steps(self, steps: List[PlanStep]) -> List[PlanStep]:
        """Assign skills to plan steps using sophisticated SkillMatcher.
        
        Uses multi-tier matching strategy:
        1. Exact skill_id match (if already assigned)
        2. Semantic similarity (embeddings)
        3. Keyword/synonym matching
        4. Category-based matching (shape_role)
        5. LLM-suggested skill names (fuzzy matching)
        6. Fallback to generic skills
        
        Args:
            steps: List of plan steps to assign skills to
            
        Returns:
            Steps with skill_id assigned where possible
        """
        if not self.skill_matcher:
            logger.warning("[PLANNER] No skill matcher available for skill assignment")
            return steps
        
        # Assign skills to each step
        for step in steps:
            if step.skill_id:
                # Already has a skill assigned (from template)
                logger.debug(
                    f"[PLANNER] Step already has skill assigned: {step.skill_id}"
                )
                continue
            
            # Extract LLM-suggested skills from metadata if available
            llm_suggested_skills = step.metadata.get('suggested_skills', [])
            
            # Use skill matcher to find best match
            try:
                match = await self.skill_matcher.match_skill(
                    step_description=step.description,
                    step_metadata=step.metadata,
                    llm_suggested_skills=llm_suggested_skills,
                )
                
                if match:
                    step.skill_id = match.skill_id
                    # Store match metadata for debugging
                    step.metadata['skill_match_confidence'] = match.confidence
                    step.metadata['skill_match_strategy'] = match.strategy.value
                    step.metadata['skill_match_reasoning'] = match.reasoning
                    
                    logger.debug(
                        f"[PLANNER] Assigned skill '{match.skill_id}' to step "
                        f"(confidence={match.confidence:.2f}, strategy={match.strategy.value})"
                    )
                else:
                    logger.debug(
                        f"[PLANNER] No skill match found for step: {step.description[:50]}..."
                    )
            except Exception as e:
                logger.exception(
                    f"[PLANNER] Error matching skill for step: {e}"
                )
        
        # Log summary of skill assignment results
        matched_count = sum(1 for step in steps if step.skill_id)
        unmatched_count = len(steps) - matched_count
        
        if unmatched_count == 0:
            logger.info(f"[PLANNER] All {len(steps)} steps successfully matched to skills")
        else:
            logger.info(
                f"[PLANNER] Skill assignment complete: {matched_count}/{len(steps)} matched, "
                f"{unmatched_count} unmatched (logged as skill gaps)"
            )
        
        return steps
    
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
            'timestamp': datetime.now(UTC).isoformat(),
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
            # Skills are now code-only (registered in-memory)
            # All skills in skill_ids are assumed available if they're in the registry
            # The skill registry validates availability at registration time
            availability = {skill_id: True for skill_id in skill_ids}
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
            cutoff_date = (datetime.now(UTC) - timedelta(days=lookback_days)).isoformat()
            
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
            logger.exception(f"[PLANNER] Failed to detect patterns: {e}")
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
                    'generated_at': datetime.now(UTC).isoformat(),
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
            logger.exception(f"[PLANNER] Failed to generate plan from pattern: {e}")
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
                    datetime.now(UTC).isoformat(),
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
            logger.exception(f"[PLANNER] Failed to record plan outcome: {e}")
            return False
