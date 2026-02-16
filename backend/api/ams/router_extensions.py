"""
AMS Router Extensions

Additional helper functions for skill overview and memory evolution tracking.
"""

from datetime import datetime, timedelta, UTC
from typing import List, Dict, Any
from aico.core.logging import get_logger
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork
from aico.services.ams_service import AMSService

from .schemas import (
    SkillDetailResponse,
    SkillOverviewResponse,
    MemoryMetricsSnapshot,
    MemoryGrowthStats,
    MemoryEvolutionResponse,
)

logger = get_logger("backend.api.ams.extensions")


async def get_skill_overview(user_id: str) -> SkillOverviewResponse:
    """
    Get comprehensive overview of all available skills with usage data.
    Uses UoW and AMSService instead of raw SQL.
    """
    try:
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            ams_service = AMSService(uow)
            
            # Get all skills and user confidence data
            all_skills = await ams_service.get_all_skills()
            user_confidence = await ams_service.get_user_skill_confidence(user_id)
            
            # Build confidence lookup
            confidence_map = {uc.skill_id: uc for uc in user_confidence}
            
            skills = []
            active_count = 0
            
            for skill in all_skills:
                uc = confidence_map.get(skill.skill_id)
                confidence = (uc.confidence_score * 100) if uc and uc.confidence_score else None
                usage_count = uc.usage_count if uc else None
                
                if usage_count and usage_count > 0:
                    active_count += 1
                
                skills.append(SkillDetailResponse(
                    skill_id=skill.skill_id,
                    skill_name=skill.skill_name,
                    skill_type=skill.skill_type,
                    status=skill.status,
                    confidence_score=confidence,
                    usage_count=usage_count,
                    positive_count=uc.positive_count if uc else None,
                    negative_count=uc.negative_count if uc else None,
                    last_used_at=uc.last_used_at if uc else None,
                    created_at=skill.created_at,
                ))
            
            # Sort: used skills first, then by usage count, then by name
            skills.sort(key=lambda s: (
                0 if s.usage_count else 1,
                -(s.usage_count or 0),
                s.skill_name
            ))
            
            return SkillOverviewResponse(
                total_skills=len(skills),
                active_skills=active_count,
                skills=skills,
            )
        
    except Exception as e:
        logger.warning(f"Skill overview query failed: {e}")
        return SkillOverviewResponse(
            total_skills=0,
            active_skills=0,
            skills=[],
        )


