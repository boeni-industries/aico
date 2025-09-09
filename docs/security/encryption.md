---
title: File Encryption
---

# File Encryption

This document describes AICO's transparent file encryption system for files without native encryption support (configs, logs, ChromaDB files, etc.).

## Overview

AICO provides a transparent file encryption wrapper class `EncryptedFile` that serves as a drop-in replacement for Python's `open()` function. This enables encryption of arbitrary files while maintaining the familiar file I/O API.

**Current Status**: ✅ Implemented and operational in the codebase with AES-256-GCM encryption.

## Architecture

### Design Principles

**Zero-Effort Security**
- Automatic key derivation using existing `AICOKeyManager`
- Transparent encryption/decryption during file operations
- No user intervention required for key management

**Cross-Platform Compatibility**
- Pure Python implementation using `cryptography` library
- Works reliably on Windows, macOS, and Linux
- No platform-specific dependencies or FUSE requirements

**Performance Optimized**
- Streaming encryption for large files (GB+)
- Configurable chunk sizes for memory efficiency
- Hardware-accelerated AES-GCM when available

### Encryption Specifications

| Component | Specification | Details |
|-----------|---------------|---------|
| **Algorithm** | AES-256-GCM | Authenticated encryption with 256-bit keys |
| **Key Derivation** | Argon2id | File-specific keys derived from master key |
| **Nonce** | 96-bit random | Unique per file encryption |
| **Authentication Tag** | 128-bit | Prevents tampering and corruption |
| **Salt** | 128-bit random | Unique per file, prevents rainbow tables |

### File Format

```
┌─────────────┬──────────────┬──────────────┬─────────────────┬──────────────┐
│   Header    │     Salt     │    Nonce     │ Encrypted Data  │   Auth Tag   │
│   4 bytes   │   16 bytes   │   12 bytes   │   Variable      │   16 bytes   │
└─────────────┴──────────────┴──────────────┴─────────────────┴──────────────┘
```

**Header Format**: `AICO` (4 ASCII bytes) - identifies AICO encrypted files

## Implementation

### Basic Usage

```python
from aico.security import EncryptedFile
from aico.security.key_manager import AICOKeyManager

# Initialize key manager
key_manager = AICOKeyManager()

# Write encrypted file
with EncryptedFile("config.enc", "w", key_manager=key_manager, purpose="config") as f:
    f.write("sensitive configuration data")

# Read encrypted file
with EncryptedFile("config.enc", "r", key_manager=key_manager, purpose="config") as f:
    data = f.read()
```

**Note**: This implementation is currently active in the AICO codebase and used for encrypting configuration files and other sensitive data.

### Advanced Usage

```python
# Binary mode support
with EncryptedFile("data.enc", "wb", key_manager=km, purpose="logs") as f:
    f.write(binary_data)

# Streaming for large files
with EncryptedFile("large.enc", "rb", key_manager=km, purpose="backup") as f:
    while chunk := f.read(8192):  # 8KB chunks
        process_chunk(chunk)

# Custom chunk size for performance tuning
with EncryptedFile("video.enc", "wb", key_manager=km, purpose="media", 
                   chunk_size=1024*1024) as f:  # 1MB chunks
    f.write(large_binary_data)
```

### Supported File Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `"r"` | Text read | Configuration files, logs |
| `"w"` | Text write | Configuration files, logs |
| `"rb"` | Binary read | ChromaDB files, media |
| `"wb"` | Binary write | ChromaDB files, media |
| `"a"` | Text append | Log files |
| `"ab"` | Binary append | Binary log files |

## Key Management Integration

### Key Derivation Process

```python
# File-specific key derivation
file_key = key_manager.derive_file_encryption_key(
    master_key=master_key,
    file_purpose=purpose  # e.g., "config", "logs", "chroma"
)
```

**Key Derivation Parameters** (from `security.yaml`):
- **Memory Cost**: 128MB (configurable)
- **Iterations**: 1 (optimized for file operations)
- **Parallelism**: 2 threads
- **Context**: `master_key + "aico-file-{purpose}"`

### Purpose-Based Keys

Different file purposes use different derived keys:

```python
# Configuration files
EncryptedFile("app.conf", "w", key_manager=km, purpose="config")

# Log files  
EncryptedFile("debug.log", "w", key_manager=km, purpose="logs")

# ChromaDB files
EncryptedFile("vectors.db", "wb", key_manager=km, purpose="chroma")

# Plugin data
EncryptedFile("plugin.dat", "wb", key_manager=km, purpose="plugin_name")
```

## Configuration

### Security Configuration

