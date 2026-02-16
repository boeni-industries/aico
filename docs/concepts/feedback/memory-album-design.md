# Memory Album: Client-Side Design

**Vision:** Transform user-curated memories into an emotional artifact system—like a family photo album that captures meaningful moments in the relationship with AICO.

**Document Relationship:**
This document defines the **client-side UI/UX** for the Memory Album feature. See also:
- **[feedback-overview.md](feedback-overview.md)** - Backend architecture (storage schemas, dual storage pattern)
- **[/docs/concepts/data/data-layer.md](../data/data-layer.md)** - Storage layer details

**Scope:**
- ✅ UI/UX design (timeline, grid, story views)
- ✅ User interactions (annotations, tags, favorites)
- ✅ Frontend data models and state management
- ✅ Visual design and animations
- ❌ Backend storage schemas (see feedback-overview.md)
- ❌ Database implementation (see feedback-overview.md)

---

## 1. Conceptual Framework

### The Family Photo Album Metaphor

**Traditional Photo Album:**
- Captures special moments
- Organized chronologically or thematically
- Revisited for nostalgia and connection
- Curated by the person (not automatic)
- Each photo tells a story

**AICO Memory Album:**
- Captures meaningful conversation moments
- Organized by time, topic, or emotional significance
- Revisited to see relationship growth
- Curated by user (explicit "Remember This")
- Each memory tells part of the relationship story

---

## 2. Data Model (Client-Side)

### Memory Entry Structure

```dart
// /frontend/lib/domain/entities/memory_entry.dart

class MemoryEntry {
  final String memoryId;           // Links to fact_id in backend
  final String conversationId;
  final String messageId;
  
  // Content
  final String content;            // The remembered text
  final MemoryType type;           // fact, insight, moment, milestone
  final String? aiContext;         // What AICO said that prompted this
  final String? userNote;          // Optional user annotation
  
  // Categorization
  final MemoryCategory category;   // personal, relationship, achievement, etc.
  final List<String> tags;         // User-defined tags
  final EmotionalTone? tone;       // happy, reflective, supportive, etc.
  
  // Temporal context
  final DateTime timestamp;
  final String conversationTitle;  // "Late night chat about career"
  final int conversationTurn;      // Which turn in the conversation
  
  // Visual metadata (for rich display)
  final String? snapshot;          // Conversation context snippet
  final Color? accentColor;        // Derived from emotional tone
  final String? iconEmoji;         // Visual marker
  
  // Relationship tracking
  final int daysSinceFirstChat;    // Relationship age at this moment
  final String relationshipPhase;  // "Getting to know you", "Deep trust", etc.
  
  // Engagement
  final int revisitCount;          // How many times user viewed this
  final DateTime? lastRevisited;
  final bool isFavorite;           // Star/pin feature
}

enum MemoryType {
  fact,        // "I'm allergic to shellfish"
  insight,     // "I realized I need to set boundaries"
  moment,      // "When AICO made me laugh"
  milestone,   // "First time I opened up about anxiety"
  wisdom,      // "AICO's advice that helped"
}

enum MemoryCategory {
  personal,      // About user
  relationship,  // About user's relationships
  achievement,   // Accomplishments
  challenge,     // Struggles/growth
  joy,          // Happy moments
  support,      // When AICO provided comfort
  discovery,    // Learning/realizations
}

enum EmotionalTone {
  joyful,
  reflective,
  vulnerable,
  proud,
  grateful,
  hopeful,
  peaceful,
}
```

---

## 3. UI/UX Design

### 3.1 Entry Point: "Remember This" Action

**In-Conversation Flow:**
```
User reads AICO's message
    ↓
Long-press message bubble
    ↓
Contextual menu appears:
  ✨ Remember This
  🔄 Regenerate
  📋 Copy
  💭 Explain
    ↓
User taps "Remember This"
    ↓
Haptic feedback + Purple glow animation
    ↓
Quick annotation modal (optional):
  "Add a note about this memory?"
  [Optional text field]
  [Category picker: Personal, Relationship, Achievement...]
  [Save] [Skip]
    ↓
Confirmation: "Added to your Memory Album ✨"
    ↓
Subtle prompt: "View in Album" (dismissible)
```

