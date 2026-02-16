# Interaction System REST API Documentation

## Base URL

```
http://<api_gateway_host>:<port>/api/v1
```

## Authentication

All endpoints require JWT authentication via Bearer token:

```
Authorization: Bearer <jwt_token>
```

## Endpoints

### Get Interaction Details

Retrieve a specific interaction with full event timeline.

```http
GET /interactions/{interaction_id}
```

**Path Parameters:**
- `interaction_id` (string, required): UUID of the interaction

**Response 200:**
```json
{
  "interaction": {
    "interaction_id": "uuid",
    "user_id": "uuid",
    "correlation_id": "uuid",
    "interaction_type": "question|choice|dialogue|approval|ack",
    "status": "pending|answered|approved|rejected|dismissed|deferred|expired|cancelled",
    "prompt": "string",
    "title": "string",
    "requirement": "required|optional",
    "severity": "low|medium|high",
    "category": "string",
    "expected_answer_type": "string",
    "allowed_options": ["string"],
    "answer_text": "string",
    "answer_json": {},
    "answered_at": "ISO8601",
    "expires_at": "ISO8601",
    "idempotency_key": "string",
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  },
  "events": [
    {
      "event_id": "uuid",
      "interaction_id": "uuid",
      "user_id": "uuid",
      "correlation_id": "uuid",
      "actor": "user:uuid|system:name",
      "event_type": "created|answered|approved|rejected|cancelled|dismissed|deferred|expired",
      "from_status": "string",
      "to_status": "string",
      "payload_json": {},
      "created_at": "ISO8601"
    }
  ]
}
```

**Response 404:**
```json
{
  "detail": "interaction not found"
}
```

**Response 410:**
```json
{
  "detail": "interaction expired"
}
```

---

### List Interactions

List interactions with optional filtering.

```http
GET /interactions
```

**Query Parameters:**
- `status` (string, optional; repeatable): Filter by status
  - terminal statuses: `answered`, `approved`, `rejected`, `cancelled`, `expired`
- `interaction_type` (string, optional; repeatable): Filter by type (`question|choice|dialogue|approval|ack`)
- `category` (string, optional; repeatable): Filter by category
- `created_after` (ISO8601 datetime, optional): Filter by creation time lower bound
- `created_before` (ISO8601 datetime, optional): Filter by creation time upper bound
- `limit` (integer, optional): Maximum number of results (default: 50, max: 200)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response 200:**
```json
{
  "items": [
    {
      "interaction_id": "uuid",
      "user_id": "uuid",
      "correlation_id": "uuid",
      "interaction_type": "question",
      "status": "pending",
      "requirement": "required",
      "severity": "medium",
      "created_at": "ISO8601",
      "updated_at": "ISO8601"
    }
  ],
  "total": 42
}
```

---

### Answer Interaction

Answer a question, choice, or dialogue interaction.

```http
POST /interactions/{interaction_id}/answer
```

**Path Parameters:**
- `interaction_id` (string, required): UUID of the interaction

**Request Body:**
```json
{
  "answer_text": "string (optional)",
  "answer_json": {} // optional, for structured answers
}
```

**Validation:**
- At least one of `answer_text` or `answer_json` must be provided
- Only valid for `question`, `choice`, or `dialogue` interaction types
- Interaction must be in `pending` status

**Response 200:**
```json
{
  "interaction": {
    "interaction_id": "uuid",
    "status": "answered",
    "answer_text": "string",
    "answered_at": "ISO8601",
    ...
  },
  "event": {
    "event_id": "uuid",
    "event_type": "answered",
    "actor": "user:uuid",
    "from_status": "pending",
    "to_status": "answered",
    ...
  }
}
```

**Response 400:**
```json
{
  "detail": "answer required"
}
```

**Response 422:**
```json
{
  "detail": "interaction type not answerable"
}
```

---

### Approve Interaction

Approve an approval interaction.

```http
POST /interactions/{interaction_id}/approve
```

**Path Parameters:**
- `interaction_id` (string, required): UUID of the interaction

**Validation:**
- Only valid for `approval` interaction type
- Interaction must be in `pending` status

**Response 200:**
```json
{
  "interaction": {
    "interaction_id": "uuid",
    "status": "approved",
    ...
  },
  "event": {
    "event_id": "uuid",
    "event_type": "approved",
    "actor": "user:uuid",
    "from_status": "pending",
    "to_status": "approved",
    ...
  }
}
```

**Response 422:**
```json
{
  "detail": "interaction type not approvable"
}
```

---

### Reject Interaction

Reject an approval interaction.

```http
POST /interactions/{interaction_id}/reject
```

