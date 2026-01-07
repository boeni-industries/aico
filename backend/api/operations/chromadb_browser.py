"""
ChromaDB Browser Functions

Provides semantic search and browsing capabilities for ChromaDB vector database.
"""

from typing import Optional
from fastapi import HTTPException, status, Request
from aico.core.logging import get_logger
from backend.api.operations.schemas import (
    ChromaDBSearchRequest, ChromaDBSearchResponse, ChromaDBDocument,
)

logger = get_logger("backend", "api.operations.chromadb_browser")


async def search_chromadb(search_request: ChromaDBSearchRequest, request: Request) -> ChromaDBSearchResponse:
    """
    Search ChromaDB using semantic similarity.
    
    Args:
        search_request: Search request with query and filters
        request: FastAPI request object for service container access
        
    Returns:
        ChromaDBSearchResponse with matching documents
    """
    try:
        logger.info(f"ChromaDB search request: query='{search_request.query_text}', collection='{search_request.collection_name}', limit={search_request.limit}, min_similarity={search_request.min_similarity}")
        
        # Get memory manager from AI registry
        from aico.ai import ai_registry
        memory_manager = ai_registry.get("memory")
        
        if not memory_manager or not hasattr(memory_manager, '_semantic_store'):
            logger.error("Memory manager or semantic store not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Semantic memory not available"
            )
        
        semantic_store = memory_manager._semantic_store
        logger.info(f"Semantic store initialized: {semantic_store._initialized}")
        
        if not semantic_store._initialized:
            logger.info("Initializing semantic store...")
            await semantic_store.initialize()
        
        # Check if modelservice is available
        if not semantic_store._modelservice:
            logger.error("ModelService not available in semantic store")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ModelService not available for embeddings"
            )
        
        logger.info(f"ModelService available: {semantic_store._modelservice is not None}")
        
        # Build filter for ChromaDB query
        where_filter = {}
        if search_request.user_id:
            where_filter['user_id'] = search_request.user_id
        if search_request.conversation_id:
            where_filter['conversation_id'] = search_request.conversation_id
        
        logger.info(f"Calling query_segments with filters: {where_filter}")
        
        # Perform semantic search
        results = await semantic_store.query_segments(
            query_text=search_request.query_text,
            user_id=search_request.user_id,
            max_results=search_request.limit,
            min_similarity=search_request.min_similarity
        )
        
        logger.info(f"query_segments returned {len(results)} results")
        
        # Convert to response format
        documents = []
        for i, result in enumerate(results):
            # Calculate similarity from distance (ChromaDB uses cosine distance)
            # Cosine similarity = 1 - cosine distance
            similarity = 1.0 - result.get('distance', 0.0)
            
            role = result['metadata'].get('role', 'unknown')
            if i < 3:  # Log first 3 results
                logger.info(f"Result {i+1}: role={role}, score={result.get('hybrid_score', similarity):.3f}, content_preview={result['content'][:50]}...")
            
            documents.append(ChromaDBDocument(
                id=result['segment_id'],
                content=result['content'],
                metadata=result['metadata'],
                similarity_score=result.get('hybrid_score', similarity),
                distance=result.get('distance', 0.0)
            ))
        
        logger.info(f"ChromaDB search: '{search_request.query_text}', found {len(documents)} results")
        
        return ChromaDBSearchResponse(
            collection_name=search_request.collection_name,
            documents=documents,
            total_count=len(documents)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search ChromaDB: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search ChromaDB: {str(e)}"
        )