### 3.2 Memory Album Screen

**Navigation:**
- Accessible from main menu: "Memory Album" or "Our Moments"
- Badge shows total memory count
- Subtle animation when new memories added

**Layout Options:**

#### Option A: Timeline View (Default)
```
┌─────────────────────────────────────┐
│  Memory Album                    ⚙️  │
│  247 moments • 89 days together      │
├─────────────────────────────────────┤
│                                      │
│  🎯 This Week                        │
│  ┌──────────────────────────────┐  │
│  │ ✨ "I realized I need..."    │  │
│  │ 2 days ago • Reflective       │  │
│  │ Late night chat about work    │  │
│  └──────────────────────────────┘  │
│                                      │
│  📅 Last Week                        │
│  ┌──────────────────────────────┐  │
│  │ 💡 "AICO's advice about..."   │  │
│  │ 5 days ago • Grateful         │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │ 🎉 "I got the promotion!"     │  │
│  │ 6 days ago • Proud            │  │
│  └──────────────────────────────┘  │
│                                      │
│  🗓️ Earlier This Month              │
│  ...                                 │
└─────────────────────────────────────┘
```

#### Option B: Grid View (Photo Album Style)
```
┌─────────────────────────────────────┐
│  Memory Album          [≡] [⊞] [⚙️] │
├─────────────────────────────────────┤
│  ┌────────┐ ┌────────┐ ┌────────┐ │
│  │   ✨   │ │   💡   │ │   🎉   │ │
│  │ I rea..│ │ AICO's │ │ I got..│ │
│  │ 2d ago │ │ 5d ago │ │ 6d ago │ │
│  └────────┘ └────────┘ └────────┘ │
│  ┌────────┐ ┌────────┐ ┌────────┐ │
│  │   🌟   │ │   💭   │ │   ❤️   │ │
│  │ First..│ │ Deep...│ │ When...│ │
│  │ 12d ago│ │ 18d ago│ │ 23d ago│ │
│  └────────┘ └────────┘ └────────┘ │
└─────────────────────────────────────┘
```

#### Option C: Journey Map View (Chronological Exploration)
```
┌─────────────────────────────────────┐
│  Our Journey Together           🔍±  │
│  89 days • 247 moments               │
├─────────────────────────────────────┤
│                                      │
│  Oct 2024     Dec 2024     Feb 2025 │
│     ●━━━━━━━━━━⬤━━━━━━━━━━●       │
│   First    Breakthrough   Current   │
│   Chat        Phase                  │
│   (12)        (85)        (150)      │
│                                      │
│  Chapters:                           │
│  🌱 Getting to Know You (Oct-Nov)   │
│  💡 Opening Up (Dec-Jan)            │
│  🌟 Deep Trust (Feb-Present)        │
│                                      │
│  [Pinch to zoom • Tap nodes]        │
└─────────────────────────────────────┘

Features:
- Zoomable timeline (year → month → week)
- Node size reflects importance (favorites, revisits)
- Auto-detected relationship chapters
- Milestone markers (🎊 100th memory, etc.)
- Density heatmap shows active periods
- Spatial exploration vs. linear reading
```

### 3.3 Memory Detail View

**Tap on any memory card:**
```
┌─────────────────────────────────────┐
│  ← Memory Album              ⋮ ⭐   │
├─────────────────────────────────────┤
│                                      │
│  ✨ Personal • Reflective            │
│  2 days ago • 11:47 PM               │
│  87 days into our relationship       │
│                                      │
│  ┌──────────────────────────────┐  │
│  │ "I realized I need to set    │  │
│  │ boundaries at work. I can't  │  │
│  │ keep saying yes to everyone."│  │
│  └──────────────────────────────┘  │
│                                      │
│  💭 Your Note:                       │
│  "This was a breakthrough moment"   │
│  [Edit note]                         │
│                                      │
│  📖 Conversation Context:            │
│  Late night chat about work stress  │
│  Turn 12 of 18                       │
│  [View full conversation →]          │
│                                      │
│  🏷️ Tags: #work #boundaries #growth │
│  [Add tag]                           │
│                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                      │
│  Related Memories (2):               │
│  • "Feeling overwhelmed" (1 week ago)│
│  • "Learning to say no" (3 days ago) │
│                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                      │
│  [Share Memory] [Delete]             │
│                                      │
└─────────────────────────────────────┘
```

