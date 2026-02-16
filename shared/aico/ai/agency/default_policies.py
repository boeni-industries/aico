"""
Default Policy Rules for Values & Ethics

Provides sensible default policies for goal evaluation, curiosity gating,
and world model updates. These can be overridden by deployment or user configs.
"""

from .values_ethics import PolicyRule, PolicyEffect, PolicyTargetType, PolicyScope


# ============================================================================
# Default Global Policy Rules
# ============================================================================

DEFAULT_POLICIES = [
    # ========================================================================
    # Goal Policies
    # ========================================================================
    
    PolicyRule(
        rule_id="default_goal_high_curiosity_warning",
        rule_name="High Curiosity Goal Warning",
        target_type=PolicyTargetType.GOAL,
        conditions={"origin": "curiosity", "curiosity_intensity": 0.8},
        effect=PolicyEffect.ALLOW_WITH_WARNING,
        user_message_template="This goal is driven by high curiosity. Please review before activation.",
        priority=50,
        scope=PolicyScope.GLOBAL
    ),
    
    # ========================================================================
    # Curiosity Signal Policies
    # ========================================================================
    
    PolicyRule(
        rule_id="default_curiosity_sensitive_life_area",
        rule_name="Sensitive Life Area Curiosity Gate",
        target_type=PolicyTargetType.CURIOSITY_SIGNAL,
        conditions={"life_area": "sensitive"},  # Matches any in profile.sensitive_life_areas
        effect=PolicyEffect.NEEDS_CONSENT,
        user_message_template="This curiosity signal touches a sensitive life area. Do you want to explore this?",
        priority=10,
        scope=PolicyScope.GLOBAL
    ),
    
    PolicyRule(
        rule_id="default_curiosity_high_intensity",
        rule_name="High Intensity Curiosity Warning",
        target_type=PolicyTargetType.CURIOSITY_SIGNAL,
        conditions={"curiosity_intensity": 0.7},
        effect=PolicyEffect.ALLOW_WITH_WARNING,
        user_message_template="This curiosity signal has high intensity. Proceed with awareness.",
        priority=60,
        scope=PolicyScope.GLOBAL
    ),
    
    # ========================================================================
    # Plan Policies
    # ========================================================================
    
    PolicyRule(
        rule_id="default_plan_multi_step_warning",
        rule_name="Multi-Step Plan Warning",
        target_type=PolicyTargetType.PLAN,
        conditions={"min_steps": 5},
        effect=PolicyEffect.ALLOW_WITH_WARNING,
        user_message_template="This plan has multiple steps. Review before execution.",
        priority=70,
        scope=PolicyScope.GLOBAL
    ),
]


async def install_default_policies(values_ethics_service, uow) -> int:
    """
    Install default policies into the database.
    
    Args:
        values_ethics_service: ValuesEthicsService instance
        uow: Unit of Work for database access
        
    Returns:
        Number of policies installed
    """
    installed = 0
    
    for policy in DEFAULT_POLICIES:
        # Check if already exists
        existing = await values_ethics_service.get_policy_rule(policy.rule_id, uow)
        if not existing:
            await values_ethics_service.add_policy_rule(policy, uow)
            installed += 1
    
    return installed