File encryption parameters are configured in `config/defaults/security.yaml`:

```yaml
security:
  encryption:
    file_encryption:
      chunk_size: 65536        # 64KB chunks for streaming
      buffer_size: 1048576     # 1MB read buffer
      nonce_size: 12           # 96-bit nonce for GCM
      tag_size: 16             # 128-bit auth tag
      header_magic: "AICO"     # File format identifier
      
    key_derivation:
      argon2id:
        file_operations: 1     # Iterations for file encryption
        memory_cost:
          file_operations: 131072  # 128MB in KiB
        lanes:
          file_operations: 2   # 2 parallel threads
```

### Performance Tuning

**Chunk Size Guidelines**:
- **Small files (<1MB)**: 8KB-16KB chunks
- **Medium files (1-100MB)**: 64KB chunks (default)
- **Large files (>100MB)**: 1MB chunks
- **Network storage**: Larger chunks (2-4MB)

**Memory Usage**:
- Base overhead: ~1MB regardless of file size
- Additional: 2x chunk_size for buffering
- Total: ~1MB + (2 × chunk_size)

## Security Features

### Threat Protection

| Threat | Protection | Implementation |
|--------|------------|----------------|
| **Data Theft** | AES-256 encryption | Industry-standard symmetric encryption |
| **Tampering** | GCM authentication | 128-bit authentication tag |
| **Rainbow Tables** | Unique salt per file | 128-bit random salt |
| **Replay Attacks** | Unique nonce per encryption | 96-bit random nonce |
| **Key Compromise** | Key rotation support | Master key rotation cascades to file keys |

### Cryptographic Properties

**Confidentiality**: AES-256 provides 2^256 key space
**Authenticity**: GCM mode provides built-in authentication
**Integrity**: Authentication tag detects any modifications
**Forward Secrecy**: Key rotation invalidates old encrypted files

### Security Validation

```python
# Verify file encryption
encrypted_file = EncryptedFile("test.enc", "r", key_manager=km, purpose="test")
is_encrypted = encrypted_file.verify_encryption()

# Get encryption information
info = encrypted_file.get_encryption_info()
print(f"Algorithm: {info['algorithm']}")
print(f"Key size: {info['key_size']} bits")
print(f"File size: {info['file_size']} bytes")
```

## Error Handling

### Common Errors

```python
from aico.security.exceptions import (
    EncryptionError,
    DecryptionError, 
    InvalidKeyError,
    CorruptedFileError
)

try:
    with EncryptedFile("data.enc", "r", key_manager=km, purpose="test") as f:
        data = f.read()
except InvalidKeyError:
    print("Wrong encryption key or corrupted key data")
except CorruptedFileError:
    print("File has been tampered with or corrupted")
except EncryptionError as e:
    print(f"Encryption failed: {e}")
```

### Error Recovery

**Invalid Key**: 
- Verify master password is correct
- Check file purpose matches original encryption
- Ensure key manager is properly initialized

**Corrupted File**:
- Authentication tag mismatch indicates tampering
- File may be partially written or corrupted
- No recovery possible - restore from backup

**Performance Issues**:
- Adjust chunk_size for your use case
- Monitor memory usage with large files
- Consider async I/O for concurrent operations

## Use Cases

### Configuration Files

```python
# Encrypt sensitive configuration
with EncryptedFile("database.conf", "w", key_manager=km, purpose="config") as f:
    f.write(f"password={sensitive_password}\n")
    f.write(f"api_key={secret_key}\n")
```

### Log Files

```python
# Encrypt logs containing user data
with EncryptedFile("user_activity.log", "a", key_manager=km, purpose="logs") as f:
    f.write(f"{timestamp}: User {user_id} performed {action}\n")
```

### ChromaDB Files

```python
# Encrypt vector database files
def encrypt_chroma_file(source_path, encrypted_path):
    with open(source_path, "rb") as src:
        with EncryptedFile(encrypted_path, "wb", key_manager=km, purpose="chroma") as dst:
            while chunk := src.read(1024*1024):  # 1MB chunks
                dst.write(chunk)
```

### Plugin Data

```python
# Plugin-specific encrypted storage
class MyPlugin:
    def save_data(self, data):
        purpose = f"plugin_{self.plugin_name}"
        with EncryptedFile("plugin.dat", "wb", key_manager=km, purpose=purpose) as f:
            f.write(pickle.dumps(data))
```

## Performance Characteristics

### Benchmarks

**Small Files** (<1MB):
- Encryption overhead: 10-50ms
- Memory usage: ~1MB base + file size
- CPU impact: Minimal (hardware AES acceleration)