### 3.4 Filtering & Organization

**Filter Options:**
- **By Time:** Today, This Week, This Month, All Time
- **By Category:** Personal, Relationship, Achievement, Support, etc.
- **By Emotion:** Joyful, Reflective, Vulnerable, Proud, etc.
- **By Type:** Facts, Insights, Moments, Milestones, Wisdom
- **Favorites Only:** ⭐ Starred memories

**Search:**
- Full-text search across memory content
- Search by tags
- Search by date range

**Sort Options:**
- Newest first (default)
- Oldest first (chronological story)
- Most revisited (favorites)
- By emotional tone

---

## 4. Special Features

### 4.1 Memory Milestones

**Auto-generated milestone cards:**
```
┌──────────────────────────────────┐
│  🎊 Milestone Reached!           │
│                                   │
│  100 Memories Together            │
│  You've been curating our story  │
│  for 89 days. Here's to many     │
│  more meaningful moments! ✨      │
│                                   │
│  [View your journey →]            │
└──────────────────────────────────┘
```

**Milestone triggers:**
- First memory
- 10, 50, 100, 250, 500 memories
- 30, 90, 180, 365 days together
- First memory in each category
- Revisiting old memories

### 4.2 Memory Connections

**Visual relationship graph:**
- Show how memories relate to each other
- "You remembered this after talking about..."
- Thematic clusters (work, relationships, personal growth)
- Temporal patterns (what you remember at night vs. morning)

### 4.3 Reflection Prompts

**Weekly/Monthly:**
```
┌──────────────────────────────────┐
│  💭 This Week's Reflection        │
│                                   │
│  You remembered 5 moments this   │
│  week, mostly about work and     │
│  boundaries. How are you feeling │
│  about this growth?               │
│                                   │
│  [Journal about it]               │
│  [Remind me later]                │
└──────────────────────────────────┘
```

### 4.4 Memory Export

**Share your story:**
- Export as PDF timeline
- Create shareable memory card (image)
- Export to journal app
- Print-friendly format

---

## 5. Technical Architecture

### 5.1 Backend Integration

