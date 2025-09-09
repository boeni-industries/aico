"""
Encrypted LibSQL Connection Management

This module provides encrypted LibSQL database connections using SQLCipher-style
encryption. It handles key derivation, database encryption setup, and secure
connection management for AICO's privacy-first data storage.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import sqlite3
import libsql

from .connection import LibSQLConnection
from aico.security.key_manager import AICOKeyManager
from aico.core.config import ConfigurationManager

# Lazy logger initialization to avoid circular imports
_logger = None

def _get_logger():
    global _logger
    if _logger is None:
        try:
            from aico.core.logging import get_logger
            
            # Try to get logger (assume already initialized by CLI)
            try:
                _logger = get_logger("data", "libsql.encrypted")
            except RuntimeError:
                # Logging not initialized - use fallback for CLI context
                import logging
                _logger = logging.getLogger("data.libsql.encrypted")
        except Exception:
            # Fallback to standard logging if unified system fails
            import logging
            _logger = logging.getLogger("data.libsql.encrypted")
    return _logger

class EncryptedLibSQLConnection(LibSQLConnection):
    """
    Encrypted LibSQL database connection manager.
    
    Extends the basic LibSQL connection with encryption capabilities:
    - Uses AICOKeyManager for secure key management
    - SQLCipher-style database encryption via PRAGMA statements
    - Transparent encryption/decryption for all operations
    """
    
    def __init__(
        self, 
        db_path: str, 
        encryption_key: Optional[bytes] = None,
        key_manager: Optional[AICOKeyManager] = None,
        master_password: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize encrypted LibSQL connection.
        
        Args:
            db_path: Path to the database file
            encryption_key: Pre-derived encryption key (preferred)
            key_manager: AICOKeyManager instance for key derivation
            master_password: Master password (if key_manager provided)
            **kwargs: Additional connection parameters
        """
        super().__init__(db_path, **kwargs)
        
        self._encryption_key = encryption_key
        if key_manager:
            self._key_manager = key_manager
        else:
            from aico.core.config import ConfigurationManager
            config = ConfigurationManager()
            self._key_manager = AICOKeyManager(config)
        self._master_password = master_password
        
        _get_logger().debug(f"Initialized encrypted LibSQL connection for {self.db_path}")
    
    def _get_encryption_key(self) -> bytes:
        """
        Get or derive encryption key for the database.
        
        Returns:
            Encryption key bytes
            
        Raises:
            ValueError: If no key available and cannot derive
        """
        if self._encryption_key:
            return self._encryption_key
            
        # Try to derive from key manager
        try:
            master_key = self._key_manager.authenticate(
                password=self._master_password,
                interactive=False
            )
            
            # Derive database-specific key
            db_key = self._key_manager.derive_database_key(
                master_key=master_key,
                database_type="libsql",
                db_path=str(self.db_path)
            )
            
            self._encryption_key = db_key
            _get_logger().debug("Derived encryption key from key manager")
            return db_key
            
        except Exception as e:
            raise ValueError(
                f"Cannot derive encryption key: {e}. "
                "Provide encryption_key parameter or ensure master password is available."
            ) from e
    
    def close(self) -> None:
        """Close the encrypted database connection."""
        self.disconnect()
    
    def _setup_encryption(self) -> bytes:
        """
        Set up database encryption key.
        
        Returns:
            Encryption key bytes
        """
        return self._get_encryption_key()
    
    def connect(self):
        """
        Establish encrypted database connection.
        
        Returns:
            Active encrypted LibSQL connection
            
        Raises:
            ConnectionError: If connection or encryption setup fails
        """
        try:
            # Set up encryption key first
            encryption_key = self._setup_encryption()
            
            # Convert key to hex string for PRAGMA
            key_hex = encryption_key.hex()
            
            # Establish connection with encryption key
            connection = libsql.connect(str(self.db_path))
            
            # Apply encryption key immediately after connection
            connection.execute(f"PRAGMA key = 'x\"{key_hex}\"'")
            
            # Apply database configuration settings (must be done outside transactions)
            self._apply_database_settings(connection)
            
            # Test that encryption is working by creating/accessing a test table
            try:
                connection.execute("SELECT count(*) FROM sqlite_master")
                _get_logger().debug("Database encryption verified successfully")
            except Exception as e:
                _get_logger().error(f"Database encryption verification failed: {e}")
                raise ConnectionError("Invalid encryption key or corrupted database") from e
            
            # Store the connection for future use
            self._connection = connection
            return connection
            
        except Exception as e:
            _get_logger().error(f"Failed to establish encrypted connection: {e}")
            raise ConnectionError(f"Encrypted database connection failed: {e}") from e
    
    def _apply_database_settings(self, connection) -> None:
        """
        Apply LibSQL configuration settings from database.yaml.
        
        Args:
            connection: Active database connection
        """
        try:
            # Load configuration
            config = ConfigurationManager()
            config.initialize()
            libsql_config = config.get("database.libsql", {})
            
            # Apply journal mode (default: WAL)
            journal_mode = libsql_config.get("journal_mode", "WAL")
            connection.execute(f"PRAGMA journal_mode = {journal_mode}")
            _get_logger().debug(f"Set journal_mode to {journal_mode}")
            
            # Apply synchronous mode (default: NORMAL)
            synchronous = libsql_config.get("synchronous", "NORMAL")
            connection.execute(f"PRAGMA synchronous = {synchronous}")
            _get_logger().debug(f"Set synchronous to {synchronous}")
            
            # Apply cache size (default: 2000)
            cache_size = libsql_config.get("cache_size", 2000)
            connection.execute(f"PRAGMA cache_size = {cache_size}")
            _get_logger().debug(f"Set cache_size to {cache_size}")
            
            # Apply busy timeout for database locking (default: 30 seconds)
            busy_timeout = libsql_config.get("busy_timeout", 30000)
            connection.execute(f"PRAGMA busy_timeout = {busy_timeout}")
            _get_logger().debug(f"Set busy_timeout to {busy_timeout}ms")
            
            _get_logger().debug("Applied LibSQL configuration settings")
            
        except Exception as e:
            _get_logger().warning(f"Failed to apply database settings: {e}")
            # Don't fail connection for configuration issues
    
    def set_master_password(self, password: str, store_in_keyring: bool = True) -> None:
        """
        Set master password for encryption.
        
        Args:
            password: New master password
            store_in_keyring: Whether to store password in system keyring
        """
        self._master_password = password
        self._encryption_key = None  # Force re-derivation
        
        if store_in_keyring:
            self._key_manager.store_database_password(password, "libsql", self.db_path.stem)
            
        _get_logger().info("Master password updated")
    
    def change_password(self, old_password: str, new_password: str) -> None:
        """
        Change database encryption password.
        
        This operation:
        1. Verifies old password
        2. Updates master password in key manager
        3. Forces key re-derivation
        
        Args:
            old_password: Current password
            new_password: New password
            
        Raises:
            ValueError: If old password is incorrect
            RuntimeError: If password change fails
        """
        try:
            # Verify old password by attempting authentication
            self._key_manager.authenticate(old_password, interactive=False)
            
            # Change password in key manager
            self._key_manager.change_password(old_password, new_password)
            
            # Update local state
            self._master_password = new_password
            self._encryption_key = None  # Force re-derivation
            
            _get_logger().info("Database password changed successfully")
            
        except Exception as e:
            _get_logger().error(f"Password change failed: {e}")
            raise RuntimeError(f"Failed to change password: {e}") from e
    
    def verify_encryption(self) -> bool:
        """
        Verify that database encryption is working correctly.
        
        Returns:
            True if encryption is active and working
        """
        try:
            with self.get_connection() as conn:
                # Try to read from sqlite_master - this will fail if key is wrong
                conn.execute("SELECT count(*) FROM sqlite_master")
                
                # Check if database file contains readable SQLite header
                # Encrypted databases should not have readable headers
                with open(self.db_path, 'rb') as f:
                    header = f.read(16)
                
                # SQLite header starts with "SQLite format 3\x00"
                sqlite_header = b"SQLite format 3\x00"
                is_encrypted = not header.startswith(sqlite_header)
                
                _get_logger().debug(f"Database encryption status: {'active' if is_encrypted else 'inactive'}")
                return is_encrypted
                
        except Exception as e:
            _get_logger().error(f"Encryption verification failed: {e}")
            return False
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """
        Get information about current encryption setup.
        
        Returns:
            Dictionary with encryption information
        """
        base_info = {
            "encrypted": self._encryption_key is not None,
            "database_path": str(self.db_path)
        }
        
        # Get detailed info from key manager
        key_manager_info = self._key_manager.get_database_password_info(
            "libsql", str(self.db_path)
        )
        
        base_info.update(key_manager_info)
        return base_info
    
    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._connection else "disconnected"
        encrypted = "encrypted" if self._encryption_key else "not encrypted"
        return f"EncryptedLibSQLConnection(db_path='{self.db_path}', status='{status}', {encrypted})"


