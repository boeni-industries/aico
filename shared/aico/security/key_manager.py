"""
AICO Key Manager - Simple Implementation

Handles:
1. Master Password Setup - First-time password setup with secure storage
2. Unified Key Management - Three authentication scenarios in one class

KISS approach: Single file, minimal dependencies, clear functionality.
"""

import os
import getpass
import keyring
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


logger = logging.getLogger(__name__)


class AICOKeyManager:
    """
    Unified key management for AICO.
    
    Handles:
    1. Master password setup and authentication
    2. Database-specific key derivation
    3. Secure keyring integration
    4. Salt management for databases
    """
    
    # Key derivation constants
    DEFAULT_KDF_ITERATIONS = 100000  # PBKDF2 iterations for database keys
    KEY_LENGTH = 32  # 256-bit keys
    SALT_LENGTH = 16  # 128-bit salt
    
    def __init__(self, service_name: str = "AICO"):
        self.service_name = service_name
        logger.debug(f"Initialized AICOKeyManager for service: {service_name}")
        
    def setup_master_password(self, password: str) -> bytes:
        """
        First-time master password setup.
        
        Args:
            password: User's master password
            
        Returns:
            Derived master key
        """
        if self.has_stored_key():
            raise ValueError("Master password already set up. Use change_password() to update.")
            
        return self._derive_and_store(password)
        
    def authenticate(self, password: Optional[str] = None, interactive: bool = True) -> bytes:
        """
        Unified authentication method.
        
        Args:
            password: Master password (optional)
            interactive: Whether to prompt for password if needed
            
        Returns:
            Master key
        """
        # Try stored key first (service mode)
        stored_key = keyring.get_password(self.service_name, "master_key")
        if stored_key:
            return bytes.fromhex(stored_key)
            
        # Need password
        if password:
            # Verify password by deriving key and comparing
            derived_key = self._derive_key(password)
            # For first setup, store it
            if not self.has_stored_key():
                self._store_key(derived_key)
            return derived_key
            
        elif interactive:
            password = getpass.getpass("Enter AICO master password: ")
            return self.authenticate(password, interactive=False)
            
        else:
            raise ValueError("No stored key and no password provided")
            
    def has_stored_key(self) -> bool:
        """Check if master key is already stored."""
        try:
            stored_key = keyring.get_password(self.service_name, "master_key")
            return stored_key is not None
        except Exception:
            return False
            
    def change_password(self, old_password: str, new_password: str) -> bytes:
        """Change master password."""
        # Verify old password
        try:
            self.authenticate(old_password, interactive=False)
        except Exception:
            raise ValueError("Invalid old password")
            
        # Clear old key and set new one
        self.clear_stored_key()
        return self.setup_master_password(new_password)
        
    def clear_stored_key(self) -> None:
        """Remove stored key (security incident)."""
        try:
            keyring.delete_password(self.service_name, "master_key")
            keyring.delete_password(self.service_name, "salt")
        except Exception:
            pass  # Key might not exist
            
    def derive_database_key(
        self, 
        master_key: bytes, 
        database_type: str,
        db_path: Optional[str] = None,
        use_pbkdf2: bool = True
    ) -> bytes:
        """
        Derive database-specific encryption key from master key.
        
        Args:
            master_key: Master key
            database_type: Database type ("libsql", "duckdb", "rocksdb", "chroma")
            db_path: Database path for salt file management (required for libsql)
            use_pbkdf2: Use PBKDF2 for compatibility (libsql) vs Argon2id (others)
            
        Returns:
            Database-specific encryption key
        """
        if database_type == "libsql" and db_path:
            # Use PBKDF2 with database-specific salt for LibSQL compatibility
            salt = self._get_or_create_db_salt(db_path)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=self.KEY_LENGTH,
                salt=salt,
                iterations=self.DEFAULT_KDF_ITERATIONS,
                backend=default_backend()
            )
            
            # Derive from master key + database context
            context = master_key + f"aico-db-{database_type}".encode()
            return kdf.derive(context)
        else:
            # Use Argon2id for other databases
            salt = os.urandom(16)
            argon2 = Argon2id(
                salt=salt,
                length=32,             # 256-bit key
                iterations=2,          # Balanced for database operations
                lanes=2,               # 2 threads
                memory_cost=256*1024,  # 256MB in KiB
                ad=None,
                secret=None
            )
            
            context = master_key + f"aico-db-{database_type}".encode()
            return argon2.derive(context)
        
    def derive_file_encryption_key(self, master_key: bytes, file_purpose: str) -> bytes:
        """
        Derive file-specific encryption key from master key.
        
        Args:
            master_key: Master key
            file_purpose: File purpose identifier (e.g., "config", "logs")
            
        Returns:
            File-specific encryption key
        """
        salt = os.urandom(16)
        argon2 = Argon2id(
            salt=salt,
            length=32,             # 256-bit key
            iterations=1,          # Lighter for file operations
            lanes=2,               # 2 threads
            memory_cost=128*1024,  # 128MB in KiB
            ad=None,
            secret=None
        )
        
        context = master_key + f"aico-file-{file_purpose}".encode()
        return argon2.derive(context)
        
    def derive_purpose_key(self, master_key: bytes, purpose: str) -> bytes:
        """
        Generic purpose-specific key derivation.
        
        Args:
            master_key: Master key
            purpose: Purpose identifier
            
        Returns:
            Purpose-specific key
        """
        salt = os.urandom(16)
        argon2 = Argon2id(
            salt=salt,
            length=32,             # 256-bit key
            iterations=2,          # Lighter for derived keys
            lanes=2,               # 2 threads
            memory_cost=256*1024,  # 256MB in KiB
            ad=None,
            secret=None
        )
        
        context = master_key + purpose.encode()
        return argon2.derive(context)
        
    def _derive_and_store(self, password: str) -> bytes:
        """Derive key from password and store it."""
        master_key = self._derive_key(password)
        self._store_key(master_key)
        return master_key
        
    def _derive_key(self, password: str) -> bytes:
        """Derive master key from password."""
        # Get or create salt
        stored_salt = keyring.get_password(self.service_name, "salt")
        if stored_salt:
            salt = bytes.fromhex(stored_salt)
        else:
            salt = os.urandom(16)
            
        argon2 = Argon2id(
            salt=salt,
            length=32,             # 256-bit key
            iterations=3,          # 3 iterations for master key
            lanes=4,               # 4 threads (parallelism)
            memory_cost=1024*1024, # 1GB memory in KiB
            ad=None,
            secret=None
        )
        
        master_key = argon2.derive(password.encode())
        
        # Store salt if new
        if not stored_salt:
            keyring.set_password(self.service_name, "salt", salt.hex())
            
        return master_key
        
    def _store_key(self, master_key: bytes) -> None:
        """Store master key securely."""
        keyring.set_password(self.service_name, "master_key", master_key.hex())
        
    def _get_or_create_db_salt(self, db_path: str) -> bytes:
        """
        Get existing database salt or create new one.
        
        Args:
            db_path: Path to the database file
            
        Returns:
            Salt bytes for key derivation
        """
        db_file = Path(db_path)
        salt_file = db_file.with_suffix(db_file.suffix + '.salt')
        
        if salt_file.exists():
            with open(salt_file, 'rb') as f:
                salt = f.read()
            logger.debug(f"Loaded existing salt for {db_file.name}")
        else:
            salt = os.urandom(self.SALT_LENGTH)
            
            # Ensure parent directory exists
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(salt_file, 'wb') as f:
                f.write(salt)
            
            # Set secure file permissions
            if hasattr(os, 'chmod'):
                os.chmod(salt_file, 0o600)
            
            logger.info(f"Generated new salt for {db_file.name}")
        
        return salt
        
    def get_database_password_info(self, database_type: str, db_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about database password setup.
        
        Args:
            database_type: Database type
            db_path: Database path (for salt file location)
            
        Returns:
            Dictionary with password/encryption information
        """
        info = {
            "service_name": self.service_name,
            "database_type": database_type,
            "has_stored_key": self.has_stored_key(),
            "key_length": self.KEY_LENGTH,
            "salt_length": self.SALT_LENGTH
        }
        
        if database_type == "libsql" and db_path:
            db_file = Path(db_path)
            salt_file = db_file.with_suffix(db_file.suffix + '.salt')
            info.update({
                "database_path": str(db_file),
                "salt_file": str(salt_file),
                "salt_exists": salt_file.exists(),
                "kdf_iterations": self.DEFAULT_KDF_ITERATIONS,
                "kdf_algorithm": "PBKDF2-SHA256"
            })
        else:
            info.update({
                "kdf_algorithm": "Argon2id"
            })
            
        return info
        
    def store_database_password(self, password: str, database_type: str, username: Optional[str] = None) -> None:
        """
        Store database-specific password in keyring.
        
        Args:
            password: Database password to store
            database_type: Database type identifier
            username: Username for the database (optional)
        """
        key_name = f"{database_type}_password"
        if username:
            key_name = f"{database_type}_{username}_password"
            
        try:
            keyring.set_password(self.service_name, key_name, password)
            logger.info(f"Stored {database_type} password in keyring")
        except Exception as e:
            logger.warning(f"Failed to store {database_type} password in keyring: {e}")
            
    def get_database_password(self, database_type: str, username: Optional[str] = None) -> Optional[str]:
        """
        Retrieve database-specific password from keyring.
        
        Args:
            database_type: Database type identifier
            username: Username for the database (optional)
            
        Returns:
            Database password or None if not found
        """
        key_name = f"{database_type}_password"
        if username:
            key_name = f"{database_type}_{username}_password"
            
        try:
            password = keyring.get_password(self.service_name, key_name)
            if password:
                logger.debug(f"Retrieved {database_type} password from keyring")
            return password
        except Exception as e:
            logger.warning(f"Failed to retrieve {database_type} password from keyring: {e}")
            return None
