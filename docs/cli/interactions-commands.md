# CLI Interaction Commands Documentation

## Overview

The `aico interactions` command group provides comprehensive testing and management tools for the interaction system.

## Commands

### simulate

Create test interactions with optional WebSocket validation.

```bash
aico interactions simulate <type> [OPTIONS]
```

**Interaction Types:**
- `question` - Ask user a question requiring text answer
- `choice` - Present user with multiple choice options
- `dialogue` - Initiate a conversation/discussion
- `approval` - Request user approval/rejection

**Common Options:**

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--user`, `-u` | UUID | Yes | User UUID for the interaction |
| `--prompt`, `-p` | String | Yes | The interaction prompt/question |
| `--title`, `-t` | String | No | Title for the interaction |
| `--severity`, `-s` | Enum | No | Severity level: low, medium, high (default: medium) |
| `--requirement`, `-r` | Enum | No | Requirement: required, optional (default: required) |
| `--category`, `-c` | String | No | Category for organization |
| `--listen-ws` | Flag | No | Enable WebSocket listener for end-to-end validation |
| `--ws-timeout` | Integer | No | WebSocket timeout in seconds (default: 10) |

**Type-Specific Options:**

**Question:**
- `--answer-type`, `-a` - Expected answer type (text, yes_no, number, date, choice)

**Choice:**
- `--options`, `-o` - Comma-separated list of allowed options (required for choice type)

**Scenario Options:**
- `--scenario` - Execution scenario: create_only, create_then_answer, create_then_cancel
- `--answer` - Answer text (required if scenario=create_then_answer)

**Examples:**

```bash
# Simple question
aico interactions simulate question \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --prompt "What is your favorite programming language?" \
  --title "Language Preference" \
  --severity medium

# Question with WebSocket validation
aico interactions simulate question \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --prompt "What is your preferred IDE?" \
  --listen-ws \
  --ws-timeout 15

# Choice interaction
aico interactions simulate choice \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --prompt "Which database do you prefer?" \
  --options "PostgreSQL,MySQL,MongoDB,SQLite" \
  --severity high

# Approval request
aico interactions simulate approval \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --prompt "Deploy v2.5.0 to production?" \
  --title "Production Deployment" \
  --severity high \
  --requirement required

# Dialogue initiation
aico interactions simulate dialogue \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --prompt "Let's discuss the new feature architecture" \
  --title "Architecture Discussion" \
  --severity medium

# Auto-answer scenario
aico interactions simulate question \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --prompt "Test question" \
  --scenario create_then_answer \
  --answer "Test answer"

# Auto-cancel scenario
aico interactions simulate question \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --prompt "Test question" \
  --scenario create_then_cancel
