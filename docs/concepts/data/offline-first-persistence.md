---
title: Offline-First Conversation Persistence
---

# Offline-First Conversation Persistence

AICO's conversation persistence strategy ensures instant message loading and seamless offline functionality through local-first storage with intelligent background synchronization.

## Problem Statement

Currently, the frontend starts with a blank slate on each launch, requiring users to wait for backend message retrieval. This creates a poor UX compared to modern messaging apps (WhatsApp, Telegram) which display cached conversations instantly.

## Architecture Principles

### 1. Cache-First Loading
- **Instant Display**: Messages load from local cache in <200ms
- **Background Sync**: Fresh data fetched asynchronously without blocking UI
- **Optimistic Updates**: Sent messages appear immediately, sync in background

### 2. Offline-First Design
- **Full Read Access**: View all cached conversations without network
- **Graceful Degradation**: Clear offline indicators, no error states
- **Automatic Recovery**: Seamless sync when connection restored

### 3. Smart Synchronization
- **Lazy Sync**: Only sync active conversations
- **Conflict Resolution**: Backend as source of truth (last-write-wins)
- **Efficient Updates**: Delta sync for changed messages only

## Implementation Overview

### Frontend (Flutter)

**Local Storage**: Drift ORM with SQLite
- `conversations` table: Conversation metadata
- `messages` table: Full message history
- `sync_metadata` table: Sync state tracking
- **Retention**: 90 days (configurable)

**Repository Pattern**: Enhanced `MessageRepositoryImpl`
```dart
getMessages(conversationId) {
  1. Load from cache → instant display
  2. Return cached data immediately
  3. Sync with backend in background
  4. Update cache with fresh data
}
```

**Startup Flow**:
1. `ConversationProvider.build()` → Load last active conversation from cache
2. Display messages instantly (<200ms)
3. Background sync updates cache
4. UI reflects changes smoothly

### Backend (Python)

**Message Retrieval**: Enhanced `GET /conversation/messages`
- Query working memory (LMDB) for recent messages (24h retention)
- Fallback to semantic memory for older messages
- Pagination support: `page`, `page_size`, `before_message_id`
- Returns: `messages[]`, `total_count`, `has_more`

**Storage Architecture**:
- **Working Memory (LMDB)**: Fast access to recent conversations (24h TTL)
- **Semantic Memory (ChromaDB)**: Long-term storage with vector search
- **Automatic Cleanup**: Messages older than retention period

## Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| Time to first message | <200ms | Industry standard: <500ms |
| Cache hit rate | >95% | Most sessions load cached data |
| Sync latency | <2s | Non-blocking background operation |
| Storage per conversation | ~50KB | Efficient for 90-day retention |

## UX Enhancements

### Loading States
- **Skeleton Screen**: Show message placeholders during initial load (not blank screen)
- **Sync Indicator**: Subtle icon when syncing in background
- **Offline Banner**: Clear "Viewing cached messages" when offline

### Smooth Transitions
- **Scroll Position**: Restore last scroll position on app restart
- **Draft Persistence**: Save unsent messages across sessions
- **Unread Counts**: Maintain locally, sync with backend

## Migration Strategy

**Existing Users**:
1. First launch: One-time sync from backend → "Loading conversation history..."
2. Subsequent launches: Instant display from cache
3. No data loss: All messages preserved in backend (24h working memory + long-term semantic memory)

**Rollout Phases**:
1. Backend API completion (Week 1)
2. Frontend local storage + basic sync (Week 2)
3. UX polish + performance optimization (Week 3)
4. Beta testing + monitoring (Week 4)
5. Production release (Week 5)

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **Drift ORM** | Type-safe, performant, excellent Flutter integration |
| **90-day retention** | Balances storage vs. utility (industry standard) |
| **Cache-first strategy** | Instant UX, matches WhatsApp/Telegram patterns |
| **Background sync** | Non-blocking, preserves responsiveness |
| **Optimistic UI** | Feels instant, handles failures gracefully |

## Risk Mitigation

- **Database migration failures** → Comprehensive testing + rollback plan
- **Sync conflicts** → Last-write-wins with backend as source of truth
- **Storage bloat** → Automatic cleanup of messages >90 days
- **Performance degradation** → Pagination + lazy loading for large conversations
- **Network failures** → Retry logic with exponential backoff

