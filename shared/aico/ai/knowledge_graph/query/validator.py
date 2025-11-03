"""
Query validation and security checks for GQL/Cypher queries.

Ensures queries are safe to execute and don't violate security constraints.
"""

import re
from typing import Optional


class QueryValidator:
    """Validates GQL/Cypher queries for security and correctness."""
    
    # Dangerous patterns that could cause security issues
    FORBIDDEN_PATTERNS = [
        r'\bUNION\b',  # Prevent union-based injection
        r'\bDROP\b',   # Prevent schema modification
        r'\bCREATE\s+INDEX\b',  # Prevent index creation
        r'\bALTER\b',  # Prevent schema alteration
    ]
    
    # Maximum query length to prevent DoS
    MAX_QUERY_LENGTH = 10000
    
    def __init__(self, max_results: int = 1000, timeout_seconds: int = 30):
        """
        Initialize validator with execution limits.
        
        Args:
            max_results: Maximum number of results to return
            timeout_seconds: Maximum query execution time
        """
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds
    
    def validate(self, query: str) -> tuple[bool, Optional[str]]:
        """
        Validate a GQL/Cypher query.
        
        Args:
            query: The query string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is None
        """
        # Check query length
        if len(query) > self.MAX_QUERY_LENGTH:
            return False, f"Query too long (max {self.MAX_QUERY_LENGTH} characters)"
        
        # Check for empty query
        if not query.strip():
            return False, "Query cannot be empty"
        
        # Check for forbidden patterns
        query_upper = query.upper()
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                return False, f"Forbidden pattern detected: {pattern}"
        
        # Basic syntax check - must contain MATCH or RETURN
        if not (re.search(r'\bMATCH\b', query_upper) or 
                re.search(r'\bRETURN\b', query_upper)):
            return False, "Query must contain MATCH or RETURN clause"
        
        return True, None
    
    def add_limit(self, query: str) -> str:
        """
        Add LIMIT clause to query if not present.
        
        Args:
            query: The query string
            
        Returns:
            Query with LIMIT clause added
        """
        query_upper = query.upper()
        
        # Check if LIMIT already exists
        if re.search(r'\bLIMIT\s+\d+', query_upper):
            return query
        
        # Add LIMIT to end of query
        return f"{query.rstrip()} LIMIT {self.max_results}"
