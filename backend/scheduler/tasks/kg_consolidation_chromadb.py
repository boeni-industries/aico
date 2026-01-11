"""
ChromaDB cleanup helper for KG consolidation task.
Separated to avoid circular imports and keep consolidation task clean.
"""

from typing import Dict
from aico.core.logging import get_logger

logger = get_logger("backend.scheduler.tasks.kg_consolidation")


async def cleanup_chromadb_historical(memory_manager) -> Dict[str, int]:
    """
    Clean up historical node and edge embeddings from ChromaDB.
    
    This ensures ChromaDB stays in sync with libSQL by removing embeddings
    for nodes/edges that have been marked as historical (is_current = 0).
    
    Args:
        memory_manager: Memory manager instance
    
    Returns:
        Dict with cleanup statistics
    """
    try:
        db = memory_manager._kg_storage.db
        node_collection = memory_manager._kg_storage._node_collection
        edge_collection = memory_manager._kg_storage._edge_collection
        
        # Query ALL historical nodes from database
        cursor = db.execute("SELECT id FROM kg_nodes WHERE is_current = 0")
        historical_node_ids = [row[0] for row in cursor.fetchall()]
        
        # Delete historical node embeddings
        nodes_deleted = 0
        if historical_node_ids:
            try:
                node_collection.delete(ids=historical_node_ids)
                nodes_deleted = len(historical_node_ids)
                logger.info(f"Deleted {nodes_deleted} historical node embeddings from ChromaDB")
            except Exception as e:
                logger.warning(f"Failed to delete ChromaDB embeddings for historical nodes: {e}")
        
        # Query ALL historical edges from database
        cursor = db.execute("SELECT id FROM kg_edges WHERE is_current = 0")
        historical_edge_ids = [row[0] for row in cursor.fetchall()]
        
        # Delete historical edge embeddings
        edges_deleted = 0
        if historical_edge_ids:
            try:
                edge_collection.delete(ids=historical_edge_ids)
                edges_deleted = len(historical_edge_ids)
                logger.info(f"Deleted {edges_deleted} historical edge embeddings from ChromaDB")
            except Exception as e:
                logger.warning(f"Failed to delete ChromaDB embeddings for historical edges: {e}")
        
        return {
            'nodes_deleted': nodes_deleted,
            'edges_deleted': edges_deleted
        }
        
    except Exception as e:
        logger.error(f"🕸️ [KG_TASK] Failed to clean up ChromaDB: {e}")
        import traceback
        traceback.print_exc()
        return {'nodes_deleted': 0, 'edges_deleted': 0}
