---
title: Data Security
---

# Data Security

This document details AICO's data security architecture, focusing specifically on protecting user data both at rest and in transit.

## Data Security Overview

AICO implements a privacy-first data security model with multiple layers of protection:

```mermaid
flowchart TD
    A[User Data] --> B[Database Encryption]
    A --> C[Application-level Encryption]
    B --> D[Key Management]
    C --> D
    D --> E[Data Access Control]
    
    classDef security fill:#663399,stroke:#9370DB,color:#fff
    class A,B,C,D,E security
```

## Data at Rest Security

### Encryption Strategy

> **ℹ️ Note on Filesystem-Level Encryption**
> 
> Traditional filesystem-level encryption solutions (gocryptfs, securefs, EncFS) face significant challenges in multi-platform environments:
> - **Platform Limitations**: Most solutions lack reliable macOS/Windows support or require complex manual builds
> - **Database Compatibility**: FUSE-based encryption can cause file locking issues and performance degradation with databases
> - **Dependency Management**: Requires platform-specific FUSE implementations (macFUSE, WinFsp) with varying stability
> 
> AICO addresses these challenges with a modern application-level encryption approach.

AICO employs a hybrid application-level encryption strategy that provides robust, cross-platform data protection without filesystem dependencies:

#### Database-Native Encryption

Each database uses its optimal encryption method for maximum performance and reliability:

- **libSQL**: SQLCipher-style encryption via PRAGMA statements with PBKDF2 key derivation
- **DuckDB**: Built-in AES-256 encryption via PRAGMA statements
- **LMDB**: Native EncryptedEnv for transparent key-value encryption
- **ChromaDB**: Custom file-level encryption wrapper

**Implementation Example**:
```python
# LibSQL with encryption
from aico.data.libsql import EncryptedLibSQLConnection

# Create encrypted database connection
conn = EncryptedLibSQLConnection(
    db_path="data/aico.db",
    master_password="user_master_password",
    store_in_keyring=True  # Secure password storage
)

# Use with context manager for automatic cleanup
with conn:
    # All operations are automatically encrypted
    conn.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO users VALUES (?, ?)", (1, "Alice"))
    
    # Query encrypted data
    users = conn.fetch_all("SELECT * FROM users")
    print(users)  # [{'id': 1, 'name': 'Alice'}]

# Key derivation and encryption details:
# - PBKDF2-SHA256 with 100,000 iterations
# - 256-bit encryption key (32 bytes)
# - 128-bit salt (16 bytes)
# - SQLCipher-style PRAGMA key encryption
# - System keyring integration for password storage

# AICO uses a single encrypted LibSQL database
# All data is stored in the main aico.db file

# Generic File Encryption

For files without native encryption support, AICO provides a transparent encryption wrapper:

```python
from aico.security import EncryptedFile

# Drop-in replacement for open()
with EncryptedFile("data/sensitive_data.enc", "wb", key_manager=km) as f:
    f.write(data)  # Automatically encrypted

with EncryptedFile("data/sensitive_data.enc", "rb", key_manager=km) as f:
    data = f.read()  # Automatically decrypted and audited
```

### LibSQL Encryption Implementation

AICO's LibSQL encryption implementation provides transparent, secure database encryption using industry-standard cryptographic practices:

#### Architecture Overview

```mermaid
flowchart TD
    A[Master Password] --> B[PBKDF2-SHA256]
    C[Random Salt] --> B
    B --> D[256-bit Encryption Key]
    D --> E[PRAGMA key]
    E --> F[Encrypted LibSQL Database]
    
    G[System Keyring] --> A
    H[Salt File] --> C
    
    classDef security fill:#663399,stroke:#9370DB,color:#fff
    class A,B,C,D,E,F,G,H security
