# AICO Backup & Restore Strategy

**Status:** Work in Progress  
**Priority:** High (Critical for data safety and encryption migration)  
**Related:** `docs/research/encryption-solutions.md`, `WIP_encryption_analysis.md`

---

## Overview

AICO requires a comprehensive backup and restore system to:
1. Protect user data against loss
2. Enable safe encryption migration (plaintext → encrypted)
3. Support device roaming and federation
4. Facilitate disaster recovery
5. Enable version rollback if needed

---

## Current Data Landscape

### Databases to Backup

#### 1. **libSQL** (Encrypted)
- **Location:** `~/.local/share/aico/data/aico.db` + `.salt`
- **Size:** Variable (grows with logs, user data)
- **Content:** 
  - User accounts and authentication
  - Logs and system events
  - Scheduled tasks
  - Configuration overrides
- **Encryption:** ✅ AES-256 via SQLCipher

#### 2. **ChromaDB** (Currently Plaintext)
- **Location:** `~/.local/share/aico/data/memory/semantic/`
- **Size:** Large (grows with conversations)
- **Content:**
  - Conversation segments
  - Vector embeddings (768-dim)
  - User facts and knowledge
  - Semantic memory
- **Encryption:** ❌ Plaintext (needs migration)

#### 3. **LMDB** (Currently Plaintext)
- **Location:** `~/.local/share/aico/data/memory/working/`
- **Size:** Small (24-hour TTL)
- **Content:**
  - Active conversation context
  - Recent message history
  - Session state
- **Encryption:** ❌ Plaintext (needs migration)

#### 4. **RocksDB** (Currently Plaintext)
- **Location:** `~/.local/share/aico/data/memory/working/` (if used)
- **Size:** Variable
- **Content:** Working memory (alternative to LMDB)
- **Encryption:** ❌ Plaintext (needs migration)

#### 5. **Configuration Files**
- **Location:** `~/.local/share/aico/config/`
- **Size:** Small (<1MB)
- **Content:**
  - `runtime.yaml`
  - User preferences
  - Model configurations
- **Encryption:** ❌ Plaintext (low priority)

---

## Backup Strategy

### Backup Types

#### 1. **Full Backup**
- Complete snapshot of all databases and configuration
- Includes encryption keys (securely)
- Suitable for disaster recovery
- Frequency: Weekly or on-demand

#### 2. **Incremental Backup**
- Only changed data since last backup
- Faster and smaller
- Requires full backup as base
- Frequency: Daily

#### 3. **Differential Backup**
- All changes since last full backup
- Balance between full and incremental
- Easier restore than incremental
- Frequency: Daily

### Backup Scope

#### Essential (Always Backup)
- ✅ libSQL database + salt file
- ✅ ChromaDB directory (semantic memory)
- ✅ LMDB/RocksDB (working memory)
- ✅ Encryption keys (from platform keyring)
- ✅ Configuration files

#### Optional (User Choice)
- ⚠️ Model files (can be re-downloaded)
- ⚠️ Cache files (can be regenerated)
- ⚠️ Temporary files (not needed)

---

## Encryption Migration Strategy

### Problem
ChromaDB and LMDB are currently plaintext. Need to migrate to encrypted storage without data loss.

### Solution Options

#### Option A: Filesystem-Level Encryption (RECOMMENDED)
**Approach:** Migrate data to gocryptfs/cppcryptfs encrypted filesystem

**Migration Steps:**
1. Create full backup of current data
2. Initialize encrypted filesystem (gocryptfs/cppcryptfs)
3. Stop AICO backend
4. Copy all data to encrypted filesystem
5. Update AICO configuration to use encrypted paths
6. Start AICO backend
7. Verify data integrity
8. Securely delete plaintext data

**Pros:**
- Zero code changes
- All databases encrypted automatically
- Transparent operation
- Reversible (can restore from backup)

**Cons:**
- Requires user password on mount
- Platform-specific tools (gocryptfs vs cppcryptfs)

#### Option B: Database-by-Database Migration
**Approach:** Migrate each database to encrypted alternative

**Migration Steps:**
1. Backup current data
2. For ChromaDB: Export → Encrypt → Import to new instance
3. For LMDB: Export → Encrypt → Import to redbx or encrypted alternative
4. Update AICO code to use new databases
5. Verify data integrity
6. Delete plaintext data

**Pros:**
- Native encryption support
- No filesystem dependencies

**Cons:**
- High code complexity
- Requires database-specific migration tools
- Risk of data loss during migration

### Recommended: Option A (Filesystem-Level)
Aligns with `docs/research/encryption-solutions.md` recommendation.

---

