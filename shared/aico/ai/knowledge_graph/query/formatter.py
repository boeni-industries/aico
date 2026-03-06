"""
Result formatting for GQL/Cypher query results.

Converts query results to various output formats (table, JSON, CSV).
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ResultFormatter:
    """Formats query results for display."""
    
    @staticmethod
    def _make_serializable(obj: Any) -> Any:
        """
        Recursively convert non-JSON-serializable types to serializable ones.
        Flattens single-element collections to just the element.
        
        Args:
            obj: Object to convert
            
        Returns:
            JSON-serializable version of the object
        """
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, (tuple, set, list)):
            # Convert collection to list
            items = [ResultFormatter._make_serializable(item) for item in obj]
            # If single element, return just the element (flatten)
            if len(items) == 1:
                logger.debug(f"Flattening single-element collection: {obj} -> {items[0]}")
                return items[0]
            elif len(items) == 0:
                return None
            else:
                return items
        elif isinstance(obj, dict):
            # GrandCypher returns edge properties as {(edge_index, edge_type): value}
            # If dict has only tuple keys, extract the values
            if obj and all(isinstance(k, tuple) for k in obj.keys()):
                # This is a GrandCypher edge property dict - extract values
                values = list(obj.values())
                if len(values) == 1:
                    logger.debug(f"Extracting single value from tuple-keyed dict: {obj} -> {values[0]}")
                    return ResultFormatter._make_serializable(values[0])
                else:
                    # Multiple values - return as list
                    return [ResultFormatter._make_serializable(v) for v in values]
            
            # Normal dict - convert keys and values
            result = {}
            for k, v in obj.items():
                # Convert key to string
                key_str = str(k) if not isinstance(k, str) else k
                # Recursively convert value
                result[key_str] = ResultFormatter._make_serializable(v)
            return result
        else:
            # For any other type, convert to string
            return str(obj)
    
    @staticmethod
    def to_dict(results: Dict[str, List[Any]]) -> Dict[str, Any]:
        """
        Convert results to dictionary format.
        
        Args:
            results: Query results from GrandCypher
            
        Returns:
            Dictionary with columns and rows
        """
        try:
            logger.info(f"Formatter received results type: {type(results)}")
            logger.info(f"Formatter received results keys: {results.keys() if isinstance(results, dict) else 'N/A'}")
            if isinstance(results, dict) and results:
                first_key = list(results.keys())[0]
                first_col = results.get(first_key)
                if isinstance(first_col, list):
                    first_value = first_col[0] if first_col else None
                else:
                    first_value = first_col
                logger.info(
                    f"First result - key: {first_key}, value type: {type(first_value)}, value: {first_value}"
                )
            
            if not results:
                logger.debug("Empty results, returning empty dict")
                return {"columns": [], "rows": [], "count": 0}

            # Normalize to dict-of-lists. Some query paths (aggregations) may yield scalars.
            if isinstance(results, dict):
                normalized: Dict[str, List[Any]] = {}
                for k, v in results.items():
                    if isinstance(v, list):
                        normalized[k] = v
                    else:
                        normalized[k] = [v]
                results = normalized
            
            # GrandCypher returns dict of {column_name: [values]}
            columns = list(results.keys())
            logger.debug(f"Formatting results with columns: {columns}")
            
            # Transpose to rows and convert non-serializable types
            if columns:
                num_rows = len(results[columns[0]])
                rows = []
                for i in range(num_rows):
                    row = []
                    for col in columns:
                        value = results[col][i]
                        # Recursively convert non-JSON-serializable types
                        value = ResultFormatter._make_serializable(value)
                        row.append(value)
                    rows.append(row)
            else:
                rows = []
            
            logger.debug(f"Formatted {len(rows)} rows")
            return {
                "columns": columns,
                "rows": rows,
                "count": len(rows)
            }
        except Exception as e:
            logger.error(f"Failed to format results to dict: {e}", exc_info=True)
            raise
    
    @staticmethod
    def to_json(results: Dict[str, List[Any]], pretty: bool = False) -> str:
        """
        Convert results to JSON string.
        
        Args:
            results: Query results from GrandCypher
            pretty: Whether to pretty-print JSON
            
        Returns:
            JSON string
        """
        try:
            formatted = ResultFormatter.to_dict(results)
            if pretty:
                return json.dumps(formatted, indent=2, ensure_ascii=False)
            return json.dumps(formatted, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to format results to JSON: {e}", exc_info=True)
            raise
    
    @staticmethod
    def to_csv(results: Dict[str, List[Any]]) -> str:
        """
        Convert results to CSV string.
        
        Args:
            results: Query results from GrandCypher
            
        Returns:
            CSV string
        """
        formatted = ResultFormatter.to_dict(results)
        
        if not formatted["columns"]:
            return ""
        
        # Header row
        lines = [",".join(formatted["columns"])]
        
        # Data rows
        for row in formatted["rows"]:
            # Convert values to strings and escape commas
            escaped = [str(v).replace(",", "\\,") for v in row]
            lines.append(",".join(escaped))
        
        return "\n".join(lines)
    
    @staticmethod
    def to_table(results: Dict[str, List[Any]]) -> str:
        """
        Convert results to ASCII table string.
        
        Args:
            results: Query results from GrandCypher
            
        Returns:
            ASCII table string
        """
        formatted = ResultFormatter.to_dict(results)
        
        if not formatted["columns"]:
            return "No results"
        
        # Calculate column widths
        columns = formatted["columns"]
        widths = [len(col) for col in columns]
        
        for row in formatted["rows"]:
            for i, val in enumerate(row):
                widths[i] = max(widths[i], len(str(val)))
        
        # Build table
        lines = []
        
        # Header
        header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
        lines.append(header)
        lines.append("-" * len(header))
        
        # Rows
        for row in formatted["rows"]:
            line = " | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row))
            lines.append(line)
        
        # Footer
        lines.append(f"\n{formatted['count']} row(s)")
        
        return "\n".join(lines)