```

#### Security Specifications

| Component | Specification | Details |
|-----------|---------------|----------|
| **Key Derivation** | PBKDF2-SHA256 | 100,000 iterations, cryptographically secure |
| **Encryption Key** | 256-bit AES | 32-byte key for maximum security |
| **Salt** | 128-bit random | 16-byte salt, unique per database |
| **Database Encryption** | SQLCipher-style | PRAGMA key with hex-encoded key |
| **Password Storage** | System Keyring | Platform-native secure storage |
| **Salt Storage** | Restricted file | 0o600 permissions, separate from database |

#### Implementation Details

**Key Derivation Process:**
```python
# PBKDF2 key derivation with secure parameters
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,  # 256-bit key
    salt=salt,  # 128-bit random salt
    iterations=100000,  # Resistant to brute force
    backend=default_backend()
)
key = kdf.derive(password.encode('utf-8'))
```

**Database Encryption:**
```python
# SQLCipher-style encryption via PRAGMA
connection.execute(f"PRAGMA key = 'x\"{key.hex()}\"'")
```

**Security Features:**
- ✅ **Transparent encryption**: All database operations automatically encrypted
- ✅ **Key verification**: Automatic validation that encryption key is correct
- ✅ **Secure storage**: Master passwords stored in system keyring
- ✅ **Salt management**: Unique salt per database, securely stored
- ✅ **File permissions**: Restrictive permissions on salt files (0o600)
- ✅ **Error handling**: Comprehensive error handling for encryption failures

**Usage Patterns:**
```python
# Simple encrypted database
conn = EncryptedLibSQLConnection("data/aico.db", master_password="secret")

# With keyring storage
conn = EncryptedLibSQLConnection("data/aico.db", store_in_keyring=True)

# Verify encryption is working
if conn.verify_encryption():
    print("Database is properly encrypted")
```

**File Structure:**
```
data/
├── aico.db        # Encrypted LibSQL database
├── aico.db.salt   # Salt file (0o600 permissions)
└── ...
```

#### Directory Structure

AICO maintains organized encrypted storage with clear separation:

```
data/
├── aico.db              # Single encrypted LibSQL database
├── aico.db.salt         # Salt file for encryption
└── logs/                # Log files (if separate from database)
```

#### Advantages of Application-Level Encryption

1. **Zero Functionality Restrictions**:
   - Databases operate with full feature sets and native performance
   - No need to modify database code or implement application-level encryption
   - All database features work without modification

2. **Unified Security Model**:
   - Single encryption layer protects all databases consistently
   - Simplifies security auditing and compliance
   - Reduces risk of implementation errors in database-specific encryption

3. **Cross-Platform Support**:
   - Works on all platforms with "Full" backend support
   - Compatible with all backend deployment targets (Linux, macOS, Windows via FUSE)

4. **Performance Efficiency**:
   - Minimal overhead compared to application-level encryption
   - Efficient for both high-performance desktops and resource-constrained devices
   - Avoids double encryption overhead

### Key Management

AICO implements a unified key management approach for application-level encryption, using appropriate key derivation functions for different use cases:

#### Key Derivation Functions

AICO uses different key derivation functions optimized for specific use cases:

**PBKDF2-SHA256 for Database Encryption:**
- Used in LibSQL encrypted connections
- 100,000 iterations for balance of security and performance
- Widely supported and battle-tested
- Suitable for database encryption scenarios

**Argon2id for General Authentication:**
- Used for master key derivation and user authentication
- Memory-hard function resistant to GPU attacks
- Configurable memory, time, and parallelism parameters
- Recommended by security experts for password hashing

```python
```python
from aico.security.key_manager import AICOKeyManager

# Key management is handled by existing AICOKeyManager
key_manager = AICOKeyManager()
master_key = key_manager.get_or_create_master_key()

# Derive keys for the single AICO database
db_key = key_manager.derive_key(master_key, "database", "aico")
file_key = key_manager.derive_key(master_key, "file", "config")
```
```

#### Key Management Process

```python
# Unified key management via existing AICOKeyManager
from aico.security.key_manager import AICOKeyManager

key_manager = AICOKeyManager()
master_key = key_manager.get_or_create_master_key()

