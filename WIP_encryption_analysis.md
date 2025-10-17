# AICO Database Encryption Analysis

## Current Encryption Status

### 1. **libSQL** ✅ ENCRYPTED
- **Status**: Fully encrypted using SQLCipher-style encryption
- **Implementation**: `shared/aico/data/libsql/encrypted.py`
- **Encryption Method**: AES-256 via PRAGMA key statements
- **Key Derivation**: PBKDF2 from master password via `AICOKeyManager`
- **Storage**: Single file (`aico.db`) + salt file (`.salt`)
- **Key Management**: 
  - Master key derived from user password
  - Database-specific keys derived using HKDF
  - Keys stored in platform secure storage (Keychain/Credential Manager)

### 2. **ChromaDB** ❌ NOT ENCRYPTED
- **Status**: Plaintext storage - CRITICAL SECURITY GAP
- **Implementation**: `shared/aico/ai/memory/semantic.py`
- **Storage Location**: `~/.local/share/aico/data/memory/semantic/`
- **Storage Format**: 
  - Directory structure with multiple files
  - Internal SQLite database (plaintext)
  - Parquet files for vector data (plaintext)
  - JSON metadata files (plaintext)
- **Sensitive Data**:
  - Conversation segments (full message content)
  - User messages and AI responses
  - Embeddings (768-dimensional vectors)
  - Metadata: user_id, conversation_id, timestamps, roles

### 3. **LMDB** ❌ NOT ENCRYPTED
- **Status**: Plaintext storage - CRITICAL SECURITY GAP
- **Implementation**: `shared/aico/ai/memory/working.py`
- **Storage Location**: `~/.local/share/aico/data/memory/working/`
- **Storage Format**:
  - Memory-mapped database files
  - Multiple named databases within environment
  - Key-value pairs stored as JSON
- **Sensitive Data**:
  - Active conversation context
  - Recent message history (24-hour TTL)
  - Session state and user data
  - Temporary conversation metadata

---

## Security Gap Analysis

### Risk Assessment

**ChromaDB Exposure**:
- **Severity**: CRITICAL
- **Data at Risk**: Complete conversation history, semantic facts, user preferences
- **Attack Surface**: Filesystem access exposes all historical conversations
- **Compliance Impact**: GDPR/privacy violations for unencrypted personal data

**LMDB Exposure**:
- **Severity**: HIGH
- **Data at Risk**: Recent conversations (24 hours), active session data
- **Attack Surface**: Filesystem access exposes current conversation context
- **Compliance Impact**: Real-time conversation monitoring possible

### Threat Scenarios

1. **Laptop Theft/Loss**: Attacker gains full access to conversation history
2. **Malware**: File-reading malware can exfiltrate all conversations
3. **Cloud Sync**: Unencrypted files synced to cloud expose data
4. **Forensics**: Device seizure exposes complete conversation records
5. **Shared Devices**: Other users can read conversation files

---

## Technical Constraints

### Why Database-Level Encryption Won't Work

**ChromaDB**:
- No native encryption support
- Complex internal structure (SQLite + Parquet + JSON)
- Modifying ChromaDB internals is fragile and unmaintainable
- Version upgrades would break custom encryption

**LMDB**:
- No native encryption support
- Memory-mapped architecture makes encryption complex
- Would require forking LMDB or wrapping every operation
- Performance impact would be significant

### Existing Encryption Infrastructure

**Available**: `shared/aico/security/encrypted_file.py`
- Provides transparent AES-256-GCM file encryption
- Integrated with `AICOKeyManager`
- Supports streaming operations
- Cross-platform (pure Python)
- Already proven with libSQL

**Challenge**: ChromaDB and LMDB expect direct filesystem access, not file-like objects. They manage their own file handles internally and cannot use Python's `EncryptedFile` directly.