def create_encrypted_database(
    db_path: str,
    master_password: str,
    store_in_keyring: bool = True,
    key_manager: Optional[AICOKeyManager] = None,
    **kwargs
) -> EncryptedLibSQLConnection:
    """
    Create a new encrypted database with the specified password.
    
    Args:
        db_path: Path for the new database
        master_password: Master password for encryption
        store_in_keyring: Whether to store password in system keyring
        key_manager: AICOKeyManager instance (optional)
        **kwargs: Additional connection parameters
        
    Returns:
        Configured encrypted connection
        
    Raises:
        FileExistsError: If database already exists
        RuntimeError: If database creation fails
    """
    db_file = Path(db_path)
    
    if db_file.exists():
        raise FileExistsError(f"Database already exists: {db_path}")
    
    try:
        # Initialize key manager and derive key
        if key_manager:
            km = key_manager
        else:
            from aico.core.config import ConfigurationManager
            config = ConfigurationManager()
            km = AICOKeyManager(config)
        
        # Set up master password if this is first time
        if not km.has_stored_key():
            master_key = km.setup_master_password(master_password)
        else:
            master_key = km.authenticate(master_password, interactive=False)
            
        # Derive database-specific encryption key
        encryption_key = km.derive_database_key(
            master_key=master_key,
            database_type="libsql",
            db_path=db_path
        )
        
        # Create encrypted connection with pre-derived key
        conn = EncryptedLibSQLConnection(
            db_path=db_path,
            encryption_key=encryption_key,
            key_manager=km,
            **kwargs
        )
        
        # Store password in keyring if requested
        if store_in_keyring:
            km.store_database_password(master_password, "libsql", db_file.stem)
        
        # Initialize database by connecting and creating a test table
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _aico_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                INSERT INTO _aico_metadata (key, value) 
                VALUES ('database_version', '1.0')
            """)
            
            conn.commit()
        
        _get_logger().info(f"Created encrypted database: {db_path}")
        return conn
        
    except Exception as e:
        # Clean up on failure
        if db_file.exists():
            db_file.unlink()
        
        salt_file = db_file.with_suffix(db_file.suffix + '.salt')
        if salt_file.exists():
            salt_file.unlink()
        
        _get_logger().error(f"Failed to create encrypted database: {e}")
        raise RuntimeError(f"Database creation failed: {e}") from e