# Database encryption
conn = EncryptedLibSQLConnection(
    "data/aico.db",
    key_manager=key_manager
)
```

#### Security Properties

1. **Master Password**: User-provided master password is the root of trust
   - Never stored, only used transiently during key derivation
   - Cleared from memory immediately after use

## Schema Management Security

AICO's in-code schema management system is designed with security-first principles to protect both schema integrity and user data during database evolution.

### Security Architecture

```mermaid
flowchart TD
    A[Schema Definitions] --> B[Code Signing]
    B --> C[Runtime Validation]
    C --> D[Encrypted Database]
    
    E[Migration History] --> F[Checksum Validation]
    F --> G[Tamper Detection]
    
    H[Plugin Schemas] --> I[Sandbox Isolation]
    I --> J[Permission Boundaries]
    
    K[Schema Metadata] --> L[Encryption at Rest]
    L --> M[Access Control]
    
    classDef security fill:#dc2626,stroke:#b91c1c,color:#fff
    classDef data fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef plugin fill:#059669,stroke:#047857,color:#fff
    
    class B,C,F,G,L,M security
    class A,D,E,K data
    class H,I,J plugin
```

### Threat Model

#### Protected Against
1. **Schema Tampering**: Unauthorized modification of database structure
2. **Migration Replay**: Malicious re-execution of previous migrations
3. **Plugin Schema Conflicts**: Plugins interfering with core or other plugin data
4. **Data Exposure**: Schema operations revealing sensitive user information
5. **Rollback Attacks**: Malicious downgrades to vulnerable schema versions

#### Security Controls

##### 1. Schema Definition Protection
```python
# Schema definitions with integrity validation
from aico.data.schema import SchemaManager

schema_manager = SchemaManager(connection)
schema_manager.validate_and_apply_migrations()
```

##### 2. Migration History Protection
```python
# Migration tracking with tamper detection
from aico.data.schema import MigrationTracker

tracker = MigrationTracker(connection)
tracker.apply_migration_if_needed(version, migration_sql)
```

##### 3. Plugin Schema Isolation
```python
# Plugin schema isolation
from aico.plugins.schema import PluginSchemaManager

plugin_schema = PluginSchemaManager(connection, plugin_name)
plugin_schema.create_isolated_tables(schema_definitions)
```

### Encryption Integration

#### Schema Metadata Encryption
```python
# Schema metadata encryption
from aico.data.schema import EncryptedSchemaManager

schema_manager = EncryptedSchemaManager(encrypted_connection)
schema_manager.store_metadata(key, value)  # Automatically encrypted
```

#### Key Derivation for Schema Operations
```python
# Schema operations use same encryption as user data
class SecureSchemaOperations:
    def __init__(self, master_password: str):
        self.connection = EncryptedLibSQLConnection(
            db_path="data/aico.db",
            master_password=master_password  # Same key as user data
        )
    
    def apply_schema_migration(self, schema_definitions):
        """Apply schema migration with full encryption"""
        # All schema operations encrypted with user's master key
        schema_manager = EncryptedSchemaManager(
            self.connection, 
            schema_definitions
        )
        schema_manager.migrate_to_latest()
```

### Access Control

#### Local-Only Operations
```python
# Local-only schema operations
from aico.data.schema import LocalSchemaManager

schema_manager = LocalSchemaManager(connection)
schema_manager.migrate_to_latest()  # Network access blocked
```

#### Permission Boundaries
```python
# Permission-aware schema operations
from aico.data.schema import PermissionAwareSchemaManager

schema_manager = PermissionAwareSchemaManager(connection, context='core')
schema_manager.validate_and_execute(sql_statement)
```

### Security Best Practices

#### Development Guidelines
1. **Schema Review**: All schema changes must be reviewed for security implications
2. **Minimal Permissions**: Grant only necessary database permissions to each component
3. **Rollback Testing**: Verify rollback operations don't expose sensitive data
4. **Checksum Validation**: Always validate schema integrity before applying changes
5. **Audit Logging**: Log all schema operations for security monitoring

#### Operational Security
1. **Backup Before Migration**: Always backup database before schema changes
2. **Test Migrations**: Test schema changes in isolated environments first
3. **Monitor Integrity**: Regularly verify schema integrity and detect tampering
4. **Plugin Vetting**: Review plugin schemas before installation
5. **Access Logging**: Log all schema access for security auditing

#### Incident Response
```python
# Schema security monitoring
from aico.data.schema import SchemaSecurityMonitor

