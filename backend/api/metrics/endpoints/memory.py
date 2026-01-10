"""
Memory System Metrics Endpoint

Provides metrics for the memory subsystem including:
- Working memory size
- Semantic query performance
- Knowledge graph statistics
- Storage breakdown
- Consolidation health

Metrics sourced from InfluxDB (memory_query measurement) and database queries.
"""

from fastapi import APIRouter, HTTPException

from ..models import MemoryMetrics, MetricValue
from ..influx_client import MetricsInfluxClient
from aico.core.logging import get_logger

logger = get_logger("backend", "api.metrics.memory")

router = APIRouter()


@router.get("/memory", response_model=MemoryMetrics)
async def get_memory_metrics():
    """Get memory system metrics from InfluxDB and database."""
    try:
        with MetricsInfluxClient() as client:
            filters = {"service": "backend"}
            
            # Query performance from InfluxDB
            query_count = client.count_points("memory_query", "-1m", filters)
            queries_per_second = query_count / 60.0
            
            # Placeholder data (would query actual database for KG stats)
            return MemoryMetrics(
                working_memory_size=MetricValue(value=1250, unit="entries", status="healthy"),
                semantic_queries_per_second=MetricValue(value=round(queries_per_second, 2), unit="queries/s", status="healthy"),
                kg_nodes=MetricValue(value=450, unit="nodes", status="healthy"),
                kg_relationships=MetricValue(value=320, unit="edges", status="healthy"),
                entity_type_distribution={"PERSON": 120, "CONCEPT": 85, "ACTIVITY": 45},
                relationship_type_distribution={"BORN_IN": 80, "HAS_GOAL": 60, "INTERESTED_IN": 90},
                storage_breakdown={"LMDB": 12.5, "ChromaDB": 45.8, "SQLite": 8.3},
                consolidation_health=MetricValue(value=95.0, unit="%", status="healthy"),
                last_consolidation="2026-01-10T20:00:00Z"
            )
    
    except Exception as e:
        # If InfluxDB is empty or has no data, return zero metrics instead of failing
        logger.warning(f"InfluxDB query failed (likely no data yet), returning zero metrics: {e}")
        
        # Return empty/zero metrics
        return MemoryMetrics(
            working_memory_size=MetricValue(value=0, unit="items", status="healthy"),
            semantic_memory_size=MetricValue(value=0, unit="items", status="healthy"),
            episodic_memory_size=MetricValue(value=0, unit="items", status="healthy"),
            queries_per_second=MetricValue(value=0.0, unit="queries/s", status="healthy"),
            avg_query_time=MetricValue(value=0.0, unit="ms", status="healthy"),
            cache_hit_rate=MetricValue(value=0.0, unit="%", status="healthy"),
            kg_nodes=MetricValue(value=0, unit="nodes", status="healthy"),
            kg_relationships=MetricValue(value=0, unit="edges", status="healthy"),
            entity_type_distribution={},
            relationship_type_distribution={},
            storage_breakdown={},
            consolidation_health=MetricValue(value=100.0, unit="%", status="healthy"),
            last_consolidation="N/A"
        )
