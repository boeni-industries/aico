# Scheduler CLI Trigger Authentication

## Overview

The `aico scheduler trigger` command uses **JWT service token authentication** to manually trigger scheduled tasks via the API Gateway.

## Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User runs: aico scheduler trigger <task_id>              │
│    - @sensitive decorator prompts for master password       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CLI retrieves JWT token                                  │
│    - AICOKeyManager.get_jwt_token("api_gateway")            │
│    - Token signed with master key                           │
│    - Contains user identity and permissions                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. CLI sends authenticated HTTP request                     │
│    POST /api/v1/scheduler/tasks/{task_id}/trigger           │
│    Headers:                                                  │
│      - Authorization: Bearer <JWT>                           │
│      - Idempotency-Key: <UUID>                               │
│      - Content-Type: application/json                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. API Gateway validates request                            │
│    - Encryption middleware: skips encryption (JWT auth)     │
│    - Idempotency middleware: validates JWT + idempotency    │
│    - REST adapter: forwards to NATS client                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. NATS request to scheduler                                │
│    - Subject: scheduler.task.trigger                        │
│    - Payload: {"task_id": "<task_id>"}                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Scheduler queues task for execution                      │
│    - Task runs on next scheduler tick (1 second interval)   │
│    - Execution logged to scheduler_task_executions          │
└─────────────────────────────────────────────────────────────┘
```

## Security Features

### 1. Authentication
- **JWT token** signed by master key
- Token contains user identity and permissions
- Token expiry enforced (24-hour default)
- Automatic token refresh on expiry

### 2. Authorization
- User identity logged for audit trail
- Future RBAC support (task-level permissions)
- Token scopes can restrict operations

### 3. Idempotency
- **Idempotency-Key** prevents duplicate triggers
- Middleware tracks requests by key + auth token hash
- 24-hour TTL for idempotency records
- Prevents accidental double-execution

### 4. Audit Trail
- User identity in JWT claims logged
- Request ID for tracing
- Execution ID links trigger to task run
- Full audit trail from CLI → Gateway → Scheduler → Execution

## Implementation Details

### CLI Command (`cli/commands/scheduler.py`)

```python
@app.command("trigger")
@sensitive  # Prompts for master password
def trigger_task(task_id: str):
    # Get JWT token from AICOKeyManager
    config_manager = ConfigurationManager()
    config_manager.initialize()
    key_manager = AICOKeyManager(config_manager)
    jwt_token = key_manager.get_jwt_token("api_gateway")
    
    # Send authenticated request
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Idempotency-Key": str(uuid.uuid4()),
        "Content-Type": "application/json"
    }
    
    response = client.post(
        f"{base_url}/api/v1/scheduler/tasks/{task_id}/trigger",
        headers=headers,
        json={}
    )
```

### API Gateway Endpoint (`backend/api_gateway/adapters/rest_adapter.py`)

```python
@self.app.post(f"{prefix}/scheduler/tasks/{{task_id}}/trigger")
async def trigger_scheduler_task(task_id: str):
    """Manually trigger a scheduler task to run immediately"""
    nats_client = GatewayNATSClient()
    await nats_client.connect()
    
    result = await nats_client.request_scheduler_task_trigger(task_id)
    
    return {
        "success": result.get("success"),
        "message": f"Task '{task_id}' triggered successfully",
        "task_id": task_id
    }
```

### Middleware Configuration

**Encryption Middleware** (`backend/api_gateway/middleware/encryption.py`):
```python
def _should_skip_encryption(self, request: Request) -> bool:
    # Allow scheduler trigger with JWT auth (no encryption needed)
    if path.startswith("/api/v1/scheduler/tasks/") and path.endswith("/trigger"):
        return True
```

**Idempotency Middleware** (`backend/api_gateway/middleware/idempotency.py`):
```python
# Scheduler trigger endpoint requires:
# 1. Authorization header (JWT token)
# 2. Idempotency-Key header (UUID)
# Both are validated before request proceeds
```

## Usage Examples

### Basic Trigger
```bash
$ aico scheduler trigger maintenance.run_ledger_cleanup
🔐 Sensitive operation: sensitive operation
   Authentication required for security
