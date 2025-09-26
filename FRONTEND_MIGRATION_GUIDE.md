# Frontend Migration Guide: Thread ID → Conversation ID

## Overview
The backend has been updated to use **user-scoped conversations** with semantic memory instead of explicit thread management. This requires corresponding frontend changes.

## Key Changes Required

### 1. **API Response Field Names**
```dart
// OLD - UnifiedMessageResponse fields
response['thread_id']
response['thread_action'] 
response['thread_reasoning']

// NEW - Updated field names
response['conversation_id']
response['conversation_action']
response['conversation_reasoning']
```

### 2. **Endpoint Changes**
```dart
// OLD - Thread-specific endpoints
GET /api/v1/conversation/threads/{thread_id}/messages
GET /api/v1/conversation/status/{thread_id}
WS  /ws/{thread_id}

// NEW - User-scoped endpoints
GET /api/v1/conversation/messages?page=1&page_size=50&since=2024-01-01
GET /api/v1/conversation/status
WS  /ws
```

### 3. **Model Updates**

#### Message Model
```dart
// Update Message class
class Message {
  final String id;
  final String content;
  final String userId;
  final String conversationId; // Was: threadId
  // ... rest unchanged
}
```

#### ConversationProvider State
```dart
// Update ConversationProvider
class ConversationState {
  final String? currentConversationId; // Was: currentThreadId
  // ... rest unchanged
}
```

### 4. **Repository Changes**

#### MessageRepositoryImpl
```dart
// OLD
conversationId: response['thread_id'] as String,

// NEW  
conversationId: response['conversation_id'] as String,
```

#### API Client Updates
```dart
// Remove thread-specific methods
// getThreadMessages(String threadId) 
// getThreadStatus(String threadId)

// Add user-scoped methods
Future<List<Message>> getMyMessages({int page = 1, int pageSize = 50, DateTime? since});
Future<ConversationStatus> getMyStatus();
```

### 5. **WebSocket Changes**
```dart
// OLD - Thread-specific WebSocket
WebSocketChannel.connect(Uri.parse('ws://localhost:8000/api/v1/conversation/ws/$threadId'));

// NEW - User-scoped WebSocket  
WebSocketChannel.connect(Uri.parse('ws://localhost:8000/api/v1/conversation/ws'));
```

### 6. **Logging Updates**
```dart
// Update all logging references
AICOLog.info('Message sent', extra: {
  'conversation_id': conversationId, // Was: thread_id
});
```

## Benefits of Migration

1. **Simplified Architecture**: No complex thread management
2. **User-Centric**: All data naturally scoped to authenticated user
3. **Semantic Memory Integration**: Context handled automatically
4. **Better UX**: Conversations flow naturally without explicit thread boundaries
5. **Scalable**: User-scoped data access patterns

## Migration Strategy

### Phase 1: Update Models & DTOs
- Update `Message` class to use `conversationId`
- Update response parsing in repositories
- Update state management classes

### Phase 2: Update API Calls
- Replace thread-specific endpoints with user-scoped ones
- Update WebSocket connection logic
- Update error handling for new response format

### Phase 3: Update UI Logic
- Remove thread selection/management UI
- Update conversation flow to be user-scoped
- Test end-to-end conversation flow

### Phase 4: Testing & Validation
- Test message sending/receiving
- Test conversation continuity
- Test WebSocket real-time updates
- Test offline/online sync

## Files to Update

### Core Files
- `lib/data/models/message.dart`
- `lib/data/repositories/message_repository_impl.dart`
- `lib/presentation/providers/conversation_provider.dart`
- `lib/networking/api_client.dart`

### Supporting Files
- All files with `thread_id` references
- WebSocket connection logic
- Logging statements
- Error handling code

## Testing Checklist

- [ ] Message sending works with new API
- [ ] AI responses received correctly
- [ ] Conversation continuity maintained
- [ ] WebSocket updates work
- [ ] Error handling updated
- [ ] Offline sync compatibility
- [ ] Authentication integration
- [ ] Performance unchanged

## Notes

- **Semantic Memory**: Context continuity is now handled by the backend's semantic memory system
- **User Authentication**: All conversations are automatically scoped to the authenticated user
- **No Thread Management**: Frontend no longer needs to manage thread creation/selection
- **Backward Compatibility**: This is a breaking change - coordinate deployment with backend updates
