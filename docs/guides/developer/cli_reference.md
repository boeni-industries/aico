# AICO CLI Reference

## Overview
Complete command reference for the AICO CLI. This document covers all available commands, their options, and usage examples.

## Installation

```bash
uv tool install aico-cli  # Recommended
aico --version            # Verify
```

---

## Version Commands (`aico version`)

Manage and synchronize versions across all AICO subsystems.

### Available Commands

| Command | Description |
|---------|-------------|
| `show [subsystem]` | Show version for subsystem or all subsystems |
| `sync` | Sync canonical versions from VERSIONS file to project files |
| `bump <subsystem> <level>` | Bump version and update files |
| `check [subsystem]` | Check project files match canonical versions |
| `next [subsystem] [level]` | Preview next version number |
| `history [subsystem]` | Show version history from git |

**Subsystems**: `shared`, `cli`, `backend`, `frontend`, `studio`, `modelservice`  
**Levels**: `major`, `minor`, `patch`

### Examples

```bash
# Show all versions
aico version show    # Current version
aico version sync    # Sync components
aico version bump patch
# Preview next version
aico version next backend minor

# Show version history
aico version history --utc
```

### Options

- `--tag` (bump): Create git tag
- `--push` (bump): Push tag to remote
- `--utc` (history): Display timestamps in UTC

---

## Security Commands (`aico security`)

Master password setup and security operations for AICO's encrypted data layer.

### Core Commands

| Command | Description | Security Level |
|---------|-------------|----------------|
| `setup` | First-time master password setup | Setup |
| `passwd` | Change master password | @sensitive |
| `status` | Check security health and key management | Regular |
| `session` | Show CLI session status and timeout | Regular |
| `clear` | Clear cached master key and session | @sensitive |
| `logout` | Clear CLI authentication session | Regular |
| `test` | Security diagnostics and benchmarks | Regular |

### User Management Commands

| Command | Description |
|---------|-------------|
| `user-create <name>` | Create new user with optional PIN |
| `user-list [uuid]` | List users or show detailed user info |
| `user-update <uuid>` | Update user profile information |
| `user-delete <uuid>` | Delete user (soft delete by default) |
| `user-set-pin <uuid>` | Set or update user PIN |
| `user-auth <uuid>` | Authenticate user with PIN |
| `user-stats` | Show user statistics |

### Role Management Commands

| Command | Description |
|---------|-------------|
| `role-list [uuid]` | List roles and permissions |
| `role-assign <uuid> <role>` | Assign role to user |
| `role-revoke <uuid> <role>` | Revoke role from user |
| `role-check <uuid> <permission>` | Check user permission |
| `role-bootstrap <uuid>` | Bootstrap admin role for initial setup |

### Examples

```bash
aico security setup                    # Initial setup
aico security user-create alice --email alice@example.com
aico security role-assign user-uuid-here admin
aico security role-list user-uuid
```

### Options

- `--password` (setup): Provide password directly
- `--jwt-only` (setup): Only initialize JWT secrets
- `--utc` (status, session): Display timestamps in UTC
- `--confirm` (clear, user-delete): Skip confirmation prompt
- `--hard` (user-delete): Permanent deletion
- `--detailed` (user-list): Show comprehensive user information
- `--show-permissions` (role-list): Show detailed permissions

### Session Management

- **30-minute timeout** with automatic extension
- **Platform keyring storage** (Keychain/Credential Manager)
- **Decorator-based security**: `@sensitive` and `@destructive` commands require fresh authentication

## Database Commands (`aico db`)

Encrypted database initialization, operations, and content inspection.

### Management Commands

| Command | Description | Security Level |
|---------|-------------|----------------|
| `init` | Initialize encrypted database or apply schemas | Regular |
| `status` | Check database encryption status | Regular |
| `test` | Test database connection and operations | Regular |
| `show` | Show database configuration and paths | Regular |
| `check` | Database integrity check | Regular |
| `vacuum` | Optimize database (VACUUM) | @destructive |

### Content Commands

| Command | Description |
|---------|-------------|
| `ls` | List all tables with record counts |
| `desc <table>` | Describe table structure (schema) |
| `count` | Count records in tables |
| `head <table>` | Show first N records from table |
| `tail <table>` | Show last N records from table |
| `stat` | Database statistics (size, tables, records) |
| `exec <query>` | Execute raw SQL query (@destructive) |

### Examples

```bash
aico db init      # Initialize database
aico db status    # Check status
aico db ls        # List tables
aico db vacuum    # Maintenance
```

### Options

- `--db-path` (init, status, test): Custom database file path
- `--db-type` (init, status, test): Database type (libsql, duckdb, chroma, rocksdb)
- `--password` (init, test): Provide master password directly
- `--table` (count): Specific table to count
- `--all` (count): Count all tables
- `--limit, -n` (head, tail): Number of records to show
- `--utc` (head, tail): Display timestamps in UTC

