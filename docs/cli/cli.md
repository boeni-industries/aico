# AICO CLI Handbook

## Overview

The AICO CLI is a comprehensive command-line interface for managing, operating, and debugging the AICO system. It provides 23 command groups covering everything from database management to AI model operations, security, and system monitoring.

**Design Philosophy:**
- **Modular**: Each command group is self-contained and focused
- **Operable**: Production-ready tools for system administration
- **Inspectable**: Deep visibility into system state and operations
- **Cross-platform**: Works on macOS, Linux, and Windows

**Installation:**
```bash
# Development mode (editable install)
cd /path/to/aico
uv pip install -e .

# Run CLI
aico --help
```

---

## Command Groups

### Core System Management

#### `aico version`
**Purpose**: Version and build information management

**Subcommands:**
- `show` - Display current version information for all components
- `sync` - Synchronize versions across all AICO system parts
- `bump` - Bump version numbers (major, minor, patch)

**Common Usage:**
```bash
# Show current versions
aico version show

# Bump patch version
aico version bump patch

# Sync versions across components
aico version sync
```

---

#### `aico config`
**Purpose**: Configuration management and validation

**Subcommands:**
- `get <key>` - Get configuration value using dot notation
- `set <key> <value>` - Set configuration value
- `list [domain]` - List all configuration or specific domain
- `validate [domain]` - Validate configuration against schemas
- `export` - Export configuration to file
- `import` - Import configuration from file

**Common Usage:**
```bash
# Get specific config value
aico config get api_gateway.rest.port

# Set config value
aico config set system.log_level DEBUG

# List all postgres config
aico config list postgres

# Validate all configuration
aico config validate
```

**Configuration Domains:**
- `system` - System-wide settings
- `logging` - Log configuration
- `api_gateway` - API Gateway settings
- `postgres` - PostgreSQL connection
- `influx` - InfluxDB connection
- `message_bus` - ZeroMQ message bus
- `modelservice` - AI model service
- `security` - Security and encryption
- `scheduler` - Task scheduler
- `emotion` - Emotion simulation
- `memory` - Memory subsystems
- `agency` - Agency system

---

#### `aico security`
**Purpose**: Security, encryption, and credential management

**Subcommands:**
- `setup` - Initial master password and JWT setup
- `passwd` - Change master password
- `status` - Security health check
- `session` - Show CLI session status
- `logout` - Clear CLI session
- `clear` - Clear cached credentials
- `test` - Security operations benchmark
- `pg-set` - Store PostgreSQL password
- `pg-env` - Export PostgreSQL environment variables
- `influx-set` - Store InfluxDB token
- `influx-env` - Export InfluxDB environment variables
- `list-keys` - List all keys in keyring
- `get-key <name>` - Retrieve specific key
- `user-create` - Create new user
- `user-list` - List all users
- `user-show <uuid>` - Show user details
- `user-delete <uuid>` - Delete user
- `role-create` - Create new role
- `role-list` - List all roles
- `role-assign` - Assign role to user

**Common Usage:**
```bash
# First-time setup
aico security setup

# Check security status
aico security status

# Store database credentials
aico security pg-set
aico security influx-set

# List stored keys
aico security list-keys

# Create user
aico security user-create "John Doe" --nickname john

# Export env vars for docker-compose
aico security pg-env --format env --include-secrets > .env
```

---

#### `aico logs`
**Purpose**: Log management and analysis (Loki integration)

**Subcommands:**
- `tail` - Stream recent logs
- `query <logql>` - Execute LogQL query
- `search <text>` - Search logs by text
- `stats` - Log statistics and metrics
- `export` - Export logs to file

**Common Usage:**
```bash
# Tail recent logs
aico logs tail --last 100

# Search for errors
aico logs search "error" --level error --last 1h

# Query with LogQL
aico logs query '{job="backend"} |= "interaction"'

# Show log statistics
aico logs stats --last 24h
```

