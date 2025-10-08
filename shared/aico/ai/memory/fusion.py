"""
Hybrid search fusion methods.

Pure functions for combining BM25 and semantic search results.
No async, no state, easy to test.

Architecture:
1. Calculate semantic scores (from vector search)
2. Calculate BM25 scores (from keyword search)
3. Fuse scores using RRF or weighted combination

Fusion Methods:
- RRF (Reciprocal Rank Fusion): Rank-based, resistant to outliers, industry standard
- Weighted: Score-based with min-max normalization (legacy)
"""

from typing import List, Dict, Any
from .bm25 import calculate_bm25


def calculate_scores(
    documents: List[Dict[str, Any]],
    query_text: str,
    k1: float = 1.5,
    b: float = 0.75,
    min_idf: float = 0.6
) -> List[Dict[str, Any]]:
    """
    Calculate both semantic and BM25 scores for documents.
    
    This is the scoring step - calculates all scores before fusion.
    
    Args:
        documents: List of dicts with 'id', 'document', 'distance' keys
        query_text: Search query
        k1: BM25 term frequency saturation parameter
        b: BM25 length normalization parameter
        min_idf: Minimum IDF threshold for BM25 query term filtering
        
    Returns:
        List of documents with semantic_score and bm25_score added
    """
    if not documents:
        return []
    
    # Extract document texts for BM25
    doc_texts = [doc.get('document', '') for doc in documents]
    
    # Calculate BM25 scores using pure BM25 module with IDF filtering
    bm25_scores = calculate_bm25(doc_texts, query_text, k1, b, min_idf)
    
    # Combine with semantic scores
    scored_docs = []
    for i, doc in enumerate(documents):
        doc_id = doc.get('id', '')
        doc_text = doc.get('document', '')
        distance = doc.get('distance', 0.0)
        
        # Semantic similarity (cosine distance to similarity)
        semantic_sim = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
        
        scored_docs.append({
            'id': doc_id,
            'document': doc_text,
            'distance': distance,
            'semantic_score': semantic_sim,
            'bm25_score': bm25_scores[i],
            'metadata': doc.get('metadata', {})
        })
    
    return scored_docs