**Path Parameters:**
- `interaction_id` (string, required): UUID of the interaction

**Validation:**
- Only valid for `approval` interaction type
- Interaction must be in `pending` status

**Response 200:**
```json
{
  "interaction": {
    "interaction_id": "uuid",
    "status": "rejected",
    ...
  },
  "event": {
    "event_id": "uuid",
    "event_type": "rejected",
    "actor": "user:uuid",
    "from_status": "pending",
    "to_status": "rejected",
    ...
  }
}
```

**Response 422:**
```json
{
  "detail": "interaction type not rejectable"
}
```

---

### Cancel Interaction

Cancel any pending interaction.

```http
POST /interactions/{interaction_id}/cancel
```

**Path Parameters:**
- `interaction_id` (string, required): UUID of the interaction

**Validation:**
- Interaction must be in `pending` status

**Response 200:**
```json
{
  "interaction": {
    "interaction_id": "uuid",
    "status": "cancelled",
    ...
  },
  "event": {
    "event_id": "uuid",
    "event_type": "cancelled",
    "actor": "user:uuid",
    "from_status": "pending",
    "to_status": "cancelled",
    ...
  }
}
```

---

## Admin Endpoints

### Simulate Interaction

Create test interactions for development and testing.

```http
POST /admin/interactions/simulate
```

**Authentication:** Requires admin role

**Request Body:**
```json
{
  "user_id": "uuid (required)",
  "interaction_type": "question|choice|dialogue|approval (required)",
  "prompt": "string (required)",
  "title": "string (optional)",
  "severity": "low|medium|high (default: medium)",
  "requirement": "required|optional (default: required)",
  "category": "string (optional)",
  "expected_answer_type": "string (optional)",
  "allowed_options": ["string"] // required for choice type,
  "expires_in_seconds": 3600 // optional,
  "scenario": "create_only|create_then_answer|create_then_cancel (optional)",
  "answer_text": "string (required if scenario=create_then_answer)",
  "answer_json": {} // optional,
  "broadcast_admin": false // optional
}
```

**Response 200:**
```json
{
  "interaction": {
    "interaction_id": "uuid",
    "status": "pending|answered|cancelled",
    ...
  },
  "event": {
    "event_id": "uuid",
    "event_type": "created",
    ...
  },
  "scenario_executed": "create_then_answer",
  "additional_events": [
    {
      "event_id": "uuid",
      "event_type": "answered",
      ...
    }
  ]
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Validation error message"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Interaction not found"
}
```

### 409 Conflict
```json
{
  "detail": "Interaction already in terminal state"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": "Invalid interaction type for this operation"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## State Transitions

### Valid Status Transitions

```
pending → answered (question, choice, dialogue)
pending → approved (approval)
pending → rejected (approval)
pending → cancelled (all types)
pending → expired (all types, automatic)
```

### Terminal States

Once an interaction reaches any of these states, no further transitions are allowed:
- `answered`
- `approved`
- `rejected`
- `cancelled`
- `expired`

---

## Message Bus Integration

All state transitions publish notifications to:

```
Topic: interaction.notifications.<user_uuid>
Format: Protobuf (AicoMessage with Struct payload)
```

**Payload Structure:**
```json
{
  "interaction": {
    "interaction_id": "uuid",
    "user_id": "uuid",
    "interaction_type": "question",
    "status": "answered",
    ...
  },
  "event": {
    "event_id": "uuid",
    "event_type": "answered",
    "actor": "user:uuid",
    ...
  }
}
```

---

## Examples

### Create and Answer Question

```bash
# 1. Simulate question (admin)
curl -X POST http://localhost:<port>/api/v1/admin/interactions/simulate \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid",
    "interaction_type": "question",
    "prompt": "What is your favorite color?",
    "title": "Color Preference",
    "severity": "low",
    "requirement": "optional"
  }'

# 2. Answer question (user)
curl -X POST http://localhost:<port>/api/v1/interactions/interaction-uuid/answer \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "answer_text": "Blue"
  }'
```

### List Pending Interactions

```bash
curl -X GET "http://localhost:<port>/api/v1/interactions?status=pending&limit=10" \
  -H "Authorization: Bearer $USER_TOKEN"
```

### Approve/Reject Approval Request

```bash
# Approve
curl -X POST http://localhost:<port>/api/v1/interactions/interaction-uuid/approve \
  -H "Authorization: Bearer $USER_TOKEN"

# Reject
curl -X POST http://localhost:<port>/api/v1/interactions/interaction-uuid/reject \
  -H "Authorization: Bearer $USER_TOKEN"
```