## Related Concepts

- [Data Layer](./data-layer.md) - Overall data architecture
- [Memory Architecture](../memory/architecture.md) - Working and semantic memory systems
- [Context Management](../memory/context-management.md) - Conversation context assembly

## Architectural Impact Analysis

### Frontend Impact

**New Components**:
- Local database layer (Drift ORM + SQLite)
- Local data source (`ConversationLocalDataSource`)
- Enhanced repository with cache-first logic
- Database migration system

**Modified Components**:
- `MessageRepositoryImpl`: Add cache-first loading + background sync
- `ConversationNotifier`: Add startup conversation loading
- `HomeScreen`: Add skeleton loading states

**Architecture Alignment**: ✅ **Fully Aligned**
- Maintains thin client design - local DB is just a cache layer
- No heavy processing added to frontend
- Follows existing repository pattern
- Preserves message-driven architecture (backend still source of truth)

**Impact Level**: **Medium** - Adds persistence layer but doesn't change core architecture

### Backend Impact

**New Components**:
- Message retrieval logic in working memory store
- Pagination support in API endpoint

**Modified Components**:
- `GET /conversation/messages`: Complete TODO implementation
- `WorkingMemoryStore`: Add `get_messages()` method with pagination
- Conversation router: Return actual message data instead of empty list

**Architecture Alignment**: ✅ **Fully Aligned**
- Leverages existing working memory (LMDB) + semantic memory (ChromaDB)
- Follows existing API Gateway pattern
- Maintains message bus architecture
- No changes to core conversation engine

**Impact Level**: **Low** - Completes existing API, minimal new code

### Security & Privacy Alignment

**Principle Compliance**:

| Principle | Implementation | Status |
|-----------|----------------|--------|
| **Local-First Processing** | All data cached locally, backend optional after initial sync | ✅ Aligned |
| **Privacy by Design** | No new data collection, just local caching of existing messages | ✅ Aligned |
| **Zero-Effort Security** | Automatic encryption via Drift + SQLite, transparent to user | ✅ Aligned |
| **Data Encryption** | SQLite database encrypted using platform secure storage | ✅ Aligned |
| **User Control** | User owns all cached data, can clear cache anytime | ✅ Aligned |

**Security Considerations**:
- Frontend local DB must use encrypted storage (Flutter secure storage + Drift encryption)
- Cache retention policy (90 days) respects privacy by not hoarding old data
- Sync only when user authenticated - no anonymous data leakage
- Backend already encrypts working memory (LMDB) - no changes needed

**Security Impact**: **None** - Maintains existing security posture, adds frontend encryption

### Developer Guidelines Alignment

**Principle Compliance**:

| Guideline | Implementation | Status |
|-----------|----------------|--------|
| **Simplicity First** | Cache-first pattern is straightforward, well-understood | ✅ Aligned |
| **DRY** | Repository pattern reused, single source of truth (backend) | ✅ Aligned |
| **KISS** | No overengineering - standard SQLite + background sync | ✅ Aligned |
| **Modularity** | Clean separation: local datasource, repository, provider | ✅ Aligned |
| **Resource Awareness** | 90-day retention + auto-cleanup prevents storage bloat | ✅ Aligned |
| **Privacy & Security** | Local-first, encrypted, user-controlled | ✅ Aligned |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Database migration failures | Medium | High | Comprehensive testing, rollback plan, beta testing |
| Cache-backend sync conflicts | Low | Medium | Last-write-wins, backend authoritative |
| Performance degradation | Low | Medium | Pagination, lazy loading, performance testing |
| Storage bloat | Low | Low | 90-day auto-cleanup, configurable retention |
| Security vulnerabilities | Low | High | Encrypted storage, security audit, penetration testing |

## References

- Industry patterns: WhatsApp, Telegram, Signal (offline-first messaging)
- Flutter best practices: Drift ORM, Riverpod state management
- Backend storage: LMDB (working memory), ChromaDB (semantic memory)
- AICO Architecture: [Architecture Overview](../../architecture/architecture-overview.md)
- AICO Security: [Security Overview](../../security/security-overview.md)
- Developer Guidelines: [Guidelines](../../guides/developer/guidelines.md)