def fuse_with_rrf(
    scored_documents: List[Dict[str, Any]],
    k: int = None,
    min_semantic_score: float = 0.35
) -> List[Dict[str, Any]]:
    """
    Fuse semantic and BM25 scores using Reciprocal Rank Fusion (RRF).
    
    RRF combines scores by rank position, not raw values.
    This makes it resistant to outliers and score distribution differences.
    
    Mathematical proof:
    - RRF formula: score(doc) = Σ[1/(k + rank_i)] for each query method
    - k = rank constant (adaptive based on dataset size if not specified)
    - rank_i = position of document in query method i (1-indexed)
    
    Properties:
    - Bounded output: max = 2/(k+1), min → 0
    - Scale-invariant: works regardless of input score ranges
    - Consensus-based: favors documents ranking high in multiple methods
    - Monotonic: better ranks always produce higher scores
    
    Adaptive k selection:
    - Small datasets (<50 docs): k = N/2 (more discriminative)
    - Medium datasets (50-500): k = 30-60 (balanced)
    - Large datasets (>500): k = 60 (industry standard)
    
    Relevance Filtering:
    - Documents with semantic_score < min_semantic_score are filtered out
    - This prevents irrelevant documents from appearing in results
    - Default threshold: 0.35 (documents must have some semantic relevance)
    
    Args:
        scored_documents: List of dicts with 'semantic_score' and 'bm25_score'
        k: Rank constant (if None, automatically determined from dataset size)
           Larger k = more uniform scores, smaller k = more top-heavy
        min_semantic_score: Minimum semantic score threshold (default: 0.35)
           Documents below this threshold are filtered out as irrelevant
        
    Returns:
        List of documents with added fields:
        - bm25_normalized: BM25 normalized to 0-1 (for display)
        - semantic_rank: Rank in semantic results (1-indexed)
        - bm25_rank: Rank in BM25 results (1-indexed)
        - rrf_score: Combined RRF score
        - rrf_k: The k value used (for debugging)
        - hybrid_score: Alias for rrf_score (for consistency)
    """
    if not scored_documents:
        return []
    
    # Filter out documents with low semantic scores (irrelevant results)
    scored_documents = [
        doc for doc in scored_documents 
        if doc['semantic_score'] >= min_semantic_score
    ]
    
    if not scored_documents:
        return []
    
    # Adaptive k based on dataset size
    if k is None:
        n = len(scored_documents)
        if n < 50:
            # Small dataset: use N/2 for better discrimination
            k = max(10, n // 2)
        elif n < 500:
            # Medium dataset: scale between 30-60
            k = min(60, 30 + (n - 50) // 15)
        else:
            # Large dataset: use industry standard
            k = 60
    
    # Rank by semantic score (higher is better)
    semantic_sorted = sorted(scored_documents, key=lambda x: x['semantic_score'], reverse=True)
    semantic_ranks = {doc['id']: rank + 1 for rank, doc in enumerate(semantic_sorted)}
    
    # Rank by BM25 score (higher is better)
    bm25_sorted = sorted(scored_documents, key=lambda x: x['bm25_score'], reverse=True)
    bm25_ranks = {doc['id']: rank + 1 for rank, doc in enumerate(bm25_sorted)}
    
    # Calculate RRF scores
    fused_documents = []
    for doc in scored_documents:
        doc_id = doc['id']
        semantic_rank = semantic_ranks[doc_id]
        bm25_rank = bm25_ranks[doc_id]
        
        # RRF formula: sum of reciprocal ranks
        # Mathematical proof: 1/(k+rank) decreases monotonically as rank increases
        # This ensures higher-ranked documents always contribute more to the final score
        rrf_score = (1.0 / (k + semantic_rank)) + (1.0 / (k + bm25_rank))
        
        # For display: calculate normalized BM25
        bm25_scores = [d['bm25_score'] for d in scored_documents]
        min_bm25 = min(bm25_scores) if bm25_scores else 0.0
        max_bm25 = max(bm25_scores) if bm25_scores else 1.0
        bm25_range = max_bm25 - min_bm25
        
        if bm25_range > 0:
            bm25_normalized = (doc['bm25_score'] - min_bm25) / bm25_range
        else:
            bm25_normalized = 0.0
        
        fused_documents.append({
            'id': doc_id,
            'document': doc['document'],
            'distance': doc['distance'],
            'semantic_score': doc['semantic_score'],
            'bm25_score': doc['bm25_score'],
            'bm25_normalized': bm25_normalized,
            'semantic_rank': semantic_rank,
            'bm25_rank': bm25_rank,
            'rrf_score': rrf_score,
            'rrf_k': k,  # Store k value for debugging
            'hybrid_score': rrf_score,  # Alias for consistency
            'metadata': doc['metadata']
        })
    
    # Sort by RRF score (higher is better)
    fused_documents.sort(key=lambda x: x['rrf_score'], reverse=True)
    
    return fused_documents


def fuse_with_weights(
    scored_documents: List[Dict[str, Any]],
    semantic_weight: float = 0.7,
    bm25_weight: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Fuse semantic and BM25 scores using weighted combination (legacy method).
    
    Combines normalized BM25 and semantic scores with configurable weights.
    Uses min-max normalization to bring BM25 scores to 0-1 range.
    
    Note: This method is sensitive to score distributions and outliers.
    Consider using RRF for more robust results.
    
    Args:
        scored_documents: List of dicts with 'semantic_score' and 'bm25_score'
        semantic_weight: Weight for semantic similarity (0-1)
        bm25_weight: Weight for BM25 score (0-1)
        
    Returns:
        List of documents with added fields:
        - bm25_normalized: BM25 normalized to 0-1
        - hybrid_score: Weighted combination
    """
    if not scored_documents:
        return []
    
    # Min-max normalization for BM25 scores
    bm25_scores = [doc['bm25_score'] for doc in scored_documents]
    min_bm25 = min(bm25_scores) if bm25_scores else 0.0
    max_bm25 = max(bm25_scores) if bm25_scores else 1.0
    bm25_range = max_bm25 - min_bm25
    
    # Calculate weighted scores
    fused_documents = []
    for doc in scored_documents:
        # Normalize BM25
        if bm25_range > 0:
            bm25_normalized = (doc['bm25_score'] - min_bm25) / bm25_range
        else:
            bm25_normalized = 0.0
        
        # Weighted combination
        hybrid_score = (semantic_weight * doc['semantic_score'] + 
                       bm25_weight * bm25_normalized)
        
        fused_documents.append({
            'id': doc['id'],
            'document': doc['document'],
            'distance': doc['distance'],
            'semantic_score': doc['semantic_score'],
            'bm25_score': doc['bm25_score'],
            'bm25_normalized': bm25_normalized,
            'hybrid_score': hybrid_score,
            'metadata': doc['metadata']
        })
    
    # Sort by hybrid score
    fused_documents.sort(key=lambda x: x['hybrid_score'], reverse=True)
    
    return fused_documents


# Convenience wrappers for backward compatibility
def calculate_rrf_scores(
    documents: List[Dict[str, Any]], 
    query_text: str, 
    k: int = None, 
    min_idf: float = 0.6,
    min_semantic_score: float = 0.35
) -> List[Dict[str, Any]]:
    """Score + Fuse with RRF (convenience wrapper).
    
    Args:
        documents: List of dicts with 'id', 'document', 'distance'
        query_text: Search query
        k: Rank constant (None = adaptive based on dataset size)
        min_idf: Minimum IDF threshold for BM25 term filtering
        min_semantic_score: Minimum semantic score threshold (default: 0.35)
        min_idf: Minimum IDF threshold for BM25 term filtering
    """
    scored = calculate_scores(documents, query_text, min_idf=min_idf)
    return fuse_with_rrf(scored, k, min_semantic_score)


def calculate_weighted_scores(documents: List[Dict[str, Any]], query_text: str, 
                              semantic_weight: float = 0.7, bm25_weight: float = 0.3, min_idf: float = 0.6) -> List[Dict[str, Any]]:
    """Score + Fuse with weights (convenience wrapper)."""
    scored = calculate_scores(documents, query_text, min_idf=min_idf)
    return fuse_with_weights(scored, semantic_weight, bm25_weight)
