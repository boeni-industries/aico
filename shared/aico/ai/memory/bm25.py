"""
BM25 keyword scoring algorithm.

Pure BM25 implementation for keyword-based document ranking.
BM25 (Best Matching 25) is a probabilistic ranking function that scores
documents based on query term frequency, document length, and term rarity.

This module provides ONLY the BM25 calculation. For combining BM25 with
semantic search, see fusion.py.
"""

import math
from typing import List
from collections import Counter


def tokenize(text: str) -> List[str]:
    """Simple tokenization for BM25 with punctuation removal."""
    import re
    # Lowercase and remove punctuation, then split
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)  # Replace punctuation with spaces
    return text.split()


def calculate_bm25(
    documents: List[str],
    query_text: str,
    k1: float = 1.5,
    b: float = 0.75,
    min_idf: float = 0.6
) -> List[float]:
    """
    Calculate BM25 scores for documents with IDF-based term filtering.
    
    Pure BM25 implementation with smart filtering of common terms.
    Terms with low IDF (appearing in too many documents) are filtered
    from the query to reduce false positives from common words.
    
    Mathematical formula:
        score(D,Q) = Σ IDF(qi) × (f(qi,D) × (k1 + 1)) / (f(qi,D) + k1 × (1 - b + b × |D|/avgdl))
    
    Where:
        - D = document
        - Q = query (filtered by min_idf)
        - qi = query term i
        - f(qi,D) = frequency of qi in D
        - |D| = length of D
        - avgdl = average document length
        - IDF(qi) = log((N - n(qi) + 0.5) / (n(qi) + 0.5) + 1)
        - N = total number of documents
        - n(qi) = number of documents containing qi
    
    IDF Filtering:
        - Terms with IDF < min_idf are excluded from query
        - Filters common words that appear in many documents
        - Language-agnostic, adapts to corpus
        - Example: "today" (IDF≈0.26) filtered, "Schaffhausen" (IDF≈2.38) kept
    
    Args:
        documents: List of document text strings
        query_text: Search query string
        k1: Term frequency saturation parameter (default 1.5)
            Higher values give more weight to term frequency
        b: Length normalization parameter (default 0.75)
            0 = no normalization, 1 = full normalization
        min_idf: Minimum IDF threshold for query terms (default 0.5)
            Terms with IDF below this are filtered out
            0 = no filtering, higher = more aggressive filtering
        
    Returns:
        List of BM25 scores (one per document), same order as input
    """
    if not documents:
        return []
    
    # Calculate document stats
    doc_count = len(documents)
    total_length = 0
    term_doc_count = Counter()
    
    for doc_text in documents:
        terms = tokenize(doc_text)
        total_length += len(terms)
        unique_terms = set(terms)
        for term in unique_terms:
            term_doc_count[term] += 1
    
    avg_doc_length = total_length / doc_count if doc_count > 0 else 0
    
    # Filter query terms by IDF threshold
    raw_query_terms = tokenize(query_text)
    filtered_query_terms = []
    
    for term in raw_query_terms:
        doc_freq = term_doc_count.get(term, 0)
        
        # Calculate IDF for this term
        if doc_freq == 0:
            # Term not in corpus - keep it (might be important rare term)
            filtered_query_terms.append(term)
            continue
        
        idf = math.log((doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
        
        # Filter out low-IDF terms (too common)
        if idf >= min_idf:
            filtered_query_terms.append(term)
    
    # Use filtered query terms for BM25 calculation
    query_terms = filtered_query_terms
    
    # Calculate BM25 score for each document
    scores = []
    for doc_text in documents:
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
        
        scores.append(bm25_score)
    
    return scores
