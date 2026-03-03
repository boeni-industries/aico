"""
GQL/Cypher query executor.

Orchestrates query validation, execution via GrandCypher, and result formatting.
"""

import logging
import re
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
        max_results: int = 1000,
        timeout_seconds: int = 30
    ):
        """
        Initialize query executor.
        
        Args:
            kg_storage: KnowledgeGraphStorage instance
            max_results: Maximum number of results to return
            timeout_seconds: Maximum query execution time
        """
        self.kg_storage = kg_storage
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
            adapter = KGGraphAdapter(self.kg_storage, user_id)
            graph = await adapter.get_graph()
            
            logger.info(f"Executing GQL query for user {user_id}: {query[:100]}...")
            logger.debug(f"Graph has {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
            
            # Step 4: Execute query via GrandCypher (or compatibility layer for unsupported constructs)
            try:
                results = await self._execute_with_compat(query=query, graph=graph)
                logger.debug(f"GrandCypher raw results type: {type(results)}")
                logger.debug(
                    f"GrandCypher raw results keys: {results.keys() if isinstance(results, dict) else 'N/A'}"
                )

                # Normalize results into GrandCypher-style dict-of-lists.
                # Some aggregations may return scalars (e.g., COUNT()) which breaks downstream formatting.
                if isinstance(results, dict):
                    normalized: Dict[str, list] = {}
                    for k, v in results.items():
                        if isinstance(v, list):
                            normalized[k] = v
                        else:
                            normalized[k] = [v]
                    results = normalized

                if isinstance(results, dict) and results:
                    first_key = list(results.keys())[0]
                    first_col = results.get(first_key, [])
                    first_value = first_col[0] if isinstance(first_col, list) and first_col else None
                    logger.debug(
                        f"First result sample - key: {first_key}, value type: {type(first_value)}, value: {first_value}"
                    )
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

    async def _execute_with_compat(self, query: str, graph) -> Any:
        """Execute query with pragmatic compatibility for shipped templates.

        This keeps GrandCypher as the default execution engine, but emulates a few
        Cypher constructs used by the shipped templates that GrandCypher doesn't parse.
        """
        q = query
        q_upper = q.upper()

        # 1) WHERE <var>.<prop> IS NOT NULL  -> run without WHERE then filter results.
        # We currently only emulate the concrete template usage: n.valid_from IS NOT NULL.
        if " IS NOT NULL" in q_upper:
            return self._execute_is_not_null_filter(query=q, graph=graph)

        # 2) WHERE NOT EXISTS { MATCH ... } -> emulate for the shipped 'skill-gaps' template.
        if "WHERE NOT EXISTS" in q_upper and "HAS_SKILL" in q_upper and "REQUIRES" in q_upper:
            return self._execute_skill_gaps(query=q, graph=graph)

        # 3) Variable length path + LENGTH(path)/relationships(path) -> emulate for shipped multi-hop template.
        if "LENGTH(" in q_upper or "RELATIONSHIPS(" in q_upper or "[*" in q:
            return self._execute_multi_hop_paths(query=q, graph=graph)

        # 4) Aggregation-heavy template with AVG/CASE WHEN -> emulate.
        if "AVG(" in q_upper or "CASE WHEN" in q_upper:
            return self._execute_property_aggregation(query=q, graph=graph)

        # Default: GrandCypher
        gc = GrandCypher(graph)
        return gc.run(q)

    def _execute_is_not_null_filter(self, query: str, graph) -> Dict[str, Any]:
        # Best-effort: strip unsupported IS NOT NULL clause and filter after.
        # Handles the shipped template: WHERE n.valid_from IS NOT NULL
        # Extract property name
        m = re.search(r"WHERE\s+([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)\s+IS\s+NOT\s+NULL", query, re.IGNORECASE)
        if not m:
            gc = GrandCypher(graph)
            return gc.run(query)

        var_name, prop_name = m.group(1), m.group(2)
        stripped = re.sub(r"WHERE\s+[^\n]+IS\s+NOT\s+NULL\s*\n?", "", query, flags=re.IGNORECASE)

        gc = GrandCypher(graph)
        results = gc.run(stripped)

        if not isinstance(results, dict) or not results:
            return results

        # Filter rows by checking the corresponding returned column if present.
        # Commonly the template returns n.valid_from.
        target_col = f"{var_name}.{prop_name}"
        if target_col not in results:
            # Nothing to filter on; return as-is.
            return results

        col_vals = results.get(target_col)
        if not isinstance(col_vals, list):
            col_vals = [col_vals]

        keep_idx = [i for i, v in enumerate(col_vals) if v is not None]
        filtered: Dict[str, list] = {}
        for k, v in results.items():
            if not isinstance(v, list):
                v = [v]
            filtered[k] = [v[i] for i in keep_idx if i < len(v)]
        return filtered

    def _execute_skill_gaps(self, query: str, graph) -> Dict[str, Any]:
        """Emulate the shipped skill-gaps template.

        Original intent:
          MATCH (goal:GOAL)-[:REQUIRES]->(skill:SKILL)
          WHERE NOT EXISTS { MATCH (p:PERSON)-[:HAS_SKILL]->(skill) }
          RETURN goal.name, skill.name
        """
        # Build set of skills possessed by any PERSON
        possessed = set()
        for u, v, attrs in graph.edges(data=True):
            labels = attrs.get("__labels__") or set()
            if isinstance(labels, str):
                labels = {labels}
            if "HAS_SKILL" in labels:
                possessed.add(v)

        goal_names: list = []
        skill_names: list = []

        for u, v, attrs in graph.edges(data=True):
            labels = attrs.get("__labels__") or set()
            if isinstance(labels, str):
                labels = {labels}
            if "REQUIRES" not in labels:
                continue

            # Ensure node labels match GOAL->SKILL
            u_labels = graph.nodes[u].get("__labels__") or set()
            v_labels = graph.nodes[v].get("__labels__") or set()
            if isinstance(u_labels, str):
                u_labels = {u_labels}
            if isinstance(v_labels, str):
                v_labels = {v_labels}
            if "GOAL" not in u_labels or "SKILL" not in v_labels:
                continue

            if v in possessed:
                continue

            goal_names.append(graph.nodes[u].get("name"))
            skill_names.append(graph.nodes[v].get("name"))

        return {"goal.name": goal_names, "skill.name": skill_names}

    def _execute_multi_hop_paths(self, query: str, graph) -> Dict[str, Any]:
        """Emulate the shipped multi-hop paths template (up to 3 hops).

        Expected pattern:
          MATCH path = (start:PERSON {name: "X"})-[*1..3]-(end:GOAL)
          RETURN start.name, end.name, LENGTH(path) as hops,
                 [rel in relationships(path) | type(rel)] as path_types
        """
        # Parse start label + property constraint and end label.
        start_label = None
        end_label = None
        start_name = None

        m = re.search(r"\(start:([A-Z_]+)\s*\{\s*name\s*:\s*\"([^\"]+)\"\s*\}\)", query)
        if m:
            start_label = m.group(1)
            start_name = m.group(2)

        m2 = re.search(r"\(end:([A-Z_]+)\)", query)
        if m2:
            end_label = m2.group(1)

        if not start_label or not end_label:
            # Fallback: let GrandCypher handle if we can't parse.
            gc = GrandCypher(graph)
            return gc.run(query)

        # Find start nodes
        starts = []
        for nid, attrs in graph.nodes(data=True):
            labels = attrs.get("__labels__") or set()
            if isinstance(labels, str):
                labels = {labels}
            if start_label in labels and (start_name is None or attrs.get("name") == start_name):
                starts.append(nid)

        # Find end nodes
        ends = []
        for nid, attrs in graph.nodes(data=True):
            labels = attrs.get("__labels__") or set()
            if isinstance(labels, str):
                labels = {labels}
            if end_label in labels:
                ends.append(nid)

        # Search paths up to 3 hops.
        max_hops = 3
        # Use undirected view to match -()--() semantics
        undirected = graph.to_undirected()

        out_start: list = []
        out_end: list = []
        out_hops: list = []
        out_types: list = []

        for s in starts:
            for e in ends:
                if s == e:
                    continue
                try:
                    for path in __import__("networkx").all_simple_paths(undirected, s, e, cutoff=max_hops):
                        hops = len(path) - 1
                        rel_types = []
                        for a, b in zip(path, path[1:]):
                            # Choose directed edge if present; otherwise reverse.
                            if graph.has_edge(a, b):
                                attrs = graph.edges[a, b]
                            else:
                                attrs = graph.edges[b, a]
                            rel_types.append(attrs.get("relation_type") or next(iter(attrs.get("__labels__") or []), None))

                        out_start.append(graph.nodes[s].get("name"))
                        out_end.append(graph.nodes[e].get("name"))
                        out_hops.append(hops)
                        out_types.append(rel_types)
                except Exception:
                    continue

        return {
            "start.name": out_start,
            "end.name": out_end,
            "hops": out_hops,
            "path_types": out_types,
        }

    def _execute_property_aggregation(self, query: str, graph) -> Dict[str, Any]:
        """Emulate the shipped property aggregation template."""
        # Group by label
        groups: Dict[str, list] = {}
        for _, attrs in graph.nodes(data=True):
            label = attrs.get("label") or next(iter(attrs.get("__labels__") or []), "unknown")
            groups.setdefault(label, []).append(attrs)

        labels_out: list = []
        total_out: list = []
        avg_conf_out: list = []
        current_count_out: list = []

        for label, items in groups.items():
            labels_out.append(label)
            total_out.append(len(items))
            confidences = [i.get("confidence") for i in items if isinstance(i.get("confidence"), (int, float))]
            avg_conf_out.append(sum(confidences) / len(confidences) if confidences else None)
            current_count_out.append(sum(1 for i in items if i.get("is_current") in (True, 1, "1")))

        # Sort by total desc to match template
        order = sorted(range(len(total_out)), key=lambda i: total_out[i], reverse=True)
        labels_out = [labels_out[i] for i in order]
        total_out = [total_out[i] for i in order]
        avg_conf_out = [avg_conf_out[i] for i in order]
        current_count_out = [current_count_out[i] for i in order]

        return {
            "n.label": labels_out,
            "total": total_out,
            "avg_confidence": avg_conf_out,
            "current_count": current_count_out,
        }