### Notes

- **Idempotent initialization**: `aico db init` works on existing databases
- **Unified encryption**: Uses AICOKeyManager for all database types
- **Safe inspection**: Content commands don't expose sensitive data
- **Automatic schemas**: Core schemas applied during initialization

---

## Logs Commands (`aico logs`)

Log management and analysis for AICO's unified logging system.

### Available Commands

| Command | Description | Security Level |
|---------|-------------|----------------|
| `ls` | List logs with filtering options | Regular |
| `cat` | Show full log entry details | Regular |
| `rm` | Delete logs by criteria | Regular |
| `stat` | Show log statistics and summaries | Regular |
| `tail` | Show recent logs | Regular |
| `grep <pattern>` | Search logs by pattern | Regular |
| `export` | Export logs to JSON or CSV | @sensitive |

### Examples

```bash
aico logs ls --limit 50              # Recent logs
aico logs ls --subsystem gateway     # Component logs
aico logs grep "authentication failed"
```

### Filtering Options

**ls command filters:**
- `--limit, -n`: Number of logs to show
- `--level`: Filter by log level (DEBUG, INFO, WARN, ERROR)
- `--subsystem`: Filter by subsystem (cli, backend, etc.)
- `--module`: Filter by specific module
- `--since`: Show logs since timestamp
- `--last`: Show logs from last period (e.g., 1h, 30m, 7d)
- `--format`: Output format (table, json, oneline)
- `--oneline`: Compact one-line format
- `--utc`: Display timestamps in UTC

**cat command options:**
- `--id`: Show specific log by ID
- `--trace-id`: Show logs by trace ID
- `--level`: Filter by log level
- `--last`: Show logs from last period
- `--format`: Output format (pretty, json)
- `--utc`: Display timestamps in UTC

**tail command options:**
- `--follow, -f`: Follow log output (not yet implemented)
- `--level`: Filter by log level
- `--subsystem`: Filter by subsystem
- `--lines, -n`: Number of lines to show (default: 20)
- `--limit`: Number of entries to show (alias for --lines)
- `--utc`: Display timestamps in UTC

**grep command options:**
- `--level`: Filter by log level
- `--subsystem`: Filter by subsystem
- `--limit`: Maximum results to show (default: 100)
- `--utc`: Display timestamps in UTC

**export command options:**
- `--output, -o`: Output file path (default: logs_export.json)
- `--format`: Export format (json, csv)
- `--last`: Export logs from last period
- `--level`: Filter by log level
- `--subsystem`: Filter by subsystem

**rm command options:**
- `--before`: Delete logs before date
- `--older-than`: Delete logs older than period (e.g., 7d)
- `--level`: Delete logs of specific level
- `--subsystem`: Delete logs from subsystem
- `--confirm`: Skip confirmation prompt

### Notes

- **Unified storage**: All AICO subsystems log to encrypted database
- **ZeroMQ transport**: Real-time log collection via message bus
- **Privacy-first**: Automatic PII redaction and audit logging
- **Follow mode**: Real-time following planned for future implementation

---

## Configuration Commands (`aico config`)

Configuration management and validation.

### Available Commands

| Command | Description |
|---------|-------------|
| `get <key>` | Get configuration value using dot notation |
| `set <key> <value>` | Set configuration value using dot notation |
| `list` | List all configuration values |
| `validate` | Validate configuration against schemas |
| `export <file>` | Export configuration to file (@sensitive) |
| `import <file>` | Import configuration from file |
| `reload` | Reload configuration from files |
| `domains` | List available configuration domains |
| `schema <domain>` | Show schema for configuration domain |
| `show` | Show configuration paths and platform info |
| `init` | Initialize configuration files |

### Examples

```bash
aico config get database.path  # Get value
aico config list               # List all
aico config validate           # Check config
```

### Options

- `--no-persist` (set): Don't persist change to storage
- `--domain, -d` (list, validate): Specific domain to operate on
- `--format, -f` (list): Output format (table, yaml, json)
- `--no-validate` (import): Skip validation during import
- `--force, -f` (init): Force initialization, overwriting existing files

---

## Service Management Commands

### Gateway Commands (`aico gateway`)

API Gateway service management and protocol control.

### Available Commands

| Command | Description |
|---------|-------------|
| `start` | Start the API Gateway service |
| `stop` | Stop the API Gateway service |
| `restart` | Restart the API Gateway service |
| `status` | Show API Gateway status and configuration |
| `config [section]` | Show gateway configuration |
| `protocols` | List available protocol adapters |
| `test` | Test API Gateway connectivity and health |
| `enable <protocol>` | Enable protocol adapter |
| `disable <protocol>` | Disable protocol adapter |

### Options