---

### Database Management

#### `aico pg`
**Purpose**: PostgreSQL database management

**Subcommands:**
- `status` - Database connection status
- `doctor` - Health check and diagnostics
- `init` - Initialize database schema
- `start` - Start PostgreSQL (Docker)
- `stop` - Stop PostgreSQL (Docker)
- `test` - Test database connection
- `show <table>` - Show table schema
- `ls` - List all tables
- `desc <table>` - Describe table structure
- `count <table>` - Count rows in table
- `head <table>` - Show first N rows
- `tail <table>` - Show last N rows
- `stat <table>` - Table statistics
- `vacuum` - Vacuum database
- `check` - Check database integrity
- `exec <sql>` - Execute SQL query

**Common Usage:**
```bash
# Check database status
aico pg status

# Initialize schema
aico pg init

# List all tables
aico pg ls

# Show table contents
aico pg head users --limit 10

# Execute SQL
aico pg exec "SELECT COUNT(*) FROM conversations"
```

---

#### `aico lmdb`
**Purpose**: LMDB working memory management

**Subcommands:**
- `status` - LMDB database status
- `stats` - Database statistics
- `list` - List all keys
- `get <key>` - Get value for key
- `delete <key>` - Delete key
- `clear` - Clear all data (with confirmation)
- `compact` - Compact database

**Common Usage:**
```bash
# Check LMDB status
aico lmdb status

# List all keys
aico lmdb list --limit 50

# Get specific key
aico lmdb get "conversation:abc123"

# Database statistics
aico lmdb stats
```

---

#### `aico chroma`
**Purpose**: ChromaDB semantic memory management

**Subcommands:**
- `status` - ChromaDB connection status
- `collections` - List all collections
- `stats <collection>` - Collection statistics
- `query <collection>` - Query collection
- `delete <collection>` - Delete collection
- `export <collection>` - Export collection data
- `import <collection>` - Import collection data

**Common Usage:**
```bash
# Check ChromaDB status
aico chroma status

# List collections
aico chroma collections

# Query semantic memory
aico chroma query semantic_memory --text "user preferences" --limit 5

# Collection statistics
aico chroma stats semantic_memory
```

---

#### `aico influx`
**Purpose**: InfluxDB time-series database management (Pro/Enterprise)

**Subcommands:**
- `status` - InfluxDB connection status
- `buckets` - List all buckets
- `query <flux>` - Execute Flux query
- `write` - Write data point
- `delete` - Delete data
- `backup` - Backup bucket
- `restore` - Restore bucket

**Common Usage:**
```bash
# Check InfluxDB status
aico influx status

# List buckets
aico influx buckets

# Query metrics
aico influx query 'from(bucket:"aico_metrics") |> range(start: -1h)'
```

---

#### `aico kg`
**Purpose**: Knowledge graph management and inspection

**Subcommands:**
- `status` - Knowledge graph status
- `stats` - Graph statistics (nodes, edges, properties)
- `entities` - List entities
- `relationships` - List relationships
- `query <cypher>` - Execute Cypher/GQL query
- `export` - Export graph data
- `import` - Import graph data
- `visualize` - Generate graph visualization
- `consolidate` - Run graph consolidation

**Common Usage:**
```bash
# Graph statistics
aico kg stats

# List entities
aico kg entities --type PERSON --limit 20

# Query graph
aico kg query "MATCH (p:PERSON) RETURN p.name LIMIT 10"

# Export graph
aico kg export --format json > graph.json
```

---

### Service Management

#### `aico gateway`
**Purpose**: API Gateway management and protocol control