monitor = SchemaSecurityMonitor(connection)
if monitor.detect_tampering():
    logger.critical("Schema tampering detected")
    monitor.lock_database_access()
```

### Compliance Considerations

#### Data Protection
- **GDPR Compliance**: Schema operations respect user data protection rights
- **Data Minimization**: Schema definitions contain no personal data
- **Right to Erasure**: Schema rollback can remove user data when required
- **Data Portability**: Schema versioning supports data export/import

#### Security Standards
- **Defense in Depth**: Multiple security layers protect schema integrity
- **Principle of Least Privilege**: Minimal permissions for schema operations
- **Secure by Default**: Schema management defaults to most secure configuration
- **Audit Trail**: Complete audit trail for all schema modifications

2. **Key Derivation**: Argon2id key derivation with context-specific parameters
   - Master key: 1GB memory, 3 iterations, 4 threads
   - File encryption: 256MB memory, 2 iterations, 2 threads
   - Authentication: 64MB memory, 1 iteration, 1 thread

3. **Secure Storage**: Derived keys securely stored using platform-specific mechanisms:
   - macOS: Keychain
   - Windows: Windows Credential Manager
   - Linux: Secret Service API / GNOME Keyring
   - Mobile: Secure Enclave (iOS) / Keystore (Android)

4. **Persistent Service Authentication**: Backend services restart without user interaction
   - Master key retrieved from secure storage on service startup
   - No password re-entry required for non-technical users
   - Maintains security through OS-level protection

5. **Biometric Unlock**: Optional biometric authentication for accessing the encryption key
   - Integrates with platform biometric APIs
   - Falls back to master password when biometrics unavailable

6. **Automatic Mounting**: Zero-effort security with automatic mounting during application startup
   - Retrieves keys from secure storage
   - Mounts encrypted filesystem transparently

For complete details on the overall key management system, see the Security Overview documentation.

## Data Synchronization Security

When data is synchronized between devices during roaming:

1. **Selective Sync Encryption**:
   - End-to-end encrypted data transfer between trusted devices
   - Encrypted database snapshots for initial synchronization
   - Incremental encrypted updates for ongoing synchronization

2. **Sync Protocol Security**:
   - Authenticated and encrypted channels for all data transfers
   - Cryptographic verification of data integrity during sync
   - Version vectors for conflict detection and resolution

## Data Access Control

AICO implements fine-grained data access controls:

1. **Data Classification**:
   - **Personal Data**: User conversations, preferences, and personal information
   - **System Data**: Configuration, logs, and operational data
   - **Derived Data**: AI-generated insights and analytics

2. **Data Access Policies**:
   - Module-specific data access permissions
   - Explicit data access logging for all sensitive operations
   - Data minimization principles applied to all access requests

## Data Privacy Features

1. **Data Minimization**:
   - Only essential data is collected and stored
   - Automatic data pruning based on relevance and age
   - Privacy-preserving analytics with differential privacy techniques

2. **User Data Control**:
   - Data export functionality for all user data
   - Selective data deletion capabilities
   - Transparency tools showing what data is stored and how it's used

## Data Security for Roaming Scenarios

AICO's data security adapts to different roaming patterns, maintaining security while supporting both coupled and detached deployment models:

1. **Coupled Roaming Security**:
   - Complete encrypted data directory moves with the application
   - Database files remain encrypted using native encryption methods
   - Master key securely synchronized via platform-specific secure storage
   - Zero-effort security maintained across device transitions

2. **Detached Roaming Security**:
   - Backend maintains encrypted databases using application-level encryption
   - Frontend accesses data via secure API with end-to-end encryption
   - Mutual TLS authentication between frontend and backend
   - Secure WebSocket or gRPC channels with forward secrecy
   - Lightweight frontend devices operate without needing local encryption capabilities
