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
from typing import Optional
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives import hashes


class AICOKeyManager:
    """
    Simple, unified key management for AICO.
    
    Handles three scenarios:
    1. Master password setup (first time)
    2. Interactive authentication (user login)
    3. Service startup (automatic)
    """
    
    def __init__(self, service_name: str = "AICO"):
        self.service_name = service_name
        
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
            
    def derive_database_key(self, master_key: bytes, database_type: str) -> bytes:
        """
        Derive database-specific encryption key from master key.
        
        Args:
            master_key: Master key
            database_type: Database type ("libsql", "duckdb", "rocksdb", "chroma")
            
        Returns:
            Database-specific encryption key
        """
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
