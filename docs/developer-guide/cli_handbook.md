# AICO CLI Handbook

## Overview
The `aico` command-line interface (CLI) is your central tool for automating, administering, and interacting with the AICO system. This handbook covers practical usage, command syntax, and real-world examples for developers and power users.

---

## Installation

### End Users
```bash
uv tool install aico-cli    # Recommended
pipx install aico-cli       # Alternative
```

---

## Version Command Group

### Purpose
Manage and synchronize the versioning of all major AICO system parts (CLI, backend, frontend, studio) from a single source of truth.

### Usage Summary

```sh
aico version [COMMAND] [OPTIONS]
```

### Available Commands

| Command                                | Description                                             |
|----------------------------------------|---------------------------------------------------------|
| `aico version [part]`                  | Print the current version of a part or all parts        |
| `aico version sync`                    | Sync all canonical project versions from VERSIONS file  |
| `aico version bump [part] [level]`     | Bump version (major, minor, patch) and propagate/tag    |
| `aico version check`                   | Validate all canonical versions vs. VERSIONS            |
| `aico version history [part]`          | Show git tag history for a part                         |
| `aico version next [part] [level]`     | Preview next version number without changing anything   |

- `[part]` can be: `cli`, `backend`, `frontend`, `studio`, or `all` (default: all)
- `[level]` can be: `major`, `minor`, or `patch`

### Examples

- Print all versions:
  ```sh
  aico version
  ```
- Print backend version:
  ```sh
  aico version backend
  ```
- Sync all canonical versions from VERSIONS:
  ```sh
  aico version sync
  ```
- Bump CLI version (patch):
  ```sh
  aico version bump cli patch
  ```
- Preview next frontend minor version:
  ```sh
  aico version next frontend minor
  ```
- Check for version drift:
  ```sh
  aico version check
  ```
- Show studio version history:
  ```sh
  aico version history studio
  ```

### UX Principles
- All commands provide clear, colorized, and actionable output.
- Incomplete or ambiguous commands trigger a helpful, predictive help text.
- Destructive actions (bump, sync) require confirmation or a `--yes` flag.
- Tabular and markdown output is used where appropriate.
- Errors and warnings are highlighted for quick identification.

### Advanced Options
- `--dry-run` (where supported): Preview changes without applying them.
- `--no-tag` (for bump): Skip git tagging when bumping version.

