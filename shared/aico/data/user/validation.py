"""
Database query validation to catch SQLite syntax in PostgreSQL code
"""
import re
from typing import Any


class QueryValidator:
    """Validates database queries to ensure PostgreSQL syntax is used"""
    
    # Patterns that indicate SQLite syntax (should fail loudly)
    SQLITE_PATTERNS = [
        (r'\bWHERE\s+\w+\s*=\s*\?', "SQLite placeholder '?' found in WHERE clause - use $N instead"),
        (r'\bSET\s+\w+\s*=\s*\?', "SQLite placeholder '?' found in SET clause - use $N instead"),
        (r'\bVALUES\s*\([^)]*\?', "SQLite placeholder '?' found in VALUES clause - use $N instead"),
        (r'\.fetch_one\(', "SQLite method 'fetch_one()' found - use 'fetchrow()' instead"),
        (r'\.fetch_all\(', "SQLite method 'fetch_all()' found - use 'fetch()' instead"),
        (r'\.fetchone\(', "SQLite method 'fetchone()' found - use 'fetchrow()' instead"),
        (r'\.fetchall\(', "SQLite method 'fetchall()' found - use 'fetch()' instead"),
        (r'\.rowcount', "SQLite attribute 'rowcount' found - parse command tag string instead"),
        (r'\bdatetime\([\'"]now[\'"]\)', "SQLite datetime('now') found - use CURRENT_TIMESTAMP instead"),
    ]
    
    @classmethod
    def validate_query(cls, query: str, context: str = "") -> None:
        """
        Validate a SQL query for PostgreSQL compatibility
        
        Args:
            query: SQL query string to validate
            context: Context information (function name, etc.) for error messages
            
        Raises:
            ValueError: If SQLite syntax is detected
        """
        for pattern, error_msg in cls.SQLITE_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                full_error = f"❌ SQLITE SYNTAX DETECTED in {context}: {error_msg}\nQuery: {query[:200]}"
                raise ValueError(full_error)
    
    @classmethod
    def validate_execute_call(cls, query: str, params: Any, context: str = "") -> None:
        """
        Validate an execute() call for PostgreSQL compatibility
        
        Args:
            query: SQL query string
            params: Query parameters
            context: Context information for error messages
            
        Raises:
            ValueError: If SQLite syntax is detected
        """
        # Check query syntax
        cls.validate_query(query, context)
        
        # Check if params are passed as tuple (SQLite style) instead of unpacked (PostgreSQL style)
        if isinstance(params, tuple) and len(params) > 0:
            # This might be SQLite style - warn about it
            if '?' in query:
                raise ValueError(
                    f"❌ SQLITE SYNTAX in {context}: Parameters passed as tuple with '?' placeholders. "
                    f"Use $N placeholders and unpack parameters: execute(query, *params) or execute(query, param1, param2)"
                )