**Large Files** (1GB+):
- Throughput: ~80-90% of unencrypted I/O
- Memory usage: Constant ~2MB (streaming)
- CPU impact: 5-15% depending on hardware

**Streaming Performance**:
- Chunk processing: ~500MB/s on modern hardware
- Memory efficiency: O(1) regardless of file size
- Concurrent operations: Supported with separate EncryptedFile instances

### Optimization Tips

1. **Choose appropriate chunk size** for your use case
2. **Use binary mode** (`rb`/`wb`) for better performance
3. **Batch small files** rather than encrypting individually
4. **Monitor memory usage** with very large files
5. **Consider async I/O** for concurrent file operations

## Integration with AICO

### Unified Logging

```python
# Automatic logging of encryption operations
with EncryptedFile("data.enc", "w", key_manager=km, purpose="logs") as f:
    f.write("sensitive data")
# Logs: "File encrypted: data.enc (purpose: logs, size: 14 bytes)"
```

### Configuration-Driven Security

All encryption parameters are configurable via AICO's configuration system:

```python
# Parameters automatically loaded from security.yaml
encrypted_file = EncryptedFile("data.enc", "w", key_manager=km, purpose="config")
# Uses chunk_size, buffer_size, etc. from configuration
```

### Zero-Effort Security

```python
# Automatic key retrieval from AICOKeyManager
key_manager = AICOKeyManager()  # Automatically loads stored keys
with EncryptedFile("data.enc", "w", key_manager=key_manager, purpose="config") as f:
    f.write("data")  # Encryption happens transparently
```

## Migration and Compatibility

### Migrating Existing Files

```python
def encrypt_existing_file(plain_path, encrypted_path, purpose, key_manager):
    """Migrate plaintext file to encrypted format."""
    with open(plain_path, "rb") as src:
        with EncryptedFile(encrypted_path, "wb", key_manager=key_manager, purpose=purpose) as dst:
            while chunk := src.read(64*1024):
                dst.write(chunk)
    
    # Optionally remove plaintext file
    os.remove(plain_path)
```

### Batch Migration

```python
def migrate_directory(source_dir, target_dir, purpose, key_manager):
    """Migrate entire directory to encrypted format."""
    for file_path in Path(source_dir).rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(source_dir)
            encrypted_path = Path(target_dir) / f"{relative_path}.enc"
            encrypted_path.parent.mkdir(parents=True, exist_ok=True)
            encrypt_existing_file(file_path, encrypted_path, purpose, key_manager)
```

### Version Compatibility

The file format includes a header that enables future format evolution:

```python
# Current format: "AICO" + version info
# Future formats can be detected and handled appropriately
```

## Best Practices

### Security Best Practices

1. **Use unique purposes** for different file types
2. **Rotate master keys** periodically (annually recommended)
3. **Monitor file integrity** with regular verification
4. **Backup encrypted files** - keys can be regenerated from master password
5. **Use secure deletion** for temporary plaintext files

### Performance Best Practices

1. **Profile your use case** to determine optimal chunk size
2. **Use streaming** for files larger than available RAM
3. **Batch operations** when encrypting many small files
4. **Monitor memory usage** in production environments
5. **Consider async I/O** for high-throughput scenarios

### Integration Best Practices

1. **Consistent purpose naming** across your application
2. **Centralized key manager** - don't create multiple instances
3. **Proper error handling** for all encryption operations
4. **Logging integration** for security audit trails
5. **Configuration management** for encryption parameters

## Troubleshooting

### Common Issues

**"Invalid key" errors**:
- Verify master password is correct
- Check that file purpose matches original encryption
- Ensure AICOKeyManager is properly initialized

**Performance issues**:
- Adjust chunk_size in configuration
- Monitor memory usage with large files
- Check for hardware AES acceleration

**File corruption**:
- Authentication tag verification failed
- File may be partially written or damaged
- Restore from backup - no recovery possible

**Memory issues**:
- Reduce chunk_size for memory-constrained environments
- Use streaming mode for large files
- Monitor memory usage in production

### Debugging

```python
# Enable debug logging
import logging
logging.getLogger("aico.security.encrypted_file").setLevel(logging.DEBUG)

# Verify encryption status
with EncryptedFile("test.enc", "r", key_manager=km, purpose="debug") as f:
    info = f.get_encryption_info()
    print(f"Encryption verified: {info}")
```

### Support

For additional support:
1. Check AICO security documentation
2. Review configuration in `security.yaml`
3. Enable debug logging for detailed error information
4. Verify key manager setup and master password