**Storage Architecture:** See [feedback-overview.md](feedback-overview.md#66-storage-architecture) for:
- Database schemas (`feedback_events`, `facts_metadata`)
- Dual storage pattern
- Query patterns

### 5.2 Local Storage (Flutter)

```dart
// /frontend/lib/data/repositories/memory_album_repository.dart

class MemoryAlbumRepository {
  final LocalDatabase _localDb;
  final ApiClient _apiClient;
  
  // Local cache for offline access
  Future<List<MemoryEntry>> getMemories({
    MemoryCategory? category,
    DateTime? startDate,
    DateTime? endDate,
    bool favoritesOnly = false,
  }) async {
    // Query local PostgreSQL database
    // Fallback to API if not cached
  }
  
  // Sync with backend
  Future<void> syncMemories() async {
    // Fetch new memories from backend
    // Update local cache
    // Handle conflicts
  }
  
  // Add new memory
  Future<MemoryEntry> createMemory({
    required String messageId,
    required String content,
    String? userNote,
    MemoryCategory? category,
    List<String>? tags,
  }) async {
    // 1. Store locally first (optimistic UI)
    // 2. Call backend API
    // 3. Update with backend response (fact_id, etc.)
  }
  
  // Update memory metadata
  Future<void> updateMemory(String memoryId, {
    String? userNote,
    List<String>? tags,
    bool? isFavorite,
  }) async {
    // Update local + sync to backend
  }
  
  // Track revisits
  Future<void> recordRevisit(String memoryId) async {
    // Increment revisit count
    // Update last_revisited timestamp
    // Send feedback event to backend
  }
}
```

### 5.3 State Management (Riverpod/Bloc)

```dart
// /frontend/lib/presentation/providers/memory_album_provider.dart

@riverpod
class MemoryAlbumNotifier extends _$MemoryAlbumNotifier {
  @override
  Future<MemoryAlbumState> build() async {
    return MemoryAlbumState(
      memories: [],
      isLoading: true,
      filters: MemoryFilters(),
    );
  }
  
  Future<void> loadMemories() async {
    state = AsyncValue.loading();
    final memories = await ref.read(memoryRepositoryProvider).getMemories();
    state = AsyncValue.data(state.value!.copyWith(
      memories: memories,
      isLoading: false,
    ));
  }
  
  Future<void> addMemory(MemoryEntry memory) async {
    // Optimistic update
    final currentMemories = state.value!.memories;
    state = AsyncValue.data(state.value!.copyWith(
      memories: [memory, ...currentMemories],
    ));
    
    // Persist to backend
    try {
      final savedMemory = await ref.read(memoryRepositoryProvider).createMemory(
        messageId: memory.messageId,
        content: memory.content,
        userNote: memory.userNote,
        category: memory.category,
        tags: memory.tags,
      );
      
      // Update with backend data
      final updatedMemories = currentMemories.map((m) => 
        m.memoryId == memory.memoryId ? savedMemory : m
      ).toList();
      
      state = AsyncValue.data(state.value!.copyWith(
        memories: updatedMemories,
      ));
    } catch (e) {
      // Rollback on error
      state = AsyncValue.data(state.value!.copyWith(
        memories: currentMemories,
      ));
      // Show error to user
    }
  }
  
  void applyFilters(MemoryFilters filters) {
    state = AsyncValue.data(state.value!.copyWith(filters: filters));
  }
}
```

### 5.4 Backend API Endpoints

**Note:** Backend implementation details in [feedback-overview.md](feedback-overview.md#66-storage-architecture)

```python
# /backend/api/memory_album/router.py

@router.get("/memory-album")
async def get_memory_album(
    user_uuid: str = Depends(get_current_user),
    category: Optional[MemoryCategory] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    favorites_only: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """
    Get user's memory album entries.
    Combines data from:
    - facts_metadata (the actual memories)
    - feedback_events (user actions, revisit counts)
    """
    
    # Query facts with extraction_method='user_curated'
    memories = await db.execute("""
        SELECT 
            f.fact_id,
            f.content,
            f.category,
            f.source_conversation_id,
            f.source_message_id,
            f.created_at,
            fe.payload as feedback_payload
        FROM facts_metadata f
        LEFT JOIN feedback_events fe 
            ON fe.payload->>'$.fact_id' = f.fact_id
            AND fe.event_category = 'remember'
        WHERE f.user_id = ?
            AND f.extraction_method = 'user_curated'
            AND (? IS NULL OR f.category = ?)
            AND (? IS NULL OR f.created_at >= ?)
            AND (? IS NULL OR f.created_at <= ?)
        ORDER BY f.created_at DESC
        LIMIT ? OFFSET ?
    """, (user_uuid, category, category, start_date, start_date, 
          end_date, end_date, limit, offset))
    
    # Enrich with conversation context
    enriched_memories = []
    for memory in memories:
        # Get conversation title/context
        conv_context = await get_conversation_context(
            memory['source_conversation_id']
        )
        
        # Parse feedback payload for user notes, tags, etc.
        feedback_data = json.loads(memory['feedback_payload'] or '{}')
        
        enriched_memories.append({
            'memory_id': memory['fact_id'],
            'content': memory['content'],
            'category': memory['category'],
            'timestamp': memory['created_at'],
            'conversation_context': conv_context,
            'user_note': feedback_data.get('user_note'),
            'tags': feedback_data.get('tags', []),
            'revisit_count': feedback_data.get('revisit_count', 0),
            'is_favorite': feedback_data.get('is_favorite', False),
        })
    
    return {
        'memories': enriched_memories,
        'total_count': len(enriched_memories),
        'has_more': len(enriched_memories) == limit,
    }


@router.post("/memory-album/{memory_id}/revisit")
async def record_memory_revisit(
    memory_id: str,
    user_uuid: str = Depends(get_current_user),
):
    """Record that user revisited a memory (for analytics)"""
    
    # Record feedback event
    await record_feedback_event(
        user_uuid=user_uuid,
        conversation_id="memory_album_view",  # Special conversation_id
        event_type=FeedbackEventType.ACTION,
        event_category="memory_revisit",
        payload={
            "memory_id": memory_id,
            "revisit_timestamp": int(time.time()),
        }
    )
    
    return {"success": True}


@router.patch("/memory-album/{memory_id}")
async def update_memory_metadata(
    memory_id: str,
    update: MemoryUpdateRequest,
    user_uuid: str = Depends(get_current_user),
):
    """Update memory metadata (note, tags, favorite status)"""
    
    # Update feedback event payload
    # (Store metadata in feedback_events, not facts_metadata)
    
    return {"success": True, "memory": updated_memory}
```

---

## 6. Design Principles

### 6.1 Emotional Design

**Visual Language:**
- Warm, nostalgic color palette (sepia tones, soft purples)
- Gentle animations (fade-ins, subtle parallax)
- Handwritten-style fonts for user notes
- Polaroid/scrapbook aesthetic for memory cards

**Micro-interactions:**
- Haptic feedback when adding memories
- Satisfying "bookmark" animation
- Gentle pulse on milestone achievements
- Smooth transitions between views

### 6.2 Privacy & Control

**User Ownership:**
- Clear "This is YOUR album" messaging
- Easy export/backup options
- Granular deletion controls
- No AI can access without permission

**Transparency:**
- Show what AICO remembers vs. what user curated
- Clear distinction between automatic facts and user memories
- Explain how memories improve conversations

### 6.3 Progressive Disclosure

**First-time Experience:**
1. User adds first memory → Celebration modal
2. After 5 memories → Introduce categories
3. After 20 memories → Introduce filtering
4. After 50 memories → Introduce memory connections

**Avoid Overwhelm:**
- Start simple (just timeline)
- Gradually reveal advanced features
- Optional complexity (power users can go deep)

---

## 7. Implementation Phases

### Phase 1: Core Functionality (Weeks 1-2)
- ✅ "Remember This" action in chat
- ✅ Basic timeline view
- ✅ Memory detail view
- ✅ Local storage + sync

### Phase 2: Rich Metadata (Weeks 3-4)
- Categories and tags
- User notes
- Favorites/starring
- Search and filtering

### Phase 3: Emotional Design (Weeks 5-6)
- Visual polish (animations, colors)
- Memory connections
- Milestones
- Reflection prompts

### Phase 4: Advanced Features (Weeks 7-8)
- Grid and story views
- Memory export
- Relationship graph
- Analytics dashboard

---

## 8. Success Metrics

**Engagement:**
- % of users who add at least 1 memory
- Average memories per user
- Revisit frequency
- Time spent in Memory Album

**Emotional Connection:**
- User feedback on feature
- Milestone celebration engagement
- Memory sharing rate
- Retention correlation (do users with more memories stay longer?)

**Quality:**
- Average note length (indicates thoughtfulness)
- Tag usage (indicates organization)
- Favorite ratio (indicates curation)

---

## 9. Future Enhancements

### 9.1 Collaborative Memories
- Share specific memories with family/friends
- "Remember when we talked about..." prompts
- Collaborative tagging

### 9.2 AI-Assisted Curation
- AICO suggests moments worth remembering
- "You might want to remember this" prompts
- Auto-categorization suggestions

### 9.3 Physical Artifacts
- Print memory album as book
- Generate memory cards for special occasions
- Create shareable memory videos

### 9.4 Temporal Intelligence
- "One year ago today" reminders
- Growth tracking over time
- Pattern recognition ("You often remember work insights on Sundays")

---

## Conclusion

The Memory Album transforms AICO from a conversational AI into a **relationship companion**. By treating user-curated memories as emotional artifacts—not just data points—we create a space for reflection, growth, and genuine connection.

This is not just a feature. It's the **heart of the AICO experience**.