⠹ Triggering task 'maintenance.run_ledger_cleanup'...
✓ Successfully triggered task 'maintenance.run_ledger_cleanup'
Note: The task will run on the next scheduler check.
```

### Verify Execution
```bash
$ aico scheduler history maintenance.run_ledger_cleanup --limit 1
Execution ID: 0faf7153-7439-4220-912f-9600ed1905fc
Status: Completed
Duration: 0.1s
Result: Run ledger cleanup completed: deleted 0 old run(s)...
```

### Error Handling
```bash
# Task not found
$ aico scheduler trigger invalid.task
✗ Task not found: invalid.task

# Authentication failure
$ aico scheduler trigger maintenance.run_ledger_cleanup
✗ Authentication failed. Please check your credentials.

# Idempotency conflict (duplicate trigger within 24h)
$ aico scheduler trigger maintenance.run_ledger_cleanup
✗ Request already processed (idempotency key conflict)
```

## Comparison with Other CLI Commands

| Command Type | Authentication | Example |
|--------------|----------------|---------|
| **API Gateway (JWT)** | JWT service token | `scheduler trigger`, `interactions *`, `agency *` |
| **Direct DB (@sensitive)** | Master password → DB credentials | `scheduler ls/show/create/update/delete` |
| **Unauthenticated** | None | `modelservice status`, `versions list` |

## Future Enhancements

### 1. RBAC (Role-Based Access Control)
```python
# JWT claims with task permissions
{
  "sub": "user_uuid",
  "scopes": ["scheduler:trigger", "scheduler:read"],
  "task_permissions": {
    "maintenance.*": "trigger",
    "user.custom_task": "trigger"
  }
}
```

### 2. Service Accounts
```bash
# Generate long-lived token for automation
$ aico auth create-service-account scheduler-bot \
  --scopes scheduler:trigger \
  --tasks "maintenance.*"

# Use in CI/CD
export AICO_SERVICE_TOKEN="<token>"
aico scheduler trigger maintenance.run_ledger_cleanup --token $AICO_SERVICE_TOKEN
```

### 3. Multi-Tenancy
```python
# JWT claims with tenant scope
{
  "sub": "user_uuid",
  "tenant_id": "tenant_123",
  "scopes": ["scheduler:trigger"]
}

# Only trigger tasks for user's tenant
```

## Security Considerations

### ✅ Secure
- JWT authentication prevents unauthorized access
- Idempotency prevents duplicate operations
- Audit trail for compliance
- Token expiry limits exposure window
- Master password required for token generation

### ⚠️ Considerations
- JWT tokens valid for 24 hours (configurable)
- Tokens stored in system keyring (secure but accessible to user)
- No rate limiting on trigger endpoint (future enhancement)
- No task-level permissions yet (all authenticated users can trigger any task)

### 🔒 Best Practices
1. **Rotate master password regularly**
2. **Monitor trigger audit logs**
3. **Implement task-level RBAC** (future)
4. **Add rate limiting** for production (future)
5. **Use service accounts** for automation (future)

## Troubleshooting

### Authentication Failures
```bash
# Clear cached credentials
$ aico security logout

# Re-authenticate
$ aico scheduler trigger <task_id>
# Will prompt for master password
```

### Idempotency Conflicts
```bash
# Wait 24 hours for idempotency TTL
# OR use different CLI session (generates new UUID)
```

### Task Not Found
```bash
# List available tasks
$ aico scheduler ls

# Verify task ID spelling
$ aico scheduler show <task_id>
```

## Related Documentation

- [CLI Authentication Patterns](../../cli/cli.md#authentication)
- [API Gateway Architecture](../api-gateway.md)
- [Scheduler Architecture](./scheduling.md)
- [Security & Access Control](../../security/authentication.md)
