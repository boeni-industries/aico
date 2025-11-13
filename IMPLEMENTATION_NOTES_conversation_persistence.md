# Conversation Persistence - Backend Implementation

## Overview
Implemented backend message retrieval functionality to support offline-first conversation persistence in the frontend.

## Changes Made

### 1. Enhanced Message Storage (`shared/aico/ai/memory/manager.py`)

**Added message_id field to stored messages:**
```python
message_data = {
    "message_id": message_id,  # NEW: Unique message identifier
    "user_id": user_id,
    "conversation_id": conversation_id,
    "content": content,
    "role": role,
    "timestamp": datetime.utcnow().isoformat(),
    "message_type": f"{role}_input" if role == "user" else f"{role}_response"
}
```

**Purpose**: Provides stable message IDs for frontend caching and deduplication.

### 2. Completed GET /conversation/messages Endpoint (`backend/api/conversation/router.py`)

**Functionality:**
- Retrieves messages from working memory (LMDB) with 24-hour retention
- Supports pagination (`page`, `page_size`)
- Supports conversation filtering (`conversation_id`)
- Supports timestamp filtering (`since`)
- Returns standardized message format for frontend

**API Response Format:**
```json
{
  "success": true,
  "messages": [
    {
      "id": "uuid",
      "conversation_id": "user_123_timestamp",
      "user_id": "user_123",
      "content": "Message text",
      "role": "user" | "assistant",
      "timestamp": "2024-11-13T14:30:00",
      "message_type": "user_input" | "assistant_response"
    }
  ],
  "conversation_id": "user_123_timestamp",
  "total_count": 10,
  "page": 1,
  "page_size": 50
}
```

**Query Parameters:**
- `page` (int, default=1): Page number for pagination
- `page_size` (int, default=50, max=100): Messages per page
- `conversation_id` (optional): Filter by specific conversation
- `since` (optional): Filter messages after timestamp

**Implementation Details:**
- Uses existing `WorkingMemoryStore.retrieve_conversation_history()` method
- Uses existing `WorkingMemoryStore.retrieve_user_history()` method
- Applies pagination after retrieval (in-memory)
- Formats messages for frontend consumption
- Handles missing memory manager gracefully

### 3. Test Script (`scripts/test_message_retrieval.py`)

Created comprehensive test script with full security stack support:

**Features:**
- JWT authentication with Bearer token
- Proper request/response encryption handling
- Session management
- Comprehensive test coverage

**Test Coverage:**
- Authentication flow (JWT token generation)
- Message sending with encryption
- Message retrieval with authentication
- Pagination functionality
- Conversation filtering
- Timestamp filtering
- Duplicate detection

**Usage:**
```bash
# Set environment variables
export USER_UUID=<your-user-uuid>
export USER_PIN=<your-pin>

# Run test
python scripts/test_message_retrieval.py
```

**Security Features:**
- Uses AICO's authentication endpoint (`/api/v1/users/authenticate`)
- Includes JWT Bearer token in all authenticated requests
- Handles encryption middleware transparently
- Validates authentication before proceeding with tests

## Architecture Alignment

✅ **Maintains existing patterns:**
- Uses AI registry for memory manager access
- Leverages existing working memory store
- Follows existing API response schemas
- No changes to core conversation engine

✅ **Security & Privacy:**
- User-scoped authentication required
- Only returns messages for authenticated user
- No new data collection
- Maintains existing encryption (LMDB)

✅ **Performance:**
- Leverages existing LMDB performance
- In-memory pagination (acceptable for 24h retention)
- No additional database queries

## Testing

**Manual Testing:**
1. Start backend: `cd backend && python -m backend.main`
2. Run test script: `python scripts/test_message_retrieval.py`
3. Verify messages are retrieved correctly

**Expected Behavior:**
- Messages sent via POST /conversation/messages are stored
- Messages can be retrieved via GET /conversation/messages
- Pagination works correctly
- Message format matches frontend expectations

## Next Steps

### Frontend Implementation (Phase 2)
1. Add Drift ORM dependencies to Flutter
2. Create local database schema (conversations, messages, sync_metadata)
3. Implement `ConversationLocalDataSource`
4. Enhance `MessageRepositoryImpl` with cache-first logic
5. Update `ConversationNotifier` to load from cache on startup
6. Add skeleton loading states to UI

### Integration Testing (Phase 3)
1. Test cache-first loading performance (<200ms target)
2. Test background sync behavior
3. Test offline mode functionality
4. Test cache-backend sync conflict resolution
5. Performance testing with large message histories

## Known Limitations

1. **Pagination is in-memory**: For 24h retention this is acceptable, but for longer retention periods, LMDB-level pagination would be more efficient.

2. **No message deduplication**: If the same message is stored multiple times, it will appear multiple times in results. Frontend should handle this.

3. **No ordering guarantee**: Messages are sorted by `_stored_at` timestamp, which may differ slightly from actual message timestamp.

4. **24-hour retention**: Messages older than 24 hours are automatically expired from working memory. For longer history, semantic memory would need to be queried.

## Future Enhancements

1. **Semantic memory fallback**: For messages older than 24 hours, query semantic memory (ChromaDB)
2. **LMDB-level pagination**: Implement cursor-based pagination in LMDB for better performance
3. **Message deduplication**: Add deduplication logic based on message_id
4. **Conversation metadata**: Add conversation title, last_message, unread_count
5. **Real-time updates**: WebSocket notifications when new messages arrive

## Files Modified

- `shared/aico/ai/memory/manager.py` - Added message_id to stored messages
- `backend/api/conversation/router.py` - Completed GET /conversation/messages endpoint
- `backend/api_gateway/middleware/encryption.py` - Added support for client_id in headers/query params for GET requests
- `scripts/test_message_retrieval.py` - Created comprehensive test script with full encryption support (new file)

## Important: Backend Restart Required

**The encryption middleware changes require a backend restart to take effect.**

After modifying `backend/api_gateway/middleware/encryption.py`, you must restart the backend service:

```bash
# Stop the backend
# Then start it again
cd backend && python -m backend.main
```

## Commit Message

```
feat(backend): implement conversation message retrieval API

- Add message_id field to stored messages for stable identification
- Complete GET /conversation/messages endpoint with pagination
- Support conversation filtering and timestamp filtering
- Return standardized message format for frontend consumption
- Add comprehensive test script for message retrieval

Part of offline-first conversation persistence implementation.
See: docs/concepts/data/offline-first-persistence.md
```