**Subcommands:**
- `start` - Start API Gateway service
- `stop` - Stop API Gateway service
- `restart` - Restart API Gateway service
- `status` - Show gateway status and configuration
- `config [section]` - Show configuration
- `protocols` - List available protocol adapters
- `test` - Test gateway connectivity
- `enable <protocol>` - Enable protocol adapter
- `disable <protocol>` - Disable protocol adapter
- `auth login` - Authenticate CLI user
- `auth logout` - Logout CLI user
- `auth status` - Show auth status
- `sessions` - List active user sessions
- `revoke-session <id>` - Revoke user session

**Common Usage:**
```bash
# Start gateway
aico gateway start

# Check status
aico gateway status

# Authenticate
aico gateway auth login

# List protocols
aico gateway protocols

# Test connectivity
aico gateway test
```

---

#### `aico modelservice`
**Purpose**: AI model service management and control

**Subcommands:**
- `start` - Start modelservice
- `stop` - Stop modelservice
- `restart` - Restart modelservice
- `status` - Service status
- `models` - List loaded models
- `load <model>` - Load specific model
- `unload <model>` - Unload model
- `test` - Test model inference
- `benchmark` - Benchmark model performance

**Common Usage:**
```bash
# Start modelservice
aico modelservice start

# Check status
aico modelservice status

# List loaded models
aico modelservice models

# Test inference
aico modelservice test --model sentiment
```

---

#### `aico ollama`
**Purpose**: Ollama model management and operations

**Subcommands:**
- `status` - Ollama service status
- `list` - List available models
- `pull <model>` - Pull model from registry
- `remove <model>` - Remove model
- `show <model>` - Show model details
- `run <model>` - Run model interactively
- `ps` - List running models
- `stop <model>` - Stop running model

**Common Usage:**
```bash
# Check Ollama status
aico ollama status

# List models
aico ollama list

# Pull model
aico ollama pull qwen2.5:7b

# Show model info
aico ollama show qwen2.5:7b
```

---

#### `aico scheduler`
**Purpose**: Task scheduler management

**Subcommands:**
- `ls` - List scheduled tasks
- `show <task_id>` - Show task details
- `enable <task_id>` - Enable task
- `disable <task_id>` - Disable task
- `run <task_id>` - Run task immediately
- `history <task_id>` - Show execution history
- `logs <task_id>` - Show task logs
- `create` - Create new task
- `delete <task_id>` - Delete task

**Common Usage:**
```bash
# List all tasks
aico scheduler ls

# Show task details
aico scheduler show log_cleanup

# Run task now
aico scheduler run log_cleanup

# View execution history
aico scheduler history log_cleanup --limit 20
```

---

### Specialized Systems

#### `aico agency`
**Purpose**: Agency system control (intentions, values, policies, lessons)

**Subcommands:**
- `status <user_id>` - View agency status
- `intentions <user_id>` - View active intentions
- `goals <user_id>` - List all goals
- `goal-show <goal_id>` - Show goal details
- `goal-create` - Create new goal
- `goal-cancel <goal_id>` - Cancel goal
- `values <user_id>` - View value system
- `policies <user_id>` - View active policies
- `metrics` - Agency metrics
- `health` - System health check
- `lessons ls` - List lessons
- `lessons show <id>` - Show lesson details
- `lessons approve <id>` - Approve lesson
- `lessons reject <id>` - Reject lesson
- `lessons stats` - Lesson statistics
- `skill-performance` - Skill performance metrics

**Common Usage:**
```bash
# View agency status
aico agency status <user_uuid>

# List active goals
aico agency goals <user_uuid>

# View lessons
aico agency lessons ls --status active

# Approve lesson
aico agency lessons approve <lesson_id>

# Check metrics
aico agency metrics --last 24h
```

---

#### `aico interactions`
**Purpose**: Interaction request testing and simulation

**Subcommands:**
- `simulate <type>` - Create test interaction
- `reply <id>` - Reply to interaction
- `list` - List interactions
- `ls` - Alias for list
- `get <id>` - Get interaction details

