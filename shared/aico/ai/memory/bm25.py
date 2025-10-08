"""
BM25 scoring for hybrid search.

Pure functions for BM25 calculation - no async, no state, easy to test.
Used by both SemanticMemoryStore and CLI tools.
"""

import math
from typing import List, Dict, Any
from collections import Counter


def tokenize(text: str) -> List[str]:
    """Simple tokenization for BM25."""
    return text.lower().split()


def calculate_bm25_scores(
    documents: List[Dict[str, Any]],
    query_text: str,
    semantic_weight: float = 0.7,
    bm25_weight: float = 0.3,
    k1: float = 1.5,
    b: float = 0.75
) -> List[Dict[str, Any]]:
    """
    Calculate hybrid scores (BM25 + semantic) for documents.
    
    Args:
        documents: List of dicts with 'id', 'document', 'distance' keys
        query_text: Search query
        semantic_weight: Weight for semantic similarity (0-1)
        bm25_weight: Weight for BM25 score (0-1)
        k1: BM25 term frequency saturation parameter
        b: BM25 length normalization parameter
        
    Returns:
        List of documents with added score fields:
        - semantic_score: Cosine similarity (0-1)
        - bm25_score: Raw BM25 score
        - bm25_normalized: BM25 normalized to 0-1
        - hybrid_score: Combined score
    """
    if not documents:
        return []
    
    # Calculate document stats for BM25
    doc_count = len(documents)
    total_length = 0
    term_doc_count = Counter()
    doc_lengths = {}
    
    for doc in documents:
        doc_id = doc.get('id', '')
        doc_text = doc.get('document', '')
        terms = tokenize(doc_text)
        
        doc_lengths[doc_id] = len(terms)
        total_length += len(terms)
        
        # Count unique terms per document for IDF
        unique_terms = set(terms)
        for term in unique_terms:
            term_doc_count[term] += 1
    
    avg_doc_length = total_length / doc_count if doc_count > 0 else 0
    query_terms = tokenize(query_text)
    
    # First pass: Calculate raw BM25 scores
    raw_scores = []
    for doc in documents:
        doc_id = doc.get('id', '')
        doc_text = doc.get('document', '')
        distance = doc.get('distance', 0.0)
        
        # Semantic similarity (cosine distance to similarity)
        semantic_sim = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
        
        # BM25 score
        doc_terms = tokenize(doc_text)
        doc_length = len(doc_terms)
        term_freqs = Counter(doc_terms)
        
        bm25_score = 0.0
        for term in query_terms:
            if term not in term_freqs:
                continue
            
            tf = term_freqs[term]
            doc_freq = term_doc_count.get(term, 1)
            
            # IDF calculation
            idf = math.log((doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
            
            # BM25 formula
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_length / avg_doc_length))
            bm25_score += idf * (numerator / denominator)
        
        raw_scores.append({
            'id': doc_id,
            'document': doc_text,
            'distance': distance,
            'semantic_score': semantic_sim,
            'bm25_score': bm25_score,
            'metadata': doc.get('metadata', {})
        })
    
    # Min-max normalization for BM25 scores
    bm25_scores = [doc['bm25_score'] for doc in raw_scores]
    min_bm25 = min(bm25_scores) if bm25_scores else 0.0
    max_bm25 = max(bm25_scores) if bm25_scores else 1.0
    bm25_range = max_bm25 - min_bm25
    
    # Second pass: Normalize and calculate hybrid scores
    scored_documents = []
    for doc in raw_scores:
        # Min-max normalization: (score - min) / (max - min)
        if bm25_range > 0:
            bm25_normalized = (doc['bm25_score'] - min_bm25) / bm25_range
        else:
            bm25_normalized = 0.0
        
        # Hybrid score with normalized values
        hybrid_score = (semantic_weight * doc['semantic_score'] + 
                       bm25_weight * bm25_normalized)
        
        scored_documents.append({
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
    scored_documents.sort(key=lambda x: x['hybrid_score'], reverse=True)
    
    return scored_documents