### Notes
- The source of truth for all versions is the `VERSIONS` file at the project root.
- Canonical versions are propagated to: `/cli`, `/backend`, `/frontend`, `/studio`.
- Versioning follows [Semantic Versioning](https://semver.org/).

---

For more details on versioning policy, see the [developer guide](./versioning.md).

---

## Security Commands (`aico security`)

Manages master password setup and security operations for AICO's encrypted data layer.

### Available Commands

| Command | Description |
|---------|-------------|
| `setup` | First-time master password setup |
| `passwd` | Change master password (affects all databases) |
| `status` | Check security health and key management status |
| `session` | Show CLI session status and timeout information |
| `clear` | Clear cached master key and active session (forces password re-entry) |
| `test` | Performance diagnostics and key derivation benchmarking |

### Examples

```bash
# First-time setup
aico security setup

# Check status
aico security status

# Check session status
aico security session

# Change master password
aico security passwd

# Test authentication
aico security test

# Clear session (force re-authentication)
aico security clear
```

### Session Management

AICO CLI uses session-based authentication for improved developer experience:

- **30-minute timeout**: Sessions automatically expire after 30 minutes of inactivity
- **Activity extension**: Sessions extend automatically on CLI usage
- **Secure storage**: Master key stored in platform keyring (Keychain/Credential Manager)
- **One-time setup**: Password entered once, then cached until session expires
- **Force fresh auth**: Sensitive commands like `security passwd` always require fresh authentication

### Session Workflow

1. **First command**: Prompts for master password, creates 30-minute session
2. **Subsequent commands**: Use cached session, no password prompt
3. **Session expiry**: Next command prompts for password, creates new session
4. **Manual clear**: `aico security clear` forces immediate re-authentication

## Database Commands (`aico db`)

Manages encrypted database initialization, operations, and content inspection.

### Database Management Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize new encrypted database or apply missing schemas |
| `status` | Check database encryption status and information |
| `test` | Test database connection and basic operations |
| `show` | Show database configuration, paths, and settings |

### Database Content Commands

| Command | Description |
|---------|-------------|
| `ls` | List all tables in database with record counts |
| `desc <table>` | Describe table structure (schema) |
| `count --table <name>\|--all` | Count records in specific table or all tables |
| `head <table> [-n N]` | Show first N records from table |
| `tail <table> [-n N]` | Show last N records from table |
| `stat` | Database statistics (size, tables, indexes, total records) |
| `vacuum` | Optimize database (VACUUM) |
| `check` | Run integrity check |
| `exec <query>` | Execute raw SQL query with safety confirmations |

### Examples

```bash
# Database Management
aico db init                              # Initialize or update existing database
aico db status                            # Check database status
aico db show                              # Show database paths and configuration

# Content Inspection
aico db ls                                # List all tables
aico db desc logs                         # Show logs table schema
aico db count --all                       # Count records in all tables
aico db head logs -n 10                   # Show first 10 log entries
aico db tail logs -n 5                    # Show last 5 log entries
aico db stat                              # Database statistics

# Maintenance
aico db vacuum                            # Optimize database
aico db check                             # Check database integrity

# Advanced
aico db exec "SELECT level, COUNT(*) FROM logs GROUP BY level"
```

### Workflow

1. **Setup master password**: `aico security setup`
2. **Initialize database**: `aico db init` (idempotent - works on existing DBs)
3. **Verify setup**: `aico db status`
4. **Inspect content**: `aico db ls`, `aico db stat`

### Notes
- **Idempotent initialization**: `aico db init` detects existing databases and applies missing schemas
- Uses `AICOKeyManager` for unified key management
- Supports multiple database types (currently LibSQL)
- PBKDF2 key derivation for LibSQL, Argon2id for others
- Stores passwords securely in system keyring
- Automatic salt management for database files
- Content commands provide safe database inspection without exposing sensitive data

---

## Logs Commands (`aico logs`)

Comprehensive log management and analysis for AICO's unified logging system. All logs are stored in the encrypted database and transported via ZeroMQ message bus.

### Available Commands

| Command | Description |
|---------|-------------|
| `ls [filters]` | List logs with filtering options |
| `cat <id>` | Show full log entry details |
| `rm [criteria]` | Delete logs by criteria (with confirmation) |
| `stat` | Show log statistics and summaries |
| `tail [-f]` | Show recent logs (follow mode for real-time) |
| `grep <pattern>` | Search logs by pattern |
| `export [format]` | Export logs to JSON or CSV |

### Filtering Options

The `ls` command supports extensive filtering:
- `--level <level>` - Filter by log level (DEBUG, INFO, WARN, ERROR)
- `--subsystem <name>` - Filter by subsystem (cli, backend, frontend, studio)
- `--module <name>` - Filter by specific module
- `--since <time>` - Show logs since timestamp
- `--until <time>` - Show logs until timestamp
- `--limit <n>` - Limit number of results
- `--format <fmt>` - Output format (table, json, compact)

### Examples

```bash
# Basic log viewing
aico logs ls                              # List recent logs
aico logs ls --limit 50                   # Show last 50 logs
aico logs tail                            # Show recent logs (like tail -f)

# Filtering
aico logs ls --level ERROR                # Show only errors
aico logs ls --subsystem backend          # Show backend logs only
aico logs ls --module security.key_manager # Show key manager logs
aico logs ls --since "2024-01-01"         # Logs since date

# Search and analysis
aico logs grep "database"                 # Search for "database" in logs
aico logs stat                            # Log statistics
aico logs cat 12345                       # Show full details for log ID 12345

# Export and cleanup
aico logs export --format json --output logs.json
aico logs rm --level DEBUG --older-than "7 days"  # Clean old debug logs
```

### Log Entry Format

Each log entry contains:
- **Timestamp**: ISO 8601 format with timezone
- **Level**: DEBUG, INFO, WARN, ERROR
- **Subsystem**: cli, backend, frontend, studio
- **Module**: Specific module path (e.g., "security.key_manager")
- **Function**: Function name where log was generated
- **File/Line**: Source file and line number
- **Message**: Log message content
- **Extra Data**: Additional structured data (JSON)
- **Trace/Session IDs**: For distributed tracing

### Configuration

Logging behavior is controlled via `config/defaults/core.yaml`:
- **Storage**: Database-only (no file logging)
- **Levels**: Configurable per subsystem and module
- **Retention**: 30 days, 500MB max size by default
- **Transport**: ZeroMQ message bus configuration
- **Privacy**: Automatic PII redaction and sensitive data encryption

### Notes
- **Unified System**: All AICO subsystems log to the same encrypted database
- **Bootstrap Buffering**: Logs generated before DB ready are buffered and flushed
- **Fallback Logging**: Console output during bootstrap, optional temp file fallback
- **Privacy-First**: Automatic PII redaction and audit logging of log access
- **Real-Time**: ZeroMQ transport enables real-time log collection and following

---