## Backup Format

### Archive Structure
```
aico-backup-YYYYMMDD-HHMMSS.tar.gz.enc
├── metadata.json              # Backup metadata
├── encryption_key.enc         # Encrypted master key
├── databases/
│   ├── aico.db               # libSQL database
│   ├── aico.db.salt          # libSQL salt
│   ├── semantic/             # ChromaDB directory
│   └── working/              # LMDB/RocksDB directory
└── config/
    ├── runtime.yaml
    └── user_preferences.json
```

### Metadata Format
```json
{
  "backup_version": "1.0",
  "aico_version": "0.1.0",
  "timestamp": "2025-10-17T12:30:00Z",
  "backup_type": "full",
  "encryption": {
    "enabled": true,
    "algorithm": "AES-256-GCM",
    "key_derivation": "PBKDF2-SHA256"
  },
  "databases": {
    "libsql": {
      "size_bytes": 10485760,
      "encrypted": true
    },
    "chromadb": {
      "size_bytes": 52428800,
      "encrypted": false,
      "collections": ["conversations", "user_facts"]
    },
    "lmdb": {
      "size_bytes": 1048576,
      "encrypted": false
    }
  },
  "platform": "darwin",
  "checksum": "sha256:abc123..."
}
```

---

## Restore Strategy

### Pre-Restore Validation
1. Verify backup integrity (checksum)
2. Check AICO version compatibility
3. Confirm encryption key availability
4. Validate backup metadata

### Restore Process

#### Full Restore
1. Stop AICO backend
2. Decrypt backup archive
3. Verify backup integrity
4. Extract databases to temporary location
5. Validate database integrity
6. Move databases to target location
7. Restore encryption keys to platform keyring
8. Update configuration
9. Start AICO backend
10. Verify functionality

#### Selective Restore
1. Extract specific database from backup
2. Validate database integrity
3. Merge or replace target database
4. Verify functionality

### Rollback Strategy
If restore fails:
1. Keep original data intact during restore
2. Use temporary location for extraction
3. Only replace original after validation
4. Maintain backup of pre-restore state

---

## Key Management in Backups

### Challenge
Encryption keys must be backed up securely but remain accessible for restore.

### Solution: Encrypted Key Export

#### Backup Process
1. Export master key from platform keyring
2. Encrypt key with user password (PBKDF2)
3. Include encrypted key in backup archive
4. Store backup password separately (user responsibility)

#### Restore Process
1. Prompt user for backup password
2. Decrypt master key from backup
3. Import key to platform keyring
4. Use key to access encrypted databases

### Key Storage Options

#### Option 1: Password-Protected Key File
```python
# Export key
master_key = keyring.get_password("AICO", "master_key")
encrypted_key = encrypt_with_password(master_key, user_password)
backup_archive.add("encryption_key.enc", encrypted_key)

# Restore key
encrypted_key = backup_archive.extract("encryption_key.enc")
master_key = decrypt_with_password(encrypted_key, user_password)
keyring.set_password("AICO", "master_key", master_key)
```

#### Option 2: Split Key (Shamir's Secret Sharing)
- Split key into N shares
- Require K shares to reconstruct
- Distribute shares across multiple locations
- More secure but complex

**Recommendation:** Option 1 for simplicity

---

## CLI Commands

**All backup and restore operations unified under `aico backup` command.**

### Quick Reference
```bash
# Create backup
aico backup create [OPTIONS]

# Restore backup
aico backup restore <BACKUP_FILE> [OPTIONS]

# List backups
aico backup list [OPTIONS]

# Verify backup
aico backup verify <BACKUP_FILE>

# Manage backups
aico backup info <BACKUP_FILE>
aico backup delete <BACKUP_FILE>
aico backup cleanup [OPTIONS]

# Schedule backups
aico backup schedule <SUBCOMMAND> [OPTIONS]

# Migrate to encrypted storage
aico backup migrate <SUBCOMMAND> [OPTIONS]
```

---

### Create Backups

```bash
# Create full backup (default: encrypted + compressed with zstd)
aico backup create
aico backup create --output ~/backups/

# Backup without encryption (for testing/trusted storage)
aico backup create --no-encrypt

# Backup without compression (faster, larger files)
aico backup create --no-compress

# Choose compression algorithm
aico backup create --compression gzip    # Better compatibility
aico backup create --compression zstd    # Best balance (default)
aico backup create --compression lz4     # Fastest
aico backup create --compression none    # No compression

# Set compression level (1=fast, 9=best compression)
aico backup create --compression-level 5

# Create incremental backup (only changes since last full)
aico backup create --type incremental

# Create differential backup (all changes since last full)
aico backup create --type differential

# Exclude optional data
aico backup create --exclude models,cache,temp

# Include only specific databases
aico backup create --include libsql,semantic

# Combine options
aico backup create --output ~/backups/ --compression zstd --compression-level 5 --exclude models
```

