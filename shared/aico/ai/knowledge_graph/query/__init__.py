"""
GQL/Cypher query execution for knowledge graph.

This module provides GQL/Cypher query support via GrandCypher, allowing users
to query their knowledge graph using ISO standard graph query language syntax.

Public API:
    - GQLQueryExecutor: Execute GQL/Cypher queries against KG storage
"""

from .executor import GQLQueryExecutor

__all__ = ["GQLQueryExecutor"]
