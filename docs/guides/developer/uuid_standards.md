# UUID Standards for AICO Architecture

## Core Principle

**All system elements in AICO must use strong UUIDs (UUID4) as primary identifiers, never human-readable names or sequential IDs.**

## UUID Usage Standards

### Required UUID Fields

**Family Members:**
- `family_member_uuid` - Primary identifier for family members
- Never use `user_id` as string or `name` as primary key

**System Elements:**
- `session_uuid` - Session identifiers
- `conversation_uuid` - Conversation thread identifiers  
- `message_uuid` - Individual message identifiers
- `plugin_uuid` - Plugin instance identifiers
- `device_uuid` - Device registration identifiers

### Database Schema Standards

**✅ Correct UUID Usage:**
```sql
CREATE TABLE family_members (
    uuid TEXT PRIMARY KEY,  -- UUID4 as primary key
    full_name TEXT NOT NULL,
    relationship TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversations (
    uuid TEXT PRIMARY KEY,
    family_member_uuid TEXT NOT NULL,
    content TEXT,
    timestamp TIMESTAMP,
    FOREIGN KEY (family_member_uuid) REFERENCES family_members(uuid)
);
```

**❌ Incorrect Usage:**
```sql
-- Don't use names as IDs
CREATE TABLE users (
    username TEXT PRIMARY KEY,  -- WRONG
    user_id INTEGER PRIMARY KEY  -- WRONG
);
```

### API Standards

**✅ Correct API Patterns:**
- `GET /api/v1/family/{family_member_uuid}`
- `POST /api/v1/conversations/{conversation_uuid}/messages`
- `DELETE /api/v1/sessions/{session_uuid}`

**❌ Incorrect API Patterns:**
- `GET /api/v1/users/{username}` - Don't use names in URLs
- `GET /api/v1/users/{user_id}` - Don't use sequential IDs

### JWT Token Standards

**✅ Correct JWT Payload:**
```json
{
  "sub": "family_member_uuid",
  "family_member_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Sarah Johnson",
  "relationship": "daughter",
  "session_uuid": "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
}
```

### Message Bus Standards

**✅ Correct Message Metadata:**
```json
{
  "metadata": {
    "message_uuid": "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
    "family_member_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "session_uuid": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

## Implementation Guidelines

### UUID Generation
- **Use UUID4** (random) for all new identifiers
- **Generate server-side** - never trust client-generated UUIDs for security
- **Store as TEXT** in databases for cross-platform compatibility

### Lookup Patterns
- **Primary lookups by UUID** for all database operations
- **Secondary lookups by name** only for user-facing operations (login)
- **Index both UUID and name** for performance

### Migration Strategy
- **Audit existing code** for `user_id`, `username`, or sequential ID usage
- **Replace with UUID fields** in database schemas
- **Update API endpoints** to use UUID parameters
- **Maintain backward compatibility** during transition

## Security Benefits

**Strong Identifiers:**
- **Non-enumerable** - Can't guess valid UUIDs
- **Non-sequential** - No information leakage about system scale
- **Collision-resistant** - Extremely low probability of duplicates
- **Cross-system safe** - Can be used across distributed components

**Privacy Protection:**
- **No personal information** in identifiers
- **Anonymous references** in logs and audit trails
- **Safe for external APIs** without exposing internal structure

## Documentation Updates Required

Based on audit, these files need UUID standardization:

1. **docs/instrumentation/instrumentation_logging.md** - Replace `user_id` with `family_member_uuid`
2. **docs/security/audit.md** - Update user references to use UUIDs
3. **docs/architecture/data_layer.md** - Standardize all user references to family_member_uuid
4. **docs/developer-guide/schema_management.md** - Update all examples to use UUIDs
5. **docs/architecture/integration_msg.md** - Replace user_id with family_member_uuid
6. **docs/architecture/personality_sim_msg.md** - Update user references

## Compliance Checklist

**✅ Database Schemas:**
- [ ] All tables use UUID primary keys
- [ ] Foreign keys reference UUIDs
- [ ] Indexes created on UUID fields

**✅ API Endpoints:**
- [ ] All URLs use UUID parameters
- [ ] JWT tokens contain UUIDs
- [ ] Response payloads use UUIDs

**✅ Message Bus:**
- [ ] All message metadata uses UUIDs
- [ ] Topic routing based on UUIDs
- [ ] Audit logs reference UUIDs

**✅ Documentation:**
- [ ] All examples use UUIDs
- [ ] API documentation updated
- [ ] Schema examples corrected

---

*This standard ensures AICO maintains strong, secure, and privacy-preserving identifiers across all system components while supporting the family member recognition architecture.*