async def get_memory_evolution(user_id: str) -> MemoryEvolutionResponse:
    """
    Get memory evolution metrics showing how memory grows over time.
    
    Tracks working memory, semantic facts, knowledge graph entities/relationships,
    and consolidation activity across different time periods.
    """
    try:
        current_time = datetime.now(UTC)
        
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            # Get current memory metrics via repositories
            trajectories = await uow.ams_trajectories.list(
                filters={'user_id': user_id, 'archived': False},
                limit=100000
            )
            working_memory_count = len(trajectories)
            
            user_memories = await uow.ams_user_memories.list(
                filters={'user_id': user_id},
                limit=100000
            )
            semantic_facts_count = len(user_memories)
            
            kg_nodes = await uow.kg_nodes.list(
                filters={'user_id': user_id},
                limit=100000
            )
            kg_entities = len(kg_nodes)
            
            kg_edges = await uow.kg_edges.list(
                filters={'user_id': user_id},
                limit=100000
            )
            kg_relationships = len(kg_edges)
            
            # Count unique conversations
            unique_conversations = set(t.conversation_id for t in trajectories)
            total_conversations = len(unique_conversations)
            
            # Calculate 7-day growth
            seven_days_ago = current_time - timedelta(days=7)
            
            facts_7d = sum(1 for m in user_memories 
                          if m.created_at and (
                              datetime.fromisoformat(m.created_at.replace('Z', '+00:00')) if isinstance(m.created_at, str)
                              else m.created_at
                          ) > seven_days_ago)
            
            entities_7d = sum(1 for n in kg_nodes 
                             if n.created_at and (
                                 datetime.fromisoformat(n.created_at.replace('Z', '+00:00')) if isinstance(n.created_at, str)
                                 else n.created_at
                             ) > seven_days_ago)
            
            relationships_7d = sum(1 for e in kg_edges 
                                  if e.created_at and (
                                      datetime.fromisoformat(e.created_at.replace('Z', '+00:00')) if isinstance(e.created_at, str)
                                      else e.created_at
                                  ) > seven_days_ago)
            
            consolidations_7d = 0
            
            # Calculate 30-day growth
            thirty_days_ago = current_time - timedelta(days=30)
            
            facts_30d = sum(1 for m in user_memories 
                           if m.created_at and (
                               datetime.fromisoformat(m.created_at.replace('Z', '+00:00')) if isinstance(m.created_at, str)
                               else m.created_at
                           ) > thirty_days_ago)
            
            entities_30d = sum(1 for n in kg_nodes 
                              if n.created_at and (
                                  datetime.fromisoformat(n.created_at.replace('Z', '+00:00')) if isinstance(n.created_at, str)
                                  else n.created_at
                              ) > thirty_days_ago)
            
            relationships_30d = sum(1 for e in kg_edges 
                                   if e.created_at and (
                                       datetime.fromisoformat(e.created_at.replace('Z', '+00:00')) if isinstance(e.created_at, str)
                                       else e.created_at
                                   ) > thirty_days_ago)
            
            consolidations_30d = 0
        
        current_metrics = MemoryMetricsSnapshot(
            timestamp=current_time.isoformat(),
            working_memory_count=working_memory_count,
            semantic_facts_count=semantic_facts_count,
            knowledge_graph_entities=kg_entities,
            knowledge_graph_relationships=kg_relationships,
            total_conversations=total_conversations,
        )
        
        growth_7d = MemoryGrowthStats(
            period_days=7,
            facts_added=facts_7d,
            entities_added=entities_7d,
            relationships_added=relationships_7d,
            consolidation_sessions=consolidations_7d,
        )
        
        growth_30d = MemoryGrowthStats(
            period_days=30,
            facts_added=facts_30d,
            entities_added=entities_30d,
            relationships_added=relationships_30d,
            consolidation_sessions=consolidations_30d,
        )
        
        # Generate insights
        insights = []
        
        if facts_7d > 0:
            daily_avg = facts_7d / 7
            insights.append(f"Adding ~{daily_avg:.1f} facts per day")
        
        if entities_7d > 0:
            insights.append(f"{entities_7d} new entities discovered this week")
        
        if consolidations_7d > 0:
            insights.append(f"{consolidations_7d} consolidation sessions completed")
        
        if semantic_facts_count > 100:
            insights.append(f"Rich semantic memory with {semantic_facts_count} facts")
        
        if kg_entities > 50:
            insights.append(f"Knowledge graph contains {kg_entities} entities")
        
        # Only show insights if we have actual data
        # Don't add placeholder/mock insights
        
        # Historical snapshots would require a time-series table
        # Don't return mock/empty data - return empty list until we have real historical tracking
        historical_snapshots = []
        
        return MemoryEvolutionResponse(
            current_metrics=current_metrics,
            growth_7d=growth_7d,
            growth_30d=growth_30d,
            historical_snapshots=historical_snapshots,
            insights=insights[:5],
        )
        
    except Exception as e:
        logger.warning(f"Memory evolution query failed: {e}")
        
        # Return default values
        current_time = datetime.now(UTC)
        return MemoryEvolutionResponse(
            current_metrics=MemoryMetricsSnapshot(
                timestamp=current_time.isoformat(),
                working_memory_count=0,
                semantic_facts_count=0,
                knowledge_graph_entities=0,
                knowledge_graph_relationships=0,
                total_conversations=0,
            ),
            growth_7d=MemoryGrowthStats(
                period_days=7,
                facts_added=0,
                entities_added=0,
                relationships_added=0,
                consolidation_sessions=0,
            ),
            growth_30d=MemoryGrowthStats(
                period_days=30,
                facts_added=0,
                entities_added=0,
                relationships_added=0,
                consolidation_sessions=0,
            ),
            historical_snapshots=[],
            insights=[],
        )
