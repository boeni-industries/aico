# Tenant-Scoped NATS Subjects Implementation

## Overview
Implemented tenant-scoped NATS subject namespacing for security and isolation in multi-tenant deployments.

## Architecture

### Subject Pattern
```
aico.<tenant_id>.<domain>.<action>
```

**Examples:**
- `aico.tenant-123.conversation.stream` (ephemeral chunks)
- `aico.tenant-123.conversation.responses` (durable final responses)
- `aico.tenant-123.interaction.notifications` (ephemeral events)

### Design Decisions

**1. Tenant ID in Subject (not just attributes)**
- **Why:** Infrastructure-level isolation, NATS ACL support, prevents cross-tenant leakage
- **Implementation:** Transparent injection in `MessageBusClient._topic_to_subject()`

**2. User ID in Attributes (not subject)**
- **Why:** Prevents subject explosion (10K+ users per tenant)
- **Performance:** One subscription per tenant vs per-user
- **Filtering:** Application-layer user routing (Gateway WebSocket adapter)

**3. Single-Tenant Mode**
- Uses `tenant_id = "default"` for consistency
- Same code paths for local and multi-tenant deployments

## Implementation Details

### MessageBusClient Changes

**1. Subject Conversion with Tenant Scoping**
```python
def _topic_to_subject(self, topic: str, tenant_id: Optional[str] = None) -> str:
    subject = topic.replace("/", ".")
    if tenant_id and not subject.startswith("aico."):
        subject = f"aico.{tenant_id}.{subject}"
    return subject
```

**2. Automatic Injection in publish()**
```python
# Extract tenant_id from attributes
tenant_id = attributes.get("tenant_id") if attributes else None
subject = self._topic_to_subject(topic, tenant_id=tenant_id)
```

**3. Scoped Subscriptions**
```python
async def subscribe(self, topic_pattern: str, callback, tenant_id: Optional[str] = None):
    base_subject = self._pattern_to_subject(topic_pattern)
    if tenant_id and not base_subject.startswith("aico."):
        subject = f"aico.{tenant_id}.{base_subject}"
```

### JetStream Stream Updates

**OUTBOX_EVENTS Stream:**
```python
subjects=["aico.*.conversation.>", "aico.*.interaction.>"]
```

**INTERACTION_NOTIFICATIONS Stream:**
```python
subjects=["aico.*.interaction.notifications.>"]
```

**AUDIT_EVENTS Stream:**
```python
subjects=["audit.events.>"]  # Not tenant-scoped (system-wide audit)
```

## Usage Patterns

### Publishing with Tenant Scope
```python
await bus_client.publish(
    "conversation.stream",
    message,
    attributes={
        "tenant_id": "tenant-123",  # Automatically scoped to aico.tenant-123.conversation.stream
        "user_id": "user-456"       # Stays in attributes for app-layer routing
    }
)
```

### Subscribing with Tenant Scope
```python
# Gateway subscribes per-tenant (efficient)
await bus_client.subscribe(
    "conversation.responses",
    handler=self._route_to_websockets,
    tenant_id="tenant-123"  # Subscribes to aico.tenant-123.conversation.responses
)
```

### Application-Layer User Filtering
```python
async def _route_to_websockets(self, msg):
    user_id = msg.metadata.attributes.get("user_id")
    if user_id in self.active_connections:
        await self.send_to_user(user_id, msg.data)
```

## Migration Path

### Phase 1: Infrastructure (COMPLETE)
- ✅ Updated `MessageBusClient` with transparent tenant injection
- ✅ Updated JetStream stream configurations
- ✅ Backward compatible (works without tenant_id)

### Phase 2: Application Updates (NEXT)
- [ ] Ensure all publish/subscribe calls pass `tenant_id` in attributes
- [ ] Update conversation_engine to include tenant_id
- [ ] Update gateway WebSocket adapter for tenant-scoped subscriptions
- [ ] Update modelservice handlers

### Phase 3: Enforcement (FUTURE)
- [ ] Make `tenant_id` mandatory (remove Optional)
- [ ] Add validation to reject messages without tenant_id
- [ ] Configure NATS ACLs for production

## Benefits

**Security:**
- Infrastructure-level tenant isolation
- NATS ACL support for authorization
- Prevents accidental cross-tenant subscriptions

**Performance:**
- Efficient wildcard subscriptions per-tenant
- No subject explosion (user_id in attributes)
- Scalable to 10K+ users per tenant

**Operational:**
- Per-tenant traffic monitoring at NATS level
- Easier debugging (tenant visible in subject)
- Future-proof for NATS authorization features

## Testing

### Verify Tenant Isolation
```python
# Publish to tenant-123
await bus_client.publish("conversation.responses", msg, attributes={"tenant_id": "tenant-123"})

# Subscribe to tenant-456 (should NOT receive tenant-123 messages)
await bus_client.subscribe("conversation.responses", handler, tenant_id="tenant-456")
```

### Verify Backward Compatibility
```python
# Without tenant_id (for single-tenant local mode)
await bus_client.publish("conversation.responses", msg)  # Works, no scoping
```

## Next Steps

1. **Update conversation_engine.py** - Ensure tenant_id passed in all publish calls
2. **Update gateway WebSocket adapter** - Use tenant-scoped subscriptions
3. **Add integration tests** - Verify tenant isolation
4. **Document for developers** - Update API docs with tenant_id requirements
