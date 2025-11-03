"""
Result formatting for GQL/Cypher query results.

Converts query results to various output formats (table, JSON, CSV).
"""

import json
from typing import Any, Dict, List


class ResultFormatter:
    """Formats query results for display."""
    
    @staticmethod
    def to_dict(results: Dict[str, List[Any]]) -> Dict[str, Any]:
        """
        Convert results to dictionary format.
        
        Args:
            results: Query results from GrandCypher
            
        Returns:
            Dictionary with columns and rows
        """
        if not results:
            return {"columns": [], "rows": [], "count": 0}
        
        # GrandCypher returns dict of {column_name: [values]}
        columns = list(results.keys())
        
        # Transpose to rows
        if columns:
            num_rows = len(results[columns[0]])
            rows = []
            for i in range(num_rows):
                row = [results[col][i] for col in columns]
                rows.append(row)
        else:
            rows = []
        
        return {
            "columns": columns,
            "rows": rows,
            "count": len(rows)
        }
    
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
        formatted = ResultFormatter.to_dict(results)
        if pretty:
            return json.dumps(formatted, indent=2, default=str)
        return json.dumps(formatted, default=str)
    
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
