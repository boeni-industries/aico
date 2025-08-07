"""
Encrypted LibSQL Connection Management

This module provides encrypted LibSQL database connections using SQLCipher-style
encryption. It handles key derivation, database encryption setup, and secure
connection management for AICO's privacy-first data storage.
"""

import os
import logging
import hashlib
from pathlib import Path
from typing import Optional, Any, Dict, List, Tuple, Union

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import keyring

from .connection import LibSQLConnection

logger = logging.getLogger(__name__)


class EncryptedLibSQLConnection(LibSQLConnection):
    """
    Encrypted LibSQL database connection manager.
    
    Extends the basic LibSQL connection with encryption capabilities:
    - Automatic key derivation from master password
    - SQLCipher-style database encryption via PRAGMA statements
    - Secure key storage using system keyring
    - Transparent encryption/decryption for all operations
    """
    
    # Encryption configuration
    DEFAULT_KDF_ITERATIONS = 100000  # PBKDF2 iterations
    KEY_LENGTH = 32  # 256-bit key
    SALT_LENGTH = 16  # 128-bit salt
    
    def __init__(
        self, 
        db_path: str, 
        master_password: Optional[str] = None,
        keyring_service: str = "aico",
        keyring_username: Optional[str] = None,
        kdf_iterations: int = DEFAULT_KDF_ITERATIONS,
        **kwargs
    ):
        """
        Initialize encrypted LibSQL connection.
        
        Args:
            db_path: Path to the database file
            master_password: Master password for encryption (if None, uses keyring)
            keyring_service: Keyring service name for secure storage
            keyring_username: Keyring username (defaults to db filename)
            kdf_iterations: PBKDF2 iterations for key derivation
            **kwargs: Additional connection parameters
        """
        super().__init__(db_path, **kwargs)
        
        self.keyring_service = keyring_service
        self.keyring_username = keyring_username or self.db_path.stem
        self.kdf_iterations = kdf_iterations
        self._master_password = master_password
        self._encryption_key: Optional[bytes] = None
        self._salt: Optional[bytes] = None
        
        logger.debug(f"Initialized encrypted LibSQL connection for {self.db_path}")
    
    def _get_master_password(self) -> str:
        """
        Get master password from provided value or keyring.
        
        Returns:
            Master password string
            
        Raises:
            ValueError: If no password available
        """
        if self._master_password:
            return self._master_password
        
        # Try to get from keyring
        password = keyring.get_password(self.keyring_service, self.keyring_username)
        if password:
            logger.debug("Retrieved master password from keyring")
            return password
        
        raise ValueError(
            f"No master password available for {self.keyring_username}. "
            "Provide master_password parameter or store in keyring."
        )
    
    def _store_master_password(self, password: str) -> None:
        """
        Store master password in system keyring.
        
        Args:
            password: Master password to store
        """
        try:
            keyring.set_password(self.keyring_service, self.keyring_username, password)
            logger.info(f"Stored master password in keyring for {self.keyring_username}")
        except Exception as e:
            logger.warning(f"Failed to store password in keyring: {e}")
    
    def _get_or_create_salt(self) -> bytes:
        """
        Get existing salt from database or create new one.
        
        Returns:
            Salt bytes for key derivation
        """
        salt_file = self.db_path.with_suffix(self.db_path.suffix + '.salt')
        
        if salt_file.exists():
            # Load existing salt
            with open(salt_file, 'rb') as f:
                salt = f.read()
            logger.debug("Loaded existing encryption salt")
        else:
            # Generate new salt
            salt = os.urandom(self.SALT_LENGTH)
            
            # Store salt securely
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            with open(salt_file, 'wb') as f:
                f.write(salt)
            
            # Set restrictive permissions (owner read/write only)
            if hasattr(os, 'chmod'):
                os.chmod(salt_file, 0o600)
            
            logger.info("Generated new encryption salt")
        
        return salt
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password and salt using PBKDF2.
        
        Args:
            password: Master password
            salt: Salt bytes
            
        Returns:
            Derived encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=self.kdf_iterations,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode('utf-8'))
        logger.debug("Derived encryption key using PBKDF2")
        return key
    
    def _setup_encryption(self) -> bytes:
        """
        Set up database encryption key.
        
        Returns:
            Encryption key bytes
        """
        if self._encryption_key is None:
            password = self._get_master_password()
            salt = self._get_or_create_salt()
            self._encryption_key = self._derive_key(password, salt)
            self._salt = salt
        
        return self._encryption_key
    
    def connect(self):
        """
        Establish encrypted database connection.
        
        Returns:
            Active encrypted LibSQL connection
            
        Raises:
            ConnectionError: If connection or encryption setup fails
        """
        try:
            # Get base connection
            connection = super().connect()
            
            # Set up encryption
            encryption_key = self._setup_encryption()
            
            # Convert key to hex string for PRAGMA
            key_hex = encryption_key.hex()
            
            # Apply encryption via PRAGMA
            # Note: This follows SQLCipher conventions
            connection.execute(f"PRAGMA key = 'x\"{key_hex}\"'")
            
            # Test that encryption is working by creating/accessing a test table
            try:
                connection.execute("SELECT count(*) FROM sqlite_master")
                logger.debug("Database encryption verified successfully")
            except Exception as e:
                logger.error(f"Database encryption verification failed: {e}")
                raise ConnectionError("Invalid encryption key or corrupted database") from e
            
            return connection
            
        except Exception as e:
            logger.error(f"Failed to establish encrypted connection: {e}")
            raise ConnectionError(f"Encrypted database connection failed: {e}") from e
    
    def set_master_password(self, password: str, store_in_keyring: bool = True) -> None:
        """
        Set master password for encryption.
        
        Args:
            password: New master password
            store_in_keyring: Whether to store password in system keyring
        """
        self._master_password = password
        self._encryption_key = None  # Force key re-derivation
        
        if store_in_keyring:
            self._store_master_password(password)
        
        logger.info("Master password updated")
    
    def change_password(self, old_password: str, new_password: str) -> None:
        """
        Change database encryption password.
        
        This is a complex operation that requires:
        1. Verifying old password
        2. Creating new encrypted database with new password
        3. Copying all data
        4. Replacing old database
        
        Args:
            old_password: Current password
            new_password: New password
            
        Raises:
            ValueError: If old password is incorrect
            RuntimeError: If password change fails
        """
        # This is a placeholder for password change functionality
        # Full implementation would require careful data migration
        raise NotImplementedError(
            "Password change functionality requires careful implementation "
            "to avoid data loss. Use database backup/restore for now."
        )
    
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
                
                logger.debug(f"Database encryption status: {'active' if is_encrypted else 'inactive'}")
                return is_encrypted
                
        except Exception as e:
            logger.error(f"Encryption verification failed: {e}")
            return False
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """
        Get information about current encryption setup.
        
        Returns:
            Dictionary with encryption information
        """
        return {
            "encrypted": self._encryption_key is not None,
            "kdf_iterations": self.kdf_iterations,
            "key_length": self.KEY_LENGTH,
            "salt_length": self.SALT_LENGTH,
            "keyring_service": self.keyring_service,
            "keyring_username": self.keyring_username,
            "database_path": str(self.db_path),
            "salt_file": str(self.db_path.with_suffix(self.db_path.suffix + '.salt'))
        }
    
    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._connection else "disconnected"
        encrypted = "encrypted" if self._encryption_key else "not encrypted"
        return f"EncryptedLibSQLConnection(db_path='{self.db_path}', status='{status}', {encrypted})"


def create_encrypted_database(
    db_path: str,
    master_password: str,
    store_in_keyring: bool = True,
    **kwargs
) -> EncryptedLibSQLConnection:
    """
    Create a new encrypted database with the specified password.
    
    Args:
        db_path: Path for the new database
        master_password: Master password for encryption
        store_in_keyring: Whether to store password in system keyring
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
        # Create encrypted connection
        conn = EncryptedLibSQLConnection(
            db_path=db_path,
            master_password=master_password,
            **kwargs
        )
        
        # Store password in keyring if requested
        if store_in_keyring:
            conn._store_master_password(master_password)
        
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
        
        logger.info(f"Created encrypted database: {db_path}")
        return conn
        
    except Exception as e:
        # Clean up on failure
        if db_file.exists():
            db_file.unlink()
        
        salt_file = db_file.with_suffix(db_file.suffix + '.salt')
        if salt_file.exists():
            salt_file.unlink()
        
        logger.error(f"Failed to create encrypted database: {e}")
        raise RuntimeError(f"Database creation failed: {e}") from e
