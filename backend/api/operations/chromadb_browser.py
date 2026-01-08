"""
ChromaDB Browser Functions

Provides semantic search and browsing capabilities for ChromaDB vector database.
"""

from typing import Optional
from fastapi import HTTPException, status, Request
from aico.core.logging import get_logger
from backend.api.operations.schemas import (
    ChromaDBSearchRequest, ChromaDBSearchResponse, ChromaDBDocument,
    ChromaDBDeleteRequest, ChromaDBDeleteResponse,
    ChromaDBBrowseDocument, ChromaDBBrowseResponse,
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


async def delete_chromadb_documents(delete_request: ChromaDBDeleteRequest, request: Request) -> ChromaDBDeleteResponse:
    """
    Delete documents from ChromaDB collection.
    
    Args:
        delete_request: Delete request with collection name and document IDs
        request: FastAPI request object for service container access
        
    Returns:
        ChromaDBDeleteResponse with deletion status
    """
    try:
        logger.info(f"ChromaDB delete request: collection='{delete_request.collection_name}', {len(delete_request.document_ids)} documents")
        
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
        
        if not semantic_store._initialized:
            await semantic_store.initialize()
        
        # Get the collection
        collection = semantic_store._collection
        
        # Delete documents
        collection.delete(ids=delete_request.document_ids)
        
        logger.info(f"Successfully deleted {len(delete_request.document_ids)} documents from {delete_request.collection_name}")
        
        return ChromaDBDeleteResponse(
            collection_name=delete_request.collection_name,
            deleted_count=len(delete_request.document_ids),
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete ChromaDB documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete documents: {str(e)}"
        )


async def browse_chromadb_collection(collection_name: str, request: Request, limit: int = 100) -> ChromaDBBrowseResponse:
    """
    Browse all documents in a ChromaDB collection.
    
    Args:
        collection_name: Name of the collection to browse
        request: FastAPI request object for service container access
        limit: Maximum number of documents to return
        
    Returns:
        ChromaDBBrowseResponse with documents
    """
    try:
        logger.info(f"ChromaDB browse request: collection='{collection_name}', limit={limit}")
        
        # Get memory manager from AI registry
        from aico.ai import ai_registry
        memory_manager = ai_registry.get("memory")
        
        if not memory_manager:
            logger.error("Memory manager not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory manager not available"
            )
        
        # Get ChromaDB client from semantic store (reuse existing client to avoid settings conflict)
        semantic_store = memory_manager._semantic_store
        if not semantic_store._initialized:
            await semantic_store.initialize()
        
        chroma_client = semantic_store._chroma_client
        
        # Get collection
        try:
            collection = chroma_client.get_collection(name=collection_name)
        except Exception as e:
            logger.error(f"Collection '{collection_name}' not found: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found"
            )
        
        # Get all documents (peek returns a sample, get returns all)
        count = collection.count()
        if count == 0:
            return ChromaDBBrowseResponse(
                collection_name=collection_name,
                documents=[],
                total_count=0
            )
        
        # Get documents with limit
        results = collection.get(limit=min(limit, count))
        
        # Convert to response format
        documents = []
        for i in range(len(results['ids'])):
            documents.append(ChromaDBBrowseDocument(
                id=results['ids'][i],
                document=results['documents'][i] if results['documents'] else '',
                metadata=results['metadatas'][i] if results['metadatas'] else {}
            ))
        
        logger.info(f"ChromaDB browse: '{collection_name}', returned {len(documents)} documents")
        
        return ChromaDBBrowseResponse(
            collection_name=collection_name,
            documents=documents,
            total_count=count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to browse ChromaDB collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to browse collection: {str(e)}"
        )