**Common Usage:**
```bash
# Simulate question
aico interactions simulate question \
  --user <uuid> \
  --prompt "Test question?" \
  --listen-ws

# Reply to interaction
aico interactions reply <id> --answer "My answer"

# List interactions
aico interactions list --user <uuid> --status pending

# Get details
aico interactions get <id>
```

See [`interactions-commands.md`](interactions-commands.md) for detailed documentation.

---

#### `aico emotion`
**Purpose**: Emotional simulation state management

**Subcommands:**
- `status` - Emotion system status
- `state <user_id>` - Current emotional state
- `history <user_id>` - Emotion history
- `appraisal <text>` - Test appraisal engine
- `simulate` - Simulate emotion response

**Common Usage:**
```bash
# Check emotion system
aico emotion status

# View current state
aico emotion state <user_uuid>

# Test appraisal
aico emotion appraisal "I just got promoted!"
```

---

#### `aico tools`
**Purpose**: Agency tool inspection and live execution

**Subcommands:**
- `ls` - List all available tools
- `show <tool_name>` - Show tool details
- `exec <tool_name>` - Execute tool with parameters

**Common Usage:**
```bash
# List tools
aico tools ls

# Show tool details
aico tools show web_search

# Execute tool
aico tools exec web_search --query "AICO AI companion"
```

---

#### `aico skills`
**Purpose**: Agency skills inspection and live execution

**Subcommands:**
- `ls` - List all available skills
- `show <skill_name>` - Show skill details
- `exec <skill_name>` - Execute skill

**Common Usage:**
```bash
# List skills
aico skills ls

# Show skill details
aico skills show conversation_skill

# Execute skill
aico skills exec conversation_skill --input "Hello"
```

---

### Deployment & Development

#### `aico deploy`
**Purpose**: Deployment orchestration for PostgreSQL/InfluxDB backends

**Subcommands:**
- `postgres` - Deploy PostgreSQL container
- `influx` - Deploy InfluxDB container
- `loki` - Deploy Loki container
- `grafana` - Deploy Grafana container
- `status` - Deployment status
- `stop` - Stop all containers
- `restart` - Restart containers
- `logs <service>` - View service logs

**Common Usage:**
```bash
# Deploy PostgreSQL
aico deploy postgres

# Deploy full stack
aico deploy postgres
aico deploy loki
aico deploy influx

# Check deployment status
aico deploy status

# View logs
aico deploy logs postgres
```

---

#### `aico dev`
**Purpose**: Development utilities (data cleanup, security reset)

**Subcommands:**
- `reset-security` - Reset security credentials
- `clear-data` - Clear all data (with confirmation)
- `seed-data` - Seed test data
- `benchmark` - Run benchmarks
- `test-bus` - Test message bus
- `test-db` - Test database connections

**Common Usage:**
```bash
# Reset security (development only)
aico dev reset-security --confirm

# Clear all data
aico dev clear-data --confirm

# Test message bus
aico dev test-bus
```

---

#### `aico bus`
**Purpose**: Message bus testing, monitoring, and management

**Subcommands:**
- `status` - Message bus status
- `test` - Test message bus connectivity
- `publish <topic>` - Publish test message
- `subscribe <topic>` - Subscribe to topic
- `stats` - Bus statistics
- `monitor` - Real-time message monitoring

**Common Usage:**
```bash
# Check bus status
aico bus status

# Test connectivity
aico bus test

# Monitor messages
aico bus monitor --topic "conversation.*"

# Publish test message
aico bus publish test.topic --data '{"test": true}'
```

---

## Global Options

All commands support these global options:

- `--help`, `-h` - Show help message
- `--version` - Show version information

---

## Authentication

Many commands require authentication. Use the gateway auth system:

```bash
# Login (generates JWT token, stored in keyring)
aico gateway auth login

# Check auth status
aico gateway auth status

# Logout
aico gateway auth logout
```

JWT tokens are stored securely in the system keychain and have a 24-hour expiry.

---

## Configuration Files