---

### Restore Backups

```bash
# Restore full backup (prompts for password if encrypted)
aico backup restore ~/backups/aico-backup-20251017-123000.tar.zst.enc

# Restore with password from stdin
echo "mypassword" | aico backup restore backup.tar.zst.enc --password-stdin

# Restore to custom location
aico backup restore backup.tar.zst.enc --target ~/aico-restored/

# Restore specific database only
aico backup restore backup.tar.zst.enc --database semantic
aico backup restore backup.tar.zst.enc --database libsql
aico backup restore backup.tar.zst.enc --database working

# Restore multiple databases
aico backup restore backup.tar.zst.enc --database semantic,libsql

# Restore configuration only
aico backup restore backup.tar.zst.enc --config-only

# Dry-run (validate without making changes)
aico backup restore backup.tar.zst.enc --dry-run

# Force overwrite existing data
aico backup restore backup.tar.zst.enc --force

# Merge mode (don't overwrite existing files)
aico backup restore backup.tar.zst.enc --merge
```

---

### List & Inspect Backups

```bash
# List all backups in default directory
aico backup list

# List backups in specific directory
aico backup list ~/backups/

# List with detailed information
aico backup list --verbose

# Show backup metadata and contents
aico backup info ~/backups/aico-backup-20251017-123000.tar.zst.enc

# Verify backup integrity (checksum validation)
aico backup verify ~/backups/aico-backup-20251017-123000.tar.zst.enc
```

---

### Manage Backups

```bash
# Delete specific backup
aico backup delete ~/backups/aico-backup-20251017-123000.tar.zst.enc

# Cleanup old backups (keep last N)
aico backup cleanup --keep 5

# Cleanup with retention policy
aico backup cleanup --keep-daily 7 --keep-weekly 4 --keep-monthly 6

# Cleanup dry-run (show what would be deleted)
aico backup cleanup --keep 5 --dry-run
```

---

### Schedule Automatic Backups

```bash
# Schedule daily backups at 2 AM
aico backup schedule create --frequency daily --time 02:00

# Schedule weekly backups on Sunday at 3 AM
aico backup schedule create --frequency weekly --day sunday --time 03:00

# Schedule with custom output directory
aico backup schedule create --frequency daily --time 02:00 --output ~/backups/

# List scheduled backup tasks
aico backup schedule list

# Show schedule details
aico backup schedule show

# Enable scheduled backups
aico backup schedule enable

# Disable scheduled backups
aico backup schedule disable

# Delete schedule
aico backup schedule delete
```

---

### Migrate to Encrypted Storage

```bash
# Migrate all data to encrypted filesystem (gocryptfs/cppcryptfs)
aico backup migrate encrypt --output ~/aico-encrypted/

# Migrate with automatic backup creation
aico backup migrate encrypt --output ~/aico-encrypted/ --create-backup

# Verify migration integrity
aico backup migrate verify --source ~/.local/share/aico/data/ --target ~/aico-encrypted/

# Rollback migration (restore from backup)
aico backup migrate rollback --backup ~/backups/pre-migration-backup.tar.zst.enc

# Show migration status
aico backup migrate status
```

---

## Architecture

### Shared Implementation (CLI + Backend)

**Core Module:** `shared/aico/backup/`

```
shared/aico/backup/
├── __init__.py
├── backup_manager.py      # Main backup/restore logic
├── archive.py             # Archive creation/extraction
├── compression.py         # Compression algorithms (gzip, zstd, lz4)
├── encryption.py          # Backup encryption (AES-256-GCM)
├── verification.py        # Integrity checking (SHA-256)
├── metadata.py            # Backup metadata management
└── databases/
    ├── __init__.py
    ├── libsql.py          # libSQL backup/restore
    ├── chromadb.py        # ChromaDB backup/restore
    ├── lmdb.py            # LMDB backup/restore
    └── rocksdb.py         # RocksDB backup/restore
```

### CLI Integration

**Location:** `cli/commands/backup.py`

```python
# CLI uses shared backup module directly
from aico.backup import BackupManager

def backup_create(output_dir, encrypt=True, compress='zstd', **kwargs):
    manager = BackupManager(
        data_dir=get_data_directory(),
        config_manager=get_config_manager()
    )
    
    backup_path = manager.create_backup(
        output_dir=output_dir,
        encrypt=encrypt,
        compression=compress,
        **kwargs
    )
    
    console.print(f"✅ Backup created: {backup_path}")
```

