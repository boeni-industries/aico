"""
Agency Skills System

Skills are executable actions that the agency can perform to achieve goals.

Skills are organized by category:
- analysis: Conversation and pattern analysis
- memory: Memory search and retrieval
- knowledge: Knowledge graph management
- reflection: Goal and progress reflection
- communication: AICO-initiated user interaction
"""

from .registry import SkillRegistry, Skill, SkillParameter, SkillResult
from .matcher import SkillMatcher, SkillMatch, MatchStrategy

# Import skills from their category modules
from .analysis import AnalyzeConversationSkill
from .memory import SearchMemorySkill
from .knowledge import UpdateKnowledgeGraphSkill
from .reflection import ReflectOnGoalSkill
from .communication import AskUserSkill, InitiateConversationSkill
from .maintenance import (
    MaintenanceConnectivityFullScanSkill,
    MaintenanceConnectivityVerifyComponentSkill,
    MaintenanceAgencyCleanupExecutionsSkill,
)

__all__ = [
    # Core registry
    "SkillRegistry",
    "Skill",
    "SkillParameter",
    "SkillResult",
    # Skill matching
    "SkillMatcher",
    "SkillMatch",
    "MatchStrategy",
    # Analysis skills
    "AnalyzeConversationSkill",
    # Memory skills
    "SearchMemorySkill",
    # Knowledge skills
    "UpdateKnowledgeGraphSkill",
    # Reflection skills
    "ReflectOnGoalSkill",
    # Communication skills
    "AskUserSkill",
    "InitiateConversationSkill",
    # Maintenance skills
    "MaintenanceConnectivityFullScanSkill",
    "MaintenanceConnectivityVerifyComponentSkill",
    "MaintenanceAgencyCleanupExecutionsSkill",
]