The CLI reads configuration from:

```
config/
├── schemas/          # JSON schemas for validation
├── defaults/         # Default configuration files
│   ├── system.yaml
│   ├── api_gateway.yaml
│   ├── postgres.yaml
│   ├── influx.yaml
│   ├── logging.yaml
│   └── ...
├── environments/     # Environment-specific overrides
└── user/            # User-specific overrides
```

Configuration hierarchy (highest priority first):
1. Runtime changes (stored in `runtime.yaml`)
2. Environment variables
3. User configuration files
4. Environment configuration files
5. Default values

---

## Common Workflows

### Initial Setup

```bash
# 1. Set up security
aico security setup

# 2. Store database credentials
aico security pg-set
aico security influx-set

# 3. Initialize database
aico pg init

# 4. Start services
aico gateway start
aico modelservice start

# 5. Authenticate CLI
aico gateway auth login
```

### Daily Operations

```bash
# Check system health
aico pg status
aico gateway status
aico modelservice status

# View recent logs
aico logs tail --last 100

# Monitor scheduler
aico scheduler ls
```

### Debugging

```bash
# Check configuration
aico config validate

# Test database connection
aico pg test

# Test message bus
aico bus test

# View security status
aico security status

# Check gateway connectivity
aico gateway test
```

### Data Management

```bash
# Export configuration
aico config export > config-backup.yaml

# Export knowledge graph
aico kg export > kg-backup.json

# Backup database
aico pg exec "SELECT * FROM users" > users-backup.sql
```

---

## Best Practices

### Security
- Always use `aico security setup` for initial configuration
- Store credentials via `aico security pg-set` and `influx-set` (never hardcode)
- Use `aico gateway auth login` for CLI authentication
- Regularly check `aico security status`

### Configuration
- Validate config after changes: `aico config validate`
- Use environment-specific configs for dev/staging/prod
- Keep sensitive values in keyring, not config files

### Monitoring
- Use `aico logs tail` for real-time monitoring
- Set up scheduled tasks for maintenance: `aico scheduler ls`
- Check service status regularly: `aico gateway status`, `aico pg status`

### Development
- Use `aico dev` commands only in development environments
- Test changes with `aico bus test` and `aico gateway test`
- Clear data between tests: `aico dev clear-data --confirm`

---

## Troubleshooting

### Command Not Found
```bash
# Ensure CLI is installed
uv pip install -e .

# Check installation
which aico
aico --help
```

### Authentication Failures
```bash
# Re-authenticate
aico gateway auth logout
aico gateway auth login

# Check session
aico security session
```

### Database Connection Issues
```bash
# Check database status
aico pg status

# Test connection
aico pg test

# Verify credentials
aico security pg-env --format env
```

### Service Not Running
```bash
# Check service status
aico gateway status
aico modelservice status

# Restart service
aico gateway restart
```

---

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Invalid arguments
- `3` - Authentication failure
- `4` - Connection failure

---

## Platform Support

The CLI is tested and supported on:
- **macOS** 12+ (Intel and Apple Silicon)
- **Linux** (Ubuntu 20.04+, Debian 11+, RHEL 8+)
- **Windows** 10/11 (via WSL2 or native)

Platform-specific features:
- **Keyring**: Uses native secure storage (Keychain on macOS, Secret Service on Linux, Credential Manager on Windows)
- **Unicode**: Full emoji and Unicode support on all platforms
- **Colors**: Rich terminal colors with fallback for limited terminals

---

## Further Documentation

- [Interactions Commands](interactions-commands.md) - Detailed interaction testing documentation
- [Configuration Management](../architecture/configuration-management.md) - Configuration system architecture
- [Security](../architecture/architecture-overview.md#privacy-security) - Security architecture
- [API Documentation](../api/interactions-api.md) - REST API reference

---

## Version

CLI Version: 1.1.0  
Last Updated: 2026-02-16