**Key Points:**
- ✅ No backend dependency
- ✅ Works standalone with CLI
- ✅ Direct filesystem access
- ✅ Uses shared configuration manager
- ✅ Uses shared encryption (AICOKeyManager)

### Backend Scheduler Integration

**Location:** `backend/scheduler/tasks/maintenance.py`

```python
# Backend scheduler uses same shared module
from aico.backup import BackupManager
from backend.scheduler.core import BaseTask

class AutomaticBackupTask(BaseTask):
    def __init__(self):
        super().__init__(
            task_id="automatic_backup",
            name="Automatic Backup",
            description="Scheduled automatic backup"
        )
    
    async def execute(self, context):
        manager = BackupManager(
            data_dir=context.config.get_data_directory(),
            config_manager=context.config
        )
        
        backup_path = await manager.create_backup_async(
            output_dir=context.config.get("backup.output_dir"),
            encrypt=context.config.get("backup.encrypt", True),
            compression=context.config.get("backup.compression", "zstd")
        )
        
        return {"backup_path": backup_path, "status": "success"}
```

**Key Points:**
- ✅ Uses same BackupManager as CLI
- ✅ Async wrapper for scheduler
- ✅ Configured via core.yaml
- ✅ No code duplication

### Configuration

**Location:** `config/defaults/core.yaml`

```yaml
backup:
  # Default backup settings
  encrypt: true                    # Encrypt backups by default
  compression: zstd                # Compression: gzip, zstd, lz4, none
  compression_level: 3             # Compression level (1-9)
  output_dir: "~/backups/aico/"   # Default backup location
  
  # Backup scope
  include:
    - libsql
    - chromadb
    - lmdb
    - rocksdb
    - config
  
  exclude:
    - models      # Don't backup model files (can re-download)
    - cache       # Don't backup cache
    - temp        # Don't backup temp files
  
  # Retention policy
  retention:
    keep_daily: 7      # Keep 7 daily backups
    keep_weekly: 4     # Keep 4 weekly backups
    keep_monthly: 6    # Keep 6 monthly backups
  
  # Scheduled backups (via task scheduler)
  schedule:
    enabled: false
    frequency: daily   # daily, weekly, monthly
    time: "02:00"      # Time to run (24h format)
    day: sunday        # For weekly backups
```

### Encryption Options

#### Option 1: Encrypted Backup (Default)
```bash
aico backup create --output ~/backups/
# Creates: aico-backup-20251017-123000.tar.zst.enc
# - Compressed with zstd
# - Encrypted with AES-256-GCM
# - Password from platform keyring or prompt
```

#### Option 2: Unencrypted Backup
```bash
aico backup create --output ~/backups/ --no-encrypt
# Creates: aico-backup-20251017-123000.tar.zst
# - Compressed with zstd
# - No encryption (use for testing or trusted storage)
```

#### Option 3: No Compression
```bash
aico backup create --output ~/backups/ --no-compress
# Creates: aico-backup-20251017-123000.tar.enc
# - No compression (faster, larger)
# - Encrypted with AES-256-GCM
```

#### Option 4: Plaintext Archive
```bash
aico backup create --output ~/backups/ --no-encrypt --no-compress
# Creates: aico-backup-20251017-123000.tar
# - No compression
# - No encryption
# - Use only for testing or trusted environments
```

### Compression Algorithms

| Algorithm | Speed | Ratio | CPU | Use Case |
|-----------|-------|-------|-----|----------|
| **zstd** (default) | Fast | High | Medium | Best balance |
| **gzip** | Medium | Medium | Low | Compatibility |
| **lz4** | Very Fast | Low | Very Low | Speed priority |
| **none** | Instant | None | None | Testing/trusted storage |

**Configuration:**
```yaml
backup:
  compression: zstd        # Algorithm
  compression_level: 3     # 1 (fast) to 9 (best compression)
```

**CLI Override:**
```bash
aico backup create --compression zstd --compression-level 5
aico backup create --compression gzip
aico backup create --compression lz4
aico backup create --no-compress
```

---

## Implementation Plan

### Phase 1: Core Backup/Restore (CLI-Only)
- [ ] Create `shared/aico/backup/` module structure
- [ ] Implement `BackupManager` class
- [ ] Implement archive creation/extraction
- [ ] Implement compression support (zstd, gzip, lz4)
- [ ] Implement encryption support (AES-256-GCM)
- [ ] Implement verification (SHA-256 checksums)
- [ ] Implement metadata management
- [ ] Add database-specific backup handlers
- [ ] Create CLI commands (`cli/commands/backup.py`)
- [ ] Test on all platforms (Windows, Linux, macOS)
- [ ] **No backend dependency - works standalone**

