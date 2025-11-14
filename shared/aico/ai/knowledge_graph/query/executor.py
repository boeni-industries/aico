"""
GQL/Cypher query executor.

Orchestrates query validation, execution via GrandCypher, and result formatting.
"""

import logging
from typing import Any, Dict, Optional

from grandcypher import GrandCypher

from .adapter import KGGraphAdapter
from .formatter import ResultFormatter
from .validator import QueryValidator

logger = logging.getLogger(__name__)


class GQLQueryExecutor:
    """
    Execute GQL/Cypher queries against knowledge graph storage.
    
    This class orchestrates the entire query execution pipeline:
    1. Validate query for security and correctness
    2. Build graph adapter for user's data
    3. Execute query via GrandCypher
    4. Format results for consumption
    """
    
    def __init__(
        self,
        kg_storage,
        db_connection,
        max_results: int = 1000,
        timeout_seconds: int = 30
    ):
        """
        Initialize query executor.
        
        Args:
            kg_storage: KnowledgeGraphStorage instance
            db_connection: Database connection for queries
            max_results: Maximum number of results to return
            timeout_seconds: Maximum query execution time
        """
        self.kg_storage = kg_storage
        self.db_connection = db_connection
        self.validator = QueryValidator(max_results, timeout_seconds)
        self.formatter = ResultFormatter()
    
    async def execute(
        self,
        query: str,
        user_id: str,
        format: str = "dict"
    ) -> Dict[str, Any]:
        """
        Execute a GQL/Cypher query.
        
        Args:
            query: GQL/Cypher query string
            user_id: User ID for data isolation
            format: Output format ('dict', 'json', 'csv', 'table')
            
        Returns:
            Dictionary with:
            - success: bool
            - data: Query results (format depends on 'format' parameter)
            - error: Error message if failed
            - metadata: Execution metadata (row count, etc.)
            
        Raises:
            ValueError: If query validation fails
        """
        try:
            # Step 1: Validate query
            is_valid, error_msg = self.validator.validate(query)
            if not is_valid:
                logger.warning(f"Query validation failed for user {user_id}: {error_msg}")
                return {
                    "success": False,
                    "data": None,
                    "error": f"Invalid query: {error_msg}",
                    "metadata": {}
                }
            
            # Step 2: Add LIMIT if not present
            query = self.validator.add_limit(query)
            
            # Step 3: Build graph adapter (user-isolated)
            adapter = KGGraphAdapter(self.kg_storage, self.db_connection, user_id)
            graph = adapter.get_graph()
            
            logger.info(f"Executing GQL query for user {user_id}: {query[:100]}...")
            logger.debug(f"Graph has {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
            
            # Step 4: Execute query via GrandCypher
            try:
                gc = GrandCypher(graph)
                results = gc.run(query)
            except Exception as e:
                logger.error(f"GrandCypher execution failed: {e}")
                return {
                    "success": False,
                    "data": None,
                    "error": f"Query execution failed: {str(e)}",
                    "metadata": {}
                }
            
            # Step 5: Format results
            if format == "dict":
                formatted_data = self.formatter.to_dict(results)
            elif format == "json":
                formatted_data = self.formatter.to_json(results, pretty=True)
            elif format == "csv":
                formatted_data = self.formatter.to_csv(results)
            elif format == "table":
                formatted_data = self.formatter.to_table(results)
            else:
                formatted_data = self.formatter.to_dict(results)
            
            # Extract metadata
            result_dict = self.formatter.to_dict(results)
            metadata = {
                "row_count": result_dict["count"],
                "column_count": len(result_dict["columns"]),
                "columns": result_dict["columns"]
            }
            
            logger.info(f"Query executed successfully: {metadata['row_count']} rows returned")
            
            return {
                "success": True,
                "data": formatted_data,
                "error": None,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}", exc_info=True)
            return {
                "success": False,
                "data": None,
                "error": f"Unexpected error: {str(e)}",
                "metadata": {}
            }
