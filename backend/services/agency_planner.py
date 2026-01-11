"""
Backend LLM-based planning helper for agency system.

This module provides LLM-enhanced planning capabilities that use the shared
agency templates and modelservice to refine plan steps. It maintains low
coupling by keeping the shared agency layer pure and deterministic.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager

# Shared agency imports (no backend dependencies)
from aico.ai.agency.models import Goal, Plan, PlanStep, PlanStatus, StepStatus
from aico.ai.agency.templates import PLAN_SHAPES, PlanShape

# Backend-specific imports
from backend.services.modelservice_client import ModelServiceClient


logger = get_logger("backend.services.agency_planner")


class LLMPlanningHelper:
    """Backend helper for LLM-enhanced planning.
    
    Phase 1: Uses templated prompts + hand-authored plan shapes to refine
    plan steps via modelservice. Keeps shared agency code decoupled from
    backend/modelservice dependencies.
    """
    
    def __init__(self, config: ConfigurationManager, modelservice_client: ModelServiceClient):
        self.config = config
        self.modelservice = modelservice_client
        self.logger = logger
        
        # Use the same conversation model as conversation_engine (no duplicate config)
        conversation_model_config = config.get("core.modelservice.ollama.default_models.conversation", {})
        self.model_name = conversation_model_config.get("name", "huihui_ai/qwen3-abliterated:8b-v2")
        
        # Get agency planning configuration
        agency_config = config.get("core.services.agency.planning", {})
        self.llm_enabled = agency_config.get("enable_llm_refinement", True)
        self.llm_temperature = agency_config.get("llm_temperature", 0.7)
        self.llm_max_tokens = agency_config.get("llm_max_tokens", 1000)
    
    async def refine_plan_with_llm(
        self,
        goal: Goal,
        base_plan: Plan,
        selected_shape: Optional[PlanShape] = None
    ) -> Plan:
        """Refine a base plan using LLM with templated prompts.
        
        Args:
            goal: The goal this plan is for
            base_plan: The deterministic base plan from shared Planner
            selected_shape: The plan shape that was used (if any)
            
        Returns:
            Refined plan with LLM-enhanced step descriptions
        """
        
        if not self.llm_enabled:
            self.logger.debug("[AGENCY_PLANNER] LLM planning disabled, returning base plan")
            return base_plan
        
        try:
            self.logger.info(
                "[AGENCY_PLANNER] Refining plan with LLM",
                extra={
                    "goal_id": goal.goal_id,
                    "plan_id": base_plan.plan_id,
                    "base_step_count": len(base_plan.steps),
                    "shape_id": selected_shape["id"] if selected_shape else None,
                }
            )
            
            # Build planning prompt
            prompt = self._build_planning_prompt(goal, base_plan, selected_shape)
            
            # Call modelservice
            messages = [
                {
                    "role": "system",
                    "content": "You are an AI planning assistant. Your task is to refine high-level plan steps into concrete, actionable instructions."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await self.modelservice.get_chat_completions(
                model=self.model_name,
                messages=messages,
                options={
                    "temperature": self.llm_temperature,
                    "max_tokens": self.llm_max_tokens
                }
            )
            
            if not response.get("success"):
                self.logger.warning(
                    f"[AGENCY_PLANNER] LLM call failed: {response.get('error')}, using base plan"
                )
                return base_plan
            
            # Parse LLM response
            llm_content = response.get("data", {}).get("content", "")
            refined_steps = self._parse_llm_response(llm_content, base_plan)
            
            if not refined_steps:
                self.logger.warning("[AGENCY_PLANNER] Failed to parse LLM response, using base plan")
                return base_plan
            
            # Create refined plan with LLM-enhanced steps
            refined_plan = Plan(
                plan_id=base_plan.plan_id,
                goal_id=base_plan.goal_id,
                status=base_plan.status,
                steps=refined_steps,
                metadata={
                    **base_plan.metadata,
                    "llm_refined": True,
                    "llm_model": self.model_name,
                    "refined_at": datetime.now(UTC).isoformat(),
                    "original_step_count": len(base_plan.steps),
                }
            )
            
            self.logger.info(
                "[AGENCY_PLANNER] Plan refined successfully",
                extra={
                    "goal_id": goal.goal_id,
                    "plan_id": refined_plan.plan_id,
                    "refined_step_count": len(refined_steps),
                }
            )
            
            return refined_plan
            
        except Exception as e:
            self.logger.error(f"[AGENCY_PLANNER] Error refining plan with LLM: {e}")
            import traceback
            traceback.print_exc()
            # Fail gracefully: return base plan
            return base_plan
    
    def _build_planning_prompt(
        self,
        goal: Goal,
        base_plan: Plan,
        selected_shape: Optional[PlanShape]
    ) -> str:
        """Build a templated prompt for LLM-based plan refinement."""
        
        prompt_parts = [
            f"Goal: {goal.title}",
        ]
        
        if goal.description:
            prompt_parts.append(f"Description: {goal.description}")
        
        prompt_parts.append(f"Goal Type: {goal.goal_type}")
        
        if selected_shape:
            prompt_parts.append(f"\nPlan Shape: {selected_shape['name']}")
            prompt_parts.append("Base Steps:")
            for step in base_plan.steps:
                prompt_parts.append(f"  {step.order}. {step.description}")
        else:
            prompt_parts.append("\nBase Steps:")
            for step in base_plan.steps:
                prompt_parts.append(f"  {step.order}. {step.description}")
        
        prompt_parts.append(
            f"\nRefine these {len(base_plan.steps)} steps into concrete, actionable instructions. "
            f"Keep the same number of steps ({len(base_plan.steps)}) and maintain their order. "
            "Make each step specific and clear. Return the refined steps as a numbered list."
        )
        
        return "\n".join(prompt_parts)
    
    def _parse_llm_response(
        self,
        llm_content: str,
        base_plan: Plan
    ) -> List[PlanStep]:
        """Parse LLM response into refined PlanStep objects.
        
        Expects numbered list format:
        1. First step description
        2. Second step description
        etc.
        """
        
        refined_steps: List[PlanStep] = []
        
        # Try to parse as numbered list
        lines = llm_content.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Match patterns like "1.", "1)", "Step 1:", etc.
            import re
            match = re.match(r'^(?:Step\s+)?(\d+)[\.\):\-]\s*(.+)$', line, re.IGNORECASE)
            
            if match:
                step_num = int(match.group(1))
                description = match.group(2).strip()
                
                # Find corresponding base step to preserve metadata
                base_step = None
                if step_num <= len(base_plan.steps):
                    base_step = base_plan.steps[step_num - 1]
                
                refined_steps.append(
                    PlanStep(
                        step_id=base_step.step_id if base_step else f"llm-step-{step_num}",
                        order=step_num,
                        description=description,
                        status=StepStatus.PENDING,
                        skill_id=base_step.skill_id if base_step else None,
                        metadata={
                            **(base_step.metadata if base_step else {}),
                            "llm_refined": True,
                            "original_description": base_step.description if base_step else None,
                        }
                    )
                )
        
        # Validate we got the right number of steps
        if len(refined_steps) != len(base_plan.steps):
            self.logger.warning(
                f"[AGENCY_PLANNER] LLM returned {len(refined_steps)} steps, expected {len(base_plan.steps)}"
            )
            return []
        
        return refined_steps


def create_llm_planning_helper(
    config: ConfigurationManager,
    modelservice_client: ModelServiceClient
) -> LLMPlanningHelper:
    """Factory function for creating LLM planning helper."""
    return LLMPlanningHelper(config, modelservice_client)