```

---

### reply

Reply to an existing interaction.

```bash
aico interactions reply <interaction_id> [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--answer`, `-a` | String | Answer text (for question/choice/dialogue) |
| `--answer-json` | JSON | Structured answer (for question/choice/dialogue) |
| `--approve` | Flag | Approve the interaction (for approval type) |
| `--reject` | Flag | Reject the interaction (for approval type) |
| `--cancel` | Flag | Cancel the interaction (any type) |
| `--listen-ws` | Flag | Enable WebSocket listener for notification |
| `--ws-timeout` | Integer | WebSocket timeout in seconds (default: 10) |

**Reply Types:**

**Answer (question/choice/dialogue):**
```bash
aico interactions reply <id> --answer "My answer text"
```

**Approve (approval):**
```bash
aico interactions reply <id> --approve
```

**Reject (approval):**
```bash
aico interactions reply <id> --reject
```

**Cancel (any type):**
```bash
aico interactions reply <id> --cancel
```

**Examples:**

```bash
# Answer a question
aico interactions reply d926f067-96ad-40b3-ad54-e5c13d0c0329 \
  --answer "Python is my favorite language"

# Answer with WebSocket validation
aico interactions reply d926f067-96ad-40b3-ad54-e5c13d0c0329 \
  --answer "Python" \
  --listen-ws

# Approve an approval request
aico interactions reply 7deeafd5-19bc-487c-847a-a7ea065b3c2e \
  --approve

# Reject an approval request
aico interactions reply 235576d9-03eb-466c-993d-00732fd05c09 \
  --reject

# Cancel any interaction
aico interactions reply 9b4db2b8-8a77-4598-821e-f02a6a9d4cd8 \
  --cancel
```

---

### get

Get detailed information about a specific interaction including event timeline.

```bash
aico interactions get <interaction_id>
```

**Output:**
- Full interaction details
- Complete event timeline with timestamps
- All state transitions

**Example:**

```bash
aico interactions get d926f067-96ad-40b3-ad54-e5c13d0c0329
```

**Output:**
```
Interaction Details

   Interaction ID     d926f067-96ad-40b3-ad54-e5c13d0c0329
   User ID            1e69de47-a3af-4343-8dba-dbf5dcf5f160
   Type               question
   Status             answered
   Prompt             What is your preferred code review process?
   Answer             Pull request with at least 2 reviewers...
   Created            2026-02-07T23:45:26Z
   Updated            2026-02-07T23:45:38Z

Event Timeline (2 events)

   Event ID       Type       Actor                    Transition
   ─────────────────────────────────────────────────────────────
   95c63882...    created    system:simulator         → pending
   c8a4a9e8...    answered   user:1e69de47...         pending → answered
```

---

### list

List interactions with optional filtering.

```bash
aico interactions list [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--user`, `-u` | UUID | Filter by user UUID |
| `--status`, `-s` | Enum | Filter by status (pending, answered, approved, rejected, cancelled, expired) - can specify multiple |
| `--type`, `-t` | Enum | Filter by type (question, choice, dialogue, approval) - can specify multiple |
| `--category`, `-c` | String | Filter by category - can specify multiple |
| `--limit`, `-l` | Integer | Maximum results (default: 50) |
| `--format`, `-f` | Enum | Output format: table, json (default: table) |

**Examples:**

```bash
# List all interactions for a user
aico interactions list --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160

# List only pending interactions
aico interactions list \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --status pending

# List by category
aico interactions list \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --category general

# List with limit
aico interactions list \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --limit 20

# JSON output
aico interactions list \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --format json
```

**Output (table format):**
```
Interaction Requests (3 found)

1. d926f067-96ad-40b3-ad54-e5c13d0c0329
  User: 1e69de47-a3af-4343-8dba-dbf5dcf5f160
  Type: question
  Status: answered
  Requirement: required
  Severity: medium
  Category: general
  Prompt: What is your favorite programming language?
  Created: 2026-02-07T23:45:26Z

2. 7deeafd5-19bc-487c-847a-a7ea065b3c2e
  User: 1e69de47-a3af-4343-8dba-dbf5dcf5f160
  Type: approval
  Status: approved
  ...
```

---

## WebSocket Listener (`--listen-ws`)

### What It Does

The `--listen-ws` flag enables end-to-end validation of the complete interaction pipeline:

1. **Spawns background thread** with dedicated event loop
2. **Connects** to WebSocket at `ws://localhost:8772/ws`
3. **Authenticates** using JWT token from keychain
4. **Subscribes** to `interaction.notifications.<user_uuid>`
5. **Waits** for broadcast message containing interaction data
6. **Validates** complete flow: Database → Message Bus → WebSocket → Client

### When to Use

- **Development**: Verify end-to-end pipeline is working
- **Testing**: Validate WebSocket notifications are delivered
- **Debugging**: Confirm message bus publishing is functioning
- **CI/CD**: Automated integration tests

### Output

When WebSocket notification is received:
```
WebSocket Listener
✓ WebSocket authenticated
✓ Subscribed to: interaction.notifications.<user_uuid>
✓ Received notification!
✓ End-to-end test successful!
Topic: interaction.notifications.<user_uuid>
```

When notification is not received:
```
WebSocket Listener
⚠ No notification received within 15s
⚠ Interaction created but WebSocket notification not received
Check that API Gateway WebSocket adapter is running
```

---

## Authentication

All commands require authentication. Authenticate first:

```bash
aico gateway auth login
```

This generates and stores a JWT token with admin privileges for 7 days.

---

## Common Workflows

### Complete Test Flow

```bash
# 1. Create interaction with WebSocket validation
aico interactions simulate question \
  --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160 \
  --prompt "What's your favorite editor?" \
  --listen-ws

# 2. Reply to the interaction
aico interactions reply <interaction_id> \
  --answer "VS Code"

# 3. View complete timeline
aico interactions get <interaction_id>

# 4. List all interactions
aico interactions list --user 1e69de47-a3af-4343-8dba-dbf5dcf5f160
```

### Testing All Interaction Types

```bash
# Question
aico interactions simulate question \
  --user <uuid> \
  --prompt "Test question?" \
  --listen-ws

# Choice
aico interactions simulate choice \
  --user <uuid> \
  --prompt "Choose one:" \
  --options "A,B,C" \
  --listen-ws

# Dialogue
aico interactions simulate dialogue \
  --user <uuid> \
  --prompt "Let's discuss..." \
  --listen-ws

# Approval
aico interactions simulate approval \
  --user <uuid> \
  --prompt "Approve this?" \
  --listen-ws
```

### Scenario Testing

```bash
# Test auto-answer
aico interactions simulate question \
  --user <uuid> \
  --prompt "Auto test" \
  --scenario create_then_answer \
  --answer "Auto answer" \
  --listen-ws

# Test auto-cancel
aico interactions simulate question \
  --user <uuid> \
  --prompt "Cancel test" \
  --scenario create_then_cancel \
  --listen-ws
```

---

## Troubleshooting

### WebSocket Connection Fails

```bash
# Check backend is running
ps aux | grep "python.*backend/main.py"

# Check API Gateway logs
aico logs tail --last 50 | grep -i websocket
```

### Authentication Fails

```bash
# Re-authenticate
aico gateway auth login

# Verify token exists
aico gateway auth status
```

### No Notifications Received

```bash
# Check message bus is running
aico logs tail --last 50 | grep -i "message bus"

# Check WebSocket adapter subscribed
aico logs tail --last 50 | grep -i "Subscribed to interaction"
```

---

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Invalid arguments

---

## Configuration

WebSocket connection settings are read from `config/defaults/api_gateway.yaml`:

```yaml
api_gateway:
  protocols:
    websocket:
      enabled: true
      port: 8772
      path: "/ws"
```

The CLI uses JWT tokens stored in the system keychain for authentication. Run `aico gateway auth login` to authenticate before using interaction commands.