### Phase 2: Backend Scheduler Integration
- [ ] Create `AutomaticBackupTask` in maintenance tasks
- [ ] Add async wrapper for BackupManager
- [ ] Add backup scheduling configuration
- [ ] Implement retention policy cleanup
- [ ] Add backup status monitoring
- [ ] Test scheduled backups

### Phase 3: Encryption Migration
- [ ] Implement gocryptfs/cppcryptfs integration
- [ ] Create migration tool
- [ ] Add migration verification
- [ ] Test migration process
- [ ] Document user migration guide

### Phase 4: Advanced Features
- [ ] Incremental backups (track changes)
- [ ] Differential backups
- [ ] Backup compression optimization
- [ ] Cloud backup integration (optional)
- [ ] Backup deduplication

### Phase 5: Device Roaming
- [ ] P2P encrypted sync protocol
- [ ] Conflict resolution
- [ ] Multi-device backup coordination
- [ ] Federated backup storage

---

## Security Considerations

### Backup Security
- ✅ Encrypt backup archives (AES-256-GCM)
- ✅ Password-protect encryption keys
- ✅ Verify backup integrity (SHA-256 checksums)
- ✅ Secure deletion of temporary files
- ✅ Access control on backup files (0600 permissions)

### Restore Security
- ✅ Validate backup source (prevent malicious backups)
- ✅ Verify checksums before restore
- ✅ Sandbox restore process (temporary location)
- ✅ Audit log of restore operations

### Key Management Security
- ✅ Never store keys in plaintext
- ✅ Use platform keyring for key storage
- ✅ Encrypt keys in backup archives
- ✅ Prompt for password (never hardcode)
- ✅ Secure key derivation (PBKDF2, 100k+ iterations)

---

## Testing Strategy

### Test Scenarios
1. **Full Backup → Full Restore**
   - Create backup of working system
   - Wipe data directory
   - Restore from backup
   - Verify all functionality

2. **Encryption Migration**
   - Backup plaintext data
   - Migrate to encrypted filesystem
   - Verify data integrity
   - Test AICO functionality
   - Rollback and verify

3. **Partial Restore**
   - Corrupt single database
   - Restore only that database
   - Verify selective restore

4. **Cross-Platform Restore**
   - Create backup on Linux
   - Restore on macOS
   - Restore on Windows
   - Verify compatibility

5. **Disaster Recovery**
   - Simulate complete data loss
   - Restore from backup
   - Verify full system recovery

---

## User Documentation

### Backup Best Practices
1. **Regular Backups:** Weekly full, daily incremental
2. **Multiple Locations:** Local + external drive + cloud (optional)
3. **Test Restores:** Verify backups work before disaster
4. **Secure Storage:** Encrypt backups, protect passwords
5. **Version Retention:** Keep multiple backup versions

### Migration Guide
1. **Pre-Migration:**
   - Create full backup
   - Verify backup integrity
   - Document current configuration
   - Test backup restore (dry-run)

2. **Migration:**
   - Run migration tool
   - Verify data integrity
   - Test AICO functionality
   - Keep backup until confident

3. **Post-Migration:**
   - Securely delete plaintext data
   - Update documentation
   - Create new encrypted backup

---

## Open Questions

1. **Backup Scheduling:**
   - Automatic vs manual backups?
   - Integration with AICO task scheduler?
   - User-configurable schedule?

2. **Cloud Backup:**
   - Support cloud storage (S3, Dropbox, etc.)?
   - End-to-end encryption for cloud backups?
   - Sync protocol for multi-device?

3. **Compression:**
   - Which compression algorithm (gzip, zstd, lz4)?
   - Compression level vs speed tradeoff?
   - Compress before or after encryption?

4. **Retention Policy:**
   - How many backups to keep?
   - Automatic cleanup of old backups?
   - User-configurable retention?

5. **Verification:**
   - Automatic backup verification after creation?
   - Periodic verification of stored backups?
   - Notification on verification failure?

---

## Related Documents

- `docs/research/encryption-solutions.md` - Encryption strategy research
- `WIP_encryption_analysis.md` - Current encryption status
- `docs/security/encryption.md` - Encryption implementation details
- `docs/guides/developer/schema-management.md` - Database schema management

---

## Next Steps

1. Review and finalize backup/restore strategy
2. Implement Phase 1 (basic backup/restore)
3. Test on all platforms (Windows, Linux, macOS)
4. Create user migration guide
5. Implement encryption migration tool
6. Document disaster recovery procedures
