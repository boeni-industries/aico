"""
AMS Router Extensions

Additional helper functions for skill overview and memory evolution tracking.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any
from aico.core.logging import get_logger

from .schemas import (
    SkillDetailResponse,
    SkillOverviewResponse,
    MemoryMetricsSnapshot,
    MemoryGrowthStats,
    MemoryEvolutionResponse,
)

logger = get_logger("backend.api.ams.extensions")


def get_skill_overview(db: sqlite3.Connection, user_id: str) -> SkillOverviewResponse:
    """
    Get comprehensive overview of all available skills with usage data.
    
    Queries ams_behavioral_skills and user_skill_confidence tables to provide
    complete skill inventory with performance metrics.
    """
    try:
        # Get all available skills
        cursor = db.execute("""
            SELECT 
                s.skill_id,
                s.skill_name,
                s.skill_type,
                s.status,
                s.created_at,
                usc.confidence_score,
                usc.usage_count,
                usc.positive_count,
                usc.negative_count,
                usc.last_used_at
            FROM ams_behavioral_skills s
            LEFT JOIN user_skill_confidence usc 
                ON s.skill_id = usc.skill_id AND usc.user_id = ?
            ORDER BY 
                CASE WHEN usc.usage_count IS NULL THEN 0 ELSE 1 END DESC,
                usc.usage_count DESC,
                s.skill_name ASC
        """, (user_id,))
        
        skills = []
        active_count = 0
        
        for row in cursor.fetchall():
            # Convert confidence from 0.0-1.0 to 0-100 percentage if it exists
            confidence = (row[5] * 100) if row[5] is not None else None
            usage_count = row[6] if row[6] is not None else None
            
            if usage_count and usage_count > 0:
                active_count += 1
            
            skills.append(SkillDetailResponse(
                skill_id=row[0],
                skill_name=row[1],
                skill_type=row[2],
                status=row[3],
                confidence_score=confidence,
                usage_count=usage_count,
                positive_count=row[7],
                negative_count=row[8],
                last_used_at=row[9],
                created_at=row[4],
            ))
        
        return SkillOverviewResponse(
            total_skills=len(skills),
            active_skills=active_count,
            skills=skills,
        )
        
    except (sqlite3.OperationalError, RuntimeError, ValueError) as e:
        logger.warning(f"Skill overview query failed: {e}")
        return SkillOverviewResponse(
            total_skills=0,
            active_skills=0,
            skills=[],
        )


def get_memory_evolution(db: sqlite3.Connection, user_id: str) -> MemoryEvolutionResponse:
    """
    Get memory evolution metrics showing how memory grows over time.
    
    Tracks working memory, semantic facts, knowledge graph entities/relationships,
    and consolidation activity across different time periods.
    """
    try:
        current_time = datetime.utcnow()
        
        # Get current memory metrics
        # Working memory - stored in ams_trajectories
        cursor = db.execute("""
            SELECT COUNT(*) FROM ams_trajectories WHERE user_id = ? AND archived = 0
        """, (user_id,))
        working_memory_count = cursor.fetchone()[0] or 0
        
        # Semantic facts - stored in ams_user_memories
        cursor = db.execute("""
            SELECT COUNT(*) FROM ams_user_memories WHERE user_id = ?
        """, (user_id,))
        semantic_facts_count = cursor.fetchone()[0] or 0
        
        # Knowledge graph entities - using actual table name kg_nodes
        cursor = db.execute("""
            SELECT COUNT(*) FROM kg_nodes WHERE user_id = ?
        """, (user_id,))
        kg_entities = cursor.fetchone()[0] or 0
        
        # Knowledge graph relationships - using actual table name kg_edges
        cursor = db.execute("""
            SELECT COUNT(*) FROM kg_edges WHERE user_id = ?
        """, (user_id,))
        kg_relationships = cursor.fetchone()[0] or 0
        
        # Total conversations - using ams_trajectories
        cursor = db.execute("""
            SELECT COUNT(DISTINCT conversation_id) FROM ams_trajectories WHERE user_id = ?
        """, (user_id,))
        total_conversations = cursor.fetchone()[0] or 0
        
        current_metrics = MemoryMetricsSnapshot(
            timestamp=current_time.isoformat(),
            working_memory_count=working_memory_count,
            semantic_facts_count=semantic_facts_count,
            knowledge_graph_entities=kg_entities,
            knowledge_graph_relationships=kg_relationships,
            total_conversations=total_conversations,
        )
        
        # Calculate 7-day growth
        seven_days_ago = current_time - timedelta(days=7)
        
        cursor = db.execute("""
            SELECT COUNT(*) FROM ams_user_memories 
            WHERE user_id = ? AND created_at > ?
        """, (user_id, seven_days_ago.isoformat()))
        facts_7d = cursor.fetchone()[0] or 0
        
        cursor = db.execute("""
            SELECT COUNT(*) FROM kg_nodes 
            WHERE user_id = ? AND created_at > ?
        """, (user_id, seven_days_ago.isoformat()))
        entities_7d = cursor.fetchone()[0] or 0
        
        cursor = db.execute("""
            SELECT COUNT(*) FROM kg_edges 
            WHERE user_id = ? AND created_at > ?
        """, (user_id, seven_days_ago.isoformat()))
        relationships_7d = cursor.fetchone()[0] or 0
        
        # Consolidation sessions are stored in ams_consolidation_state as JSON
        # Cannot easily query historical session count from current schema
        consolidations_7d = 0
        
        growth_7d = MemoryGrowthStats(
            period_days=7,
            facts_added=facts_7d,
            entities_added=entities_7d,
            relationships_added=relationships_7d,
            consolidation_sessions=consolidations_7d,
        )
        
        # Calculate 30-day growth
        thirty_days_ago = current_time - timedelta(days=30)
        
        cursor = db.execute("""
            SELECT COUNT(*) FROM ams_user_memories 
            WHERE user_id = ? AND created_at > ?
        """, (user_id, thirty_days_ago.isoformat()))
        facts_30d = cursor.fetchone()[0] or 0
        
        cursor = db.execute("""
            SELECT COUNT(*) FROM kg_nodes 
            WHERE user_id = ? AND created_at > ?
        """, (user_id, thirty_days_ago.isoformat()))
        entities_30d = cursor.fetchone()[0] or 0
        
        cursor = db.execute("""
            SELECT COUNT(*) FROM kg_edges 
            WHERE user_id = ? AND created_at > ?
        """, (user_id, thirty_days_ago.isoformat()))
        relationships_30d = cursor.fetchone()[0] or 0
        
        # Consolidation sessions are stored in ams_consolidation_state as JSON
        # Cannot easily query historical session count from current schema
        consolidations_30d = 0
        
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
        
    except (sqlite3.OperationalError, RuntimeError, ValueError) as e:
        logger.warning(f"Memory evolution query failed: {e}")
        
        # Return default values
        current_time = datetime.utcnow()
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