- `--dev` (start): Start in development mode using UV
- `--detach/--no-detach` (start): Run as background service (default: True)

**Authentication subcommands (`aico gateway auth`):**
- `login` - Generate and store JWT token for CLI
- `logout` - Remove stored JWT token
- `status` - Show authentication status

**Admin subcommands (`aico gateway admin`):**
- `sessions` - List active sessions
- `revoke-session <id>` - Revoke specific session
- `gateway-status` - Show detailed gateway status

### Scheduler Commands (`aico scheduler`)

Task scheduler management.

### Available Commands

| Command | Description | Security Level |
|---------|-------------|----------------|
| `ls` | List scheduled tasks | @sensitive |
| `show <task-id>` | Show task details | @sensitive |
| `create <task-id>` | Create new scheduled task | @sensitive |
| `update <task-id>` | Update task configuration | @sensitive |
| `delete <task-id>` | Delete scheduled task | @sensitive |
| `enable <task-id>` | Enable task | @sensitive |
| `disable <task-id>` | Disable task | @sensitive |
| `trigger <task-id>` | Manually trigger task execution | @sensitive |
| `history [task-id]` | Show task execution history | @sensitive |
| `status` | Show scheduler status and statistics | @sensitive |

### Model Service Commands (`aico modelservice`, `aico ollama`)

Model service and Ollama management.

**Model Service:**
- `start` - Start model service
- `stop` - Stop model service
- `status` - Show service status
- `test` - Test model service connectivity

**Ollama:**
- `install` - Install Ollama
- `start` - Start Ollama service
- `stop` - Stop Ollama service
- `status` - Show Ollama status
- `models` - List available models
- `pull <model>` - Download model
- `remove <model>` - Remove model
- `chat <model>` - Interactive chat with model

### Scheduler Options

- `--enabled, -e` (ls): Show only enabled tasks
- `--format, -f` (ls): Output format (table, json)
- `--config, -c` (create): JSON config file path
- `--enabled/--disabled` (create): Enable task immediately
- `--confirm` (delete): Skip confirmation prompt
- `--wait` (trigger): Wait for task completion
- `--limit, -n` (history): Limit number of results

### Examples

```bash
aico scheduler ls                # List tasks
aico scheduler create backup-task BackupTask "0 2 * * *"
aico scheduler trigger backup-task
```

### Model Service Examples

```bash
aico ollama install llama2  # Install model
aico ollama models list      # List models
aico ollama chat llama2    # Interactive chat
```

### Message Bus Commands (`aico bus`)

Message bus testing and monitoring.

### Available Commands

| Command | Description |
|---------|-------------|
| `test` | Test message bus connectivity |
| `monitor` | Monitor message bus activity |
| `status` | Show message bus status |
| `publish <topic> <message>` | Publish test message |

### Examples

```bash
aico bus test     # Test connectivity
aico bus monitor  # Monitor activity
aico bus publish test.topic "Hello"
```

---

## Development Commands (`aico dev`)

Development utilities and cleanup tools.

### Available Commands

| Command | Description |
|---------|-------------|
| `wipe` | Wipe development data with granular control |
| `protoc` | Compile Protocol Buffer files to Python code |

### Options

- `--security` (wipe): Clear master password and keyring data
- `--data` (wipe): Remove databases and salt files
- `--config` (wipe): Remove configuration files
- `--cache` (wipe): Remove cache and temporary files
- `--app-dir` (wipe): Remove entire application directory
- `--all` (wipe): Wipe everything (security + data + config + cache + app-dir)
- `--dry-run` (wipe): Show what would be deleted without doing it
- `--i-know-what-im-doing` (wipe): Skip environment checks (DANGEROUS)
- `--verbose, -v` (protoc): Show detailed output
- `--dry-run` (protoc): Show command that would be executed without running it

---

## Security Levels

Commands are classified by security requirements:

- **Setup**: No authentication required (initial setup commands)
- **Regular**: Uses session-based authentication (30-minute timeout)
- **@sensitive**: Requires fresh authentication (password changes, data export)
- **@destructive**: Requires fresh authentication (operations with data loss risk)

## Global Options

- `--help` - Show command help
- `--utc` - Display timestamps in UTC
- `--format [table|json|yaml]` - Output format
- `--confirm` - Skip confirmation prompts
- `--verbose` / `--quiet` - Control output verbosity

## Common Workflows

### Initial Setup
```bash
aico security setup    # Master password
aico db init          # Database
aico gateway start    # Start services
```

### Daily Operations
```bash
aico gateway status   # System status
aico logs ls --limit 20
aico security user-list
```

### Troubleshooting
```bash
aico logs grep "error"
aico gateway test
aico config validate
```

### Maintenance
```bash
aico logs rm --older-than 30d
aico db vacuum
aico version sync
```

---
