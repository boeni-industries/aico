"""
Basic LibSQL Connection Management

This module provides basic LibSQL database connection functionality
without encryption. It handles connection lifecycle, basic operations,
and error handling for local SQLite-compatible databases.
"""

import os
from pathlib import Path
from typing import Optional, Any, Dict, List, Tuple
from contextlib import contextmanager

import libsql

# Lazy logger initialization to avoid circular imports
_logger = None

def _get_logger():
    global _logger
    if _logger is None:
        try:
            from aico.core.logging import get_logger, initialize_logging
            from aico.core.config import ConfigurationManager
            
            # Try to initialize logging if not already done
            try:
                _logger = get_logger("data", "libsql.connection")
            except RuntimeError:
                # Logging not initialized, initialize it
                config = ConfigurationManager()
                initialize_logging(config)
                _logger = get_logger("data", "libsql.connection")
        except Exception:
            # Fallback to standard logging if unified system fails
            import logging
            _logger = logging.getLogger("data.libsql.connection")
    return _logger


class LibSQLConnection:
    """
    Basic LibSQL database connection manager.
    
    Provides a clean interface for connecting to local LibSQL/SQLite databases
    with proper connection lifecycle management and error handling.
    """
    
    def __init__(self, db_path: str, **kwargs):
        """
        Initialize LibSQL connection.
        
        Args:
            db_path: Path to the database file
            **kwargs: Additional connection parameters
        """
        self.db_path = Path(db_path)
        self.connection_params = kwargs
        self._connection: Optional[libsql.Connection] = None
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        _get_logger().debug(f"Initialized LibSQL connection for {self.db_path}")
    
    def connect(self) -> libsql.Connection:
        """
        Establish database connection.
        
        Returns:
            Active LibSQL connection
            
        Raises:
            ConnectionError: If connection fails
        """
        try:
            if self._connection is None:
                self._connection = libsql.connect(
                    str(self.db_path),
                    **self.connection_params
                )
                _get_logger().debug(f"Connected to LibSQL database: {self.db_path}")
            
            return self._connection
            
        except Exception as e:
            _get_logger().error(f"Failed to connect to LibSQL database {self.db_path}: {e}")
            raise ConnectionError(f"Database connection failed: {e}") from e
    
    def disconnect(self) -> None:
        """Close database connection."""
        if self._connection:
            try:
                self._connection.close()
                _get_logger().info(f"Disconnected from LibSQL database: {self.db_path}")
            except Exception as e:
                _get_logger().warning(f"Error closing connection: {e}")
            finally:
                self._connection = None
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            Active LibSQL connection
            
        Example:
            with conn.get_connection() as db:
                result = db.execute("SELECT * FROM users")
        """
        connection = self.connect()
        try:
            yield connection
        finally:
            # Note: We don't auto-close here to allow connection reuse
            # Call disconnect() explicitly when done
            pass
    
    def execute(self, query: str, parameters: Optional[Tuple] = None) -> Any:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            parameters: Query parameters tuple
            
        Returns:
            Query result
            
        Raises:
            DatabaseError: If query execution fails
        """
        try:
            with self.get_connection() as conn:
                if parameters:
                    result = conn.execute(query, parameters)
                else:
                    result = conn.execute(query)
                
                _get_logger().debug(f"Executed query: {query[:100]}...")
                return result
                
        except Exception as e:
            _get_logger().error(f"Query execution failed: {e}")
            raise RuntimeError(f"Database query failed: {e}") from e
    
    def execute_many(self, query: str, parameters_list: List[Tuple]) -> None:
        """
        Execute a SQL query multiple times with different parameters.
        
        Args:
            query: SQL query string
            parameters_list: List of parameter tuples
            
        Raises:
            DatabaseError: If query execution fails
        """
        try:
            with self.get_connection() as conn:
                for parameters in parameters_list:
                    conn.execute(query, parameters)
                conn.commit()
                
                _get_logger().debug(f"Executed {len(parameters_list)} queries: {query[:100]}...")
                
        except Exception as e:
            _get_logger().error(f"Batch query execution failed: {e}")
            raise RuntimeError(f"Database batch operation failed: {e}") from e
    
    def fetch_one(self, query: str, parameters: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row from query results.
        
        Args:
            query: SQL query string
            parameters: Query parameters tuple
            
        Returns:
            Single row as dictionary or None
        """
        result = self.execute(query, parameters)
        row = result.fetchone()
        
        if row:
            # Convert to dictionary using column names
            columns = [desc[0] for desc in result.description] if result.description else []
            return dict(zip(columns, row))
        
        return None
    
    def fetch_all(self, query: str, parameters: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Fetch all rows from query results.
        
        Args:
            query: SQL query string
            parameters: Query parameters tuple
            
        Returns:
            List of rows as dictionaries
        """
        result = self.execute(query, parameters)
        rows = result.fetchall()
        
        if rows and result.description:
            columns = [desc[0] for desc in result.description]
            return [dict(zip(columns, row)) for row in rows]
        
        return []
    
    def commit(self) -> None:
        """Commit current transaction."""
        if self._connection:
            self._connection.commit()
            _get_logger().debug("Transaction committed")
    
    def rollback(self) -> None:
        """Rollback current transaction."""
        if self._connection:
            self._connection.rollback()
            _get_logger().debug("Transaction rolled back")
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        
        Automatically commits on success or rolls back on error.
        
        Example:
            with conn.transaction():
                conn.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
                conn.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))
        """
        try:
            yield self
            self.commit()
            _get_logger().debug("Transaction committed successfully")
        except Exception as e:
            self.rollback()
            _get_logger().error(f"Transaction rolled back due to error: {e}")
            raise
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
        """
        result = self.fetch_one(query, (table_name,))
        return result is not None
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get information about table columns.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        query = f"PRAGMA table_info({table_name})"
        return self.fetch_all(query)
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._connection else "disconnected"
        return f"LibSQLConnection(db_path='{self.db_path}', status='{status}')"
