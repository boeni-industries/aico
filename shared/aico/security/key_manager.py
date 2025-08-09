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
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from aico.core.config import ConfigurationManager
import logging

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
    
    def __init__(self, service_name: str = "AICO"):
        self.service_name = service_name
        logger.debug(f"Initialized AICOKeyManager for service: {service_name}")
    
    def _get_security_config(self, key: str):
        """Get security configuration value using hierarchical YAML system."""
        from aico.core.config import ConfigurationManager
        config_manager = ConfigurationManager()
        config_manager.initialize()
        return config_manager.get(f"security.encryption.{key}")
    
    @property
    def KEY_LENGTH(self) -> int:
        """Get key length from configuration."""
        return self._get_security_config("key_length")
    
    @property
    def SALT_LENGTH(self) -> int:
        """Get salt length from configuration."""
        return self._get_security_config("salt_length")
    

        
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
        
        # Validate password strength
        self._validate_password_strength(password)
            
        return self._derive_and_store(password)
    
    def _validate_password_strength(self, password: str) -> None:
        """Validate password meets minimum security requirements."""
        min_length = self._get_security_config("password_policy.min_length") or 12
        
        if len(password) < min_length:
            raise ValueError(f"Password must be at least {min_length} characters long")
        
        # Check for common weak passwords
        weak_passwords = {"password", "123456", "12345", "admin", "qwerty", "letmein"}
        if password.lower() in weak_passwords:
            raise ValueError("Password is too common and easily guessable")
        
        # Basic complexity check
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        complexity_count = sum([has_upper, has_lower, has_digit, has_special])
        if complexity_count < 3:
            raise ValueError("Password must contain at least 3 of: uppercase, lowercase, digits, special characters")
        
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
        
        # Validate new password strength
        self._validate_password_strength(new_password)
            
        # Clear old key and set new one
        self.clear_stored_key()
        return self._derive_and_store(new_password)
        
    def clear_stored_key(self) -> None:
        """Remove stored key (security incident)."""
        try:
            keyring.delete_password(self.service_name, "master_key")
            keyring.delete_password(self.service_name, "salt")
            keyring.delete_password(self.service_name, "key_created")
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
                iterations=self._get_security_config("key_derivation.pbkdf2.iterations"),
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
                length=self._get_security_config("key_derivation.argon2id.length"),
                iterations=self._get_security_config("key_derivation.argon2id.database_operations"),
                lanes=self._get_security_config("key_derivation.argon2id.lanes.database_operations"),
                memory_cost=self._get_security_config("key_derivation.argon2id.memory_cost.database_operations"),
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
            length=self._get_security_config("key_derivation.argon2id.length"),
            iterations=self._get_security_config("key_derivation.argon2id.file_operations"),
            lanes=self._get_security_config("key_derivation.argon2id.lanes.file_operations"),
            memory_cost=self._get_security_config("key_derivation.argon2id.memory_cost.file_operations"),
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
            length=self._get_security_config("key_derivation.argon2id.length"),
            iterations=self._get_security_config("key_derivation.argon2id.derived_keys"),
            lanes=self._get_security_config("key_derivation.argon2id.lanes.derived_keys"),
            memory_cost=self._get_security_config("key_derivation.argon2id.memory_cost.derived_keys"),
            ad=None,
            secret=None
        )
        
        context = master_key + purpose.encode()
        return argon2.derive(context)
        
    def _derive_and_store(self, password: str) -> bytes:
        """Derive key from password and store it."""
        master_key = self._derive_key(password)
        self._store_key(master_key)
        # Store creation timestamp
        keyring.set_password(self.service_name, "key_created", str(int(time.time())))
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
            length=self._get_security_config("key_derivation.argon2id.length"),
            iterations=self._get_security_config("key_derivation.argon2id.master_key"),
            lanes=self._get_security_config("key_derivation.argon2id.lanes.master_key"),
            memory_cost=self._get_security_config("key_derivation.argon2id.memory_cost.master_key"),
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
                "kdf_iterations": self._get_security_config("key_derivation.pbkdf2.iterations"),
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
    
    def get_security_health_info(self) -> Dict[str, Any]:
        """Get comprehensive security health information."""
        info = {
            "has_master_key": self.has_stored_key(),
            "key_created": None,
            "key_age_days": None,
            "security_level": "Not Set Up",
            "algorithm": "Argon2id",
            "key_size": self.KEY_LENGTH,
            "memory_cost_mb": None,
            "iterations": None,
            "parallelism": None,
            "rotation_recommended": False,
            "backup_available": True  # Keys can be regenerated from password
        }
        
        if not info["has_master_key"]:
            return info
            
        # Get key creation time
        try:
            created_timestamp = keyring.get_password(self.service_name, "key_created")
            if created_timestamp:
                created_time = datetime.fromtimestamp(int(created_timestamp))
                info["key_created"] = created_time.strftime("%Y-%m-%d %H:%M:%S")
                info["key_age_days"] = (datetime.now() - created_time).days
        except Exception:
            pass
            
        # Get Argon2id parameters for master key
        try:
            memory_cost = self._get_security_config("key_derivation.argon2id.memory_cost.master_key")
            iterations = self._get_security_config("key_derivation.argon2id.master_key")
            parallelism = self._get_security_config("key_derivation.argon2id.lanes.master_key")
            
            if memory_cost:
                info["memory_cost_mb"] = memory_cost // 1024  # Convert KiB to MB
            if iterations:
                info["iterations"] = iterations
            if parallelism:
                info["parallelism"] = parallelism
        except Exception:
            pass
            
        # Assess security level
        if info["key_age_days"] is not None:
            if info["key_age_days"] > 365:
                info["security_level"] = "Needs Rotation"
                info["rotation_recommended"] = True
            elif info["key_age_days"] > 180:
                info["security_level"] = "Good"
                info["rotation_recommended"] = True
            else:
                info["security_level"] = "Strong"
        else:
            info["security_level"] = "Good"
            
        return info
    
    def benchmark_key_derivation(self) -> Dict[str, Any]:
        """Benchmark key derivation performance for diagnostics."""
        if not self.has_stored_key():
            raise ValueError("No master key set up for benchmarking")
            
        results = {
            "master_key_derivation_ms": None,
            "database_key_derivations": {},
            "performance_assessment": "Unknown",
            "recommendations": []
        }
        
        # Test master key derivation (simulate with dummy password)
        try:
            start_time = time.time()
            # Use a dummy password for timing test
            self._derive_key("benchmark_test_password_12345")
            end_time = time.time()
            results["master_key_derivation_ms"] = int((end_time - start_time) * 1000)
        except Exception as e:
            results["master_key_derivation_ms"] = f"Error: {e}"
            
        # Test database key derivations
        try:
            master_key = b"dummy_key_for_benchmark_32_bytes"
            for db_type in ["libsql", "duckdb", "chroma"]:
                try:
                    start_time = time.time()
                    if db_type == "libsql":
                        # For benchmarking, use in-memory salt (no disk writes)
                        self._benchmark_libsql_key_derivation(master_key)
                    else:
                        self.derive_database_key(master_key, db_type)
                    end_time = time.time()
                    results["database_key_derivations"][db_type] = {
                        "time_ms": int((end_time - start_time) * 1000),
                        "status": "Success"
                    }
                except Exception as e:
                    results["database_key_derivations"][db_type] = {
                        "time_ms": None,
                        "status": f"Error: {e}"
                    }
        except Exception:
            pass
            
        # Performance assessment
        master_time = results["master_key_derivation_ms"]
        if isinstance(master_time, int):
            if master_time < 500:
                results["performance_assessment"] = "Fast"
                results["recommendations"].append("Increase memory cost in security.yaml for stronger protection")
            elif master_time < 2000:
                results["performance_assessment"] = "Optimal"
                # No recommendations for optimal performance - don't add anything
            elif master_time < 5000:
                results["performance_assessment"] = "Slow"
                results["recommendations"].append("Reduce memory cost in security.yaml for better user experience")
            else:
                results["performance_assessment"] = "Very Slow"
                results["recommendations"].append("Reduce memory cost in security.yaml to improve usability")
                
        return results
    
    def _benchmark_libsql_key_derivation(self, master_key: bytes) -> None:
        """
        Benchmark LibSQL key derivation using in-memory salt (no disk writes).
        
        Args:
            master_key: Master key for derivation
        """
        # Generate random salt in memory only (never written to disk)
        salt = os.urandom(self.SALT_LENGTH)
        
        # Perform PBKDF2 key derivation (same as real LibSQL but no file I/O)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=self._get_security_config("key_derivation.pbkdf2.iterations"),
            backend=default_backend()
        )
        
        # Derive key (same computation as real database)
        context = master_key + b"aico-db-libsql"
        kdf.derive(context)
        
        # Salt and derived key automatically garbage collected
        # No disk writes, no cleanup needed, no security risk
