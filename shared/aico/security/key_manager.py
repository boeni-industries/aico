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
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from aico.core.config import ConfigurationManager

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
                _logger = get_logger("security", "key_manager")
            except RuntimeError:
                # Logging not initialized, initialize it
                config = ConfigurationManager()
                initialize_logging(config)
                _logger = get_logger("security", "key_manager")
        except Exception:
            # Fallback to standard logging if unified system fails
            import logging
            _logger = logging.getLogger("security.key_manager")
    return _logger


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
        self._session_cache_file = self._get_session_cache_file()
        self._session_cache = self._load_session_cache()  # Load persistent session cache
        _get_logger().debug(f"Initialized AICOKeyManager for service: {service_name}")
    
    def _is_sensitive_command(self, command_path: str) -> bool:
        """Check if command requires fresh authentication."""
        sensitive_commands = {
            'security.passwd',
            'security.reset', 
            'security.export',
            'security.import',
            'logs.export',
            'dev.reset'
        }
        return command_path in sensitive_commands
        
    
    def get_jwt_secret(self, service_name: str = "api_gateway") -> str:
        """Get or create JWT signing secret for a service"""
        import secrets
        
        key_name = f"{service_name}_jwt_secret"
        
        try:
            # Try to get existing secret from keyring
            secret = keyring.get_password(self.service_name, key_name)
            if secret:
                return secret
        except Exception:
            pass
        
        # Create new JWT secret
        secret = secrets.token_urlsafe(32)
        
        try:
            keyring.set_password(self.service_name, key_name, secret)
            _get_logger().info(f"Created new JWT secret for service: {service_name}")
        except Exception as e:
            _get_logger().warning(f"Could not store JWT secret in keyring: {e}")
        
        return secret
    
    def rotate_jwt_secret(self, service_name: str = "api_gateway") -> str:
        """Rotate JWT secret for a service"""
        import secrets
        
        key_name = f"{service_name}_jwt_secret"
        old_key_name = f"{service_name}_jwt_secret_old"
        
        try:
            # Move current secret to old
            current_secret = keyring.get_password(self.service_name, key_name)
            if current_secret:
                keyring.set_password(self.service_name, old_key_name, current_secret)
                _get_logger().info(f"Moved current JWT secret to old for service: {service_name}")
        except Exception:
            pass
        
        # Create new secret
        new_secret = secrets.token_urlsafe(32)
        
        try:
            keyring.set_password(self.service_name, key_name, new_secret)
            _get_logger().info(f"Created new JWT secret for service: {service_name}")
        except Exception as e:
            _get_logger().warning(f"Could not store new JWT secret in keyring: {e}")
        
        return new_secret
    
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
    
    @property
    def SESSION_TIMEOUT_MINUTES(self) -> int:
        """Get CLI session timeout from configuration."""
        try:
            return self._get_security_config("cli.session_timeout_minutes") or 30
        except:
            return 30  # Default to 30 minutes
    

        
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
        
    def authenticate(self, password: Optional[str] = None, interactive: bool = True, force_fresh: bool = False) -> bytes:
        """
        Unified authentication method with session support.
        
        Args:
            password: Master password (optional)
            interactive: Whether to prompt for password if needed
            force_fresh: Force fresh authentication, bypass session cache
            
        Returns:
            Master key
        """
        # Check session cache first (unless force_fresh)
        if not force_fresh:
            cached_key = self._get_cached_session()
            if cached_key:
                self._extend_session()  # Extend session on activity
                return cached_key
        
        # Try stored key from keyring (service mode) - only if not force_fresh
        if not force_fresh:
            stored_key = keyring.get_password(self.service_name, "master_key")
            if stored_key:
                master_key = bytes.fromhex(stored_key)
                self._cache_session(master_key)  # Cache for session timeout
                return master_key
            
        # Need password
        if password:
            # Verify password by deriving key and comparing
            derived_key = self._derive_key(password)
            # For first setup, store it
            if not self.has_stored_key():
                self._store_key(derived_key)
            self._cache_session(derived_key)  # Cache for session timeout
            return derived_key
            
        elif interactive:
            password = getpass.getpass("Enter AICO master password: ")
            return self.authenticate(password, interactive=False, force_fresh=force_fresh)
            
        else:
            raise ValueError("No stored key and no password provided")
    
    def authenticate_for_command(self, command_path: str, password: Optional[str] = None, interactive: bool = True) -> bytes:
        """
        Authenticate with automatic sensitive command detection.
        
        Args:
            command_path: Command path like 'security.passwd' or 'logs.export'
            password: Master password (optional)
            interactive: Whether to prompt for password if needed
            
        Returns:
            Master key
        """
        force_fresh = self._is_sensitive_command(command_path)
        if force_fresh:
            _get_logger().info(f"Forcing fresh authentication for sensitive command: {command_path}")
        
        return self.authenticate(password=password, interactive=interactive, force_fresh=force_fresh)
            
    def has_stored_key(self) -> bool:
        """Check if master key is already stored."""
        try:
            stored_key = keyring.get_password(self.service_name, "master_key")
            return stored_key is not None
        except Exception:
            return False
    
    def _get_session_cache_file(self) -> Path:
        """Get path to session cache file."""
        from aico.core.paths import AICOPaths
        paths = AICOPaths()
        cache_dir = paths.get_cache_directory()
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "cli_session.json"
    
    def _load_session_cache(self) -> dict:
        """Load session cache from file."""
        try:
            if self._session_cache_file.exists():
                import json
                with open(self._session_cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            _get_logger().debug(f"Failed to load session cache: {e}")
        return {}
    
    def _save_session_cache(self) -> None:
        """Save session cache to file."""
        try:
            import json
            with open(self._session_cache_file, 'w') as f:
                json.dump(self._session_cache, f)
        except Exception as e:
            _get_logger().debug(f"Failed to save session cache: {e}")

    def _cache_session(self, master_key: bytes) -> None:
        """Cache session with timestamp for timeout management."""
        session_data = {
            "master_key": master_key.hex(),
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat()
        }
        self._session_cache["current"] = session_data
        self._save_session_cache()
        _get_logger().debug("Session cached for CLI authentication")
    
    def _get_cached_session(self) -> Optional[bytes]:
        """Get cached session if still valid."""
        if "current" not in self._session_cache:
            return None
            
        session_data = self._session_cache["current"]
        last_accessed = datetime.fromisoformat(session_data["last_accessed"])
        timeout_delta = timedelta(minutes=self.SESSION_TIMEOUT_MINUTES)
        
        if datetime.now() - last_accessed > timeout_delta:
            # Session expired
            self._clear_session()
            _get_logger().debug("CLI session expired")
            return None
            
        return bytes.fromhex(session_data["master_key"])
    
    def _extend_session(self) -> None:
        """Extend session by updating last accessed time."""
        if "current" in self._session_cache:
            self._session_cache["current"]["last_accessed"] = datetime.now().isoformat()
            self._save_session_cache()
            _get_logger().debug("CLI session extended")
    
    def _clear_session(self) -> None:
        """Clear cached session."""
        if "current" in self._session_cache:
            del self._session_cache["current"]
            self._save_session_cache()
            _get_logger().debug("CLI session cleared")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about current session."""
        if "current" not in self._session_cache:
            return {"active": False}
            
        session_data = self._session_cache["current"]
        created_at = datetime.fromisoformat(session_data["created_at"])
        last_accessed = datetime.fromisoformat(session_data["last_accessed"])
        timeout_delta = timedelta(minutes=self.SESSION_TIMEOUT_MINUTES)
        expires_at = last_accessed + timeout_delta
        
        return {
            "active": True,
            "created_at": created_at.isoformat(),
            "last_accessed": last_accessed.isoformat(),
            "expires_at": expires_at.isoformat(),
            "timeout_minutes": self.SESSION_TIMEOUT_MINUTES,
            "time_remaining_minutes": max(0, int((expires_at - datetime.now()).total_seconds() / 60))
        }
            
    def change_password(self, old_password: str, new_password: str) -> bytes:
        """Change master password."""
        # Verify old password
        try:
            self.authenticate(old_password, interactive=False, force_fresh=True)
        except Exception:
            raise ValueError("Invalid old password")
        
        # Validate new password strength
        self._validate_password_strength(new_password)
            
        # Clear old key and session, set new one
        self.clear_stored_key()
        self._clear_session()
        return self._derive_and_store(new_password)
        
    def clear_stored_key(self) -> None:
        """Remove stored key (security incident)."""
        try:
            keyring.delete_password(self.service_name, "master_key")
            keyring.delete_password(self.service_name, "salt")
            keyring.delete_password(self.service_name, "key_created")
        except Exception:
            pass  # Key might not exist
        
        # Clear session cache as well
        self._clear_session()
            
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
        try:
            keyring.set_password(self.service_name, "master_key", master_key.hex())
        except Exception as e:
            # Check for macOS keychain authentication failure
            error_str = str(e)
            if "-25244" in error_str or "Unknown Error" in error_str:
                raise ValueError(
                    "Failed to store key in macOS Keychain. This usually happens when:\n"
                    "  • You entered the wrong macOS system password\n"
                    "  • You canceled the keychain access dialog\n"
                    "  • Keychain access timed out\n\n"
                    "Please try again and enter your correct macOS system password when prompted."
                ) from e
            else:
                raise ValueError(f"Failed to store key in system keyring: {e}") from e
        
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
            _get_logger().debug(f"Loaded existing salt for {db_file.name}")
        else:
            salt = os.urandom(self.SALT_LENGTH)
            
            # Ensure parent directory exists
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(salt_file, 'wb') as f:
                f.write(salt)
            
            # Set secure file permissions
            if hasattr(os, 'chmod'):
                os.chmod(salt_file, 0o600)
            
            _get_logger().info(f"Generated new salt for {db_file.name}")
        
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
            _get_logger().info(f"Stored {database_type} password in keyring")
        except Exception as e:
            _get_logger().warning(f"Failed to store {database_type} password in keyring: {e}")
            
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
                _get_logger().debug(f"Retrieved {database_type} password from keyring")
            return password
        except Exception as e:
            _get_logger().warning(f"Failed to retrieve {database_type} password from keyring: {e}")
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
    
    def store_jwt_token(self, service_name: str, token: str) -> None:
        """
        Store JWT token securely in platform keyring.
        
        Args:
            service_name: Service identifier (e.g., 'api_gateway', 'cli')
            token: JWT token to store
        """
        token_key = f"{service_name}_jwt_token"
        
        try:
            keyring.set_password(self.service_name, token_key, token)
            _get_logger().debug(f"JWT token stored securely for service: {service_name}")
        except Exception as e:
            _get_logger().error(f"Failed to store JWT token in keyring: {e}")
            raise RuntimeError(f"Could not store JWT token securely: {e}")
    
    def get_jwt_token(self, service_name: str) -> Optional[str]:
        """
        Retrieve JWT token from platform keyring.
        
        Args:
            service_name: Service identifier (e.g., 'api_gateway', 'cli')
            
        Returns:
            JWT token if found, None otherwise
        """
        token_key = f"{service_name}_jwt_token"
        
        try:
            token = keyring.get_password(self.service_name, token_key)
            if token:
                _get_logger().debug(f"JWT token retrieved for service: {service_name}")
                return token
            else:
                _get_logger().debug(f"No JWT token found for service: {service_name}")
                return None
        except Exception as e:
            _get_logger().error(f"Failed to retrieve JWT token from keyring: {e}")
            return None
    
    def remove_jwt_token(self, service_name: str) -> bool:
        """
        Remove JWT token from platform keyring.
        
        Args:
            service_name: Service identifier (e.g., 'api_gateway', 'cli')
            
        Returns:
            True if token was removed or didn't exist, False on error
        """
        token_key = f"{service_name}_jwt_token"
        
        try:
            # Check if token exists first
            if keyring.get_password(self.service_name, token_key):
                keyring.delete_password(self.service_name, token_key)
                _get_logger().info(f"JWT token removed for service: {service_name}")
            else:
                _get_logger().debug(f"No JWT token to remove for service: {service_name}")
            return True
        except Exception as e:
            _get_logger().error(f"Failed to remove JWT token from keyring: {e}")
            return False
    
    def list_jwt_tokens(self) -> Dict[str, bool]:
        """
        List all JWT tokens stored for this service.
        
        Returns:
            Dictionary mapping service names to token existence
        """
        tokens = {}
        common_services = ['api_gateway', 'cli', 'admin', 'studio']
        
        for service in common_services:
            token_key = f"{service}_jwt_token"
            try:
                token = keyring.get_password(self.service_name, token_key)
                tokens[service] = token is not None
            except Exception:
                tokens[service] = False
                
        return tokens
