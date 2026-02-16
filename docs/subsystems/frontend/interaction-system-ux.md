# Interaction System UX Specification

**Status**: Ready for Implementation  
**Last Updated**: 2026-02-08  
**Integrates With**: design-principles.md, state-management.md, networking.md

---

## Overview

The interaction system provides a unified UX for all user-AICO interactions: questions, choices, approvals, and dialogues. It integrates seamlessly into the existing conversation flow while maintaining awareness through the right drawer.

---

## Core UX Principles

### 1. **Ambient, Not Blocking**
- Interactions are **requests**, not interruptions
- Conversation continues normally
- User maintains full control of attention

### 2. **Dual Access Pattern**
```
Conversation (Primary)  → Immediate action in context
Drawer (Secondary)      → Awareness, triage, history
```

### 3. **Progressive Disclosure**
```
Badge → Drawer List → Conversation Context → Full Detail
```

### 4. **Contextual Urgency**
- **Required + High**: Prominent in conversation + gentle reminders
- **Required + Medium**: Visible in conversation + drawer badge
- **Optional**: Drawer only, no interruption

---

## Integration Points

### **Right Drawer - Interactions Tab**

**Replaces**: Old `ProactiveTimeline` (notifications tab)  
**Purpose**: Inbox, triage, history

#### Tab Structure
```dart
DrawerTab.interactions  // Renamed from: notifications
```

#### Filter Tabs
```
[Pending: 3] [Deferred: 1] [All: 15] [Answered: 8] [Dismissed: 4]
```

#### Card Layout
```
┌─────────────────────────────────┐
│ 🔴 Required • High • 2m ago     │
│ ⚠️  Production Deployment       │
│ "Approve v2.5.0 to production?" │
│                                 │
│ [View in Chat] [Approve] [Reject]│
└─────────────────────────────────┘
```

#### Sorting Priority
1. Required + High severity (red badge)
2. Required + Medium/Low
3. Optional + Recent
4. Deferred (separate tab)
5. Historical (collapsed)

---

### **Conversation Integration**

#### Inline Interaction Bubbles

**Question Type**:
```dart
InteractionQuestionBubble(
  interaction: request,
  onAnswer: (text) => submit(),
)
```
```
┌─────────────────────────────────┐
│ AICO: "I need some information" │
│                                 │
│ ┌─────────────────────────────┐│
│ │ ❓ Question                 ││
│ │ "What's your preferred      ││
│ │  database for the project?" ││
│ │                             ││
│ │ [Text Input Field]          ││
│ │ [Submit Answer]             ││
│ └─────────────────────────────┘│
└─────────────────────────────────┘
```

**Choice Type**:
```dart
InteractionChoiceBubble(
  interaction: request,
  options: request.allowedOptions,
  onSelect: (option) => submit(),
)
```
```
┌─────────────────────────────────┐
│ ┌─────────────────────────────┐│
│ │ 🎯 Choice                   ││
│ │ "Which testing framework?"  ││
│ │                             ││
│ │ ○ pytest                    ││
│ │ ○ unittest                  ││
│ │ ○ nose2                     ││
│ │ ○ Robot Framework           ││
│ └─────────────────────────────┘│
└─────────────────────────────────┘
```

**Approval Type**:
```dart
InteractionApprovalBubble(
  interaction: request,
  onApprove: () => approve(),
  onReject: () => reject(),
)
```
```
┌─────────────────────────────────┐
│ ┌─────────────────────────────┐│
│ │ ⚠️  Approval Required       ││
│ │ "Deploy v2.5.0 to           ││
│ │  production environment?"   ││
│ │                             ││
│ │ [✓ Approve] [✗ Reject]     ││
│ └─────────────────────────────┘│
└─────────────────────────────────┘
```

**Dialogue Type**:
```dart
InteractionDialogueBubble(
  interaction: request,
  onStart: () => openConversation(),
)
```
```
┌─────────────────────────────────┐
│ ┌─────────────────────────────┐│
│ │ 💬 Let's Discuss            ││
│ │ "I'd like to talk about the ││
│ │  new feature architecture"  ││
│ │                             ││
│ │ [Start Conversation]        ││
│ └─────────────────────────────┘│
└─────────────────────────────────┘
```

---

## Edge Cases & Perfect UX

### **Case 1: User Ignores and Continues Chatting**

**Behavior**:
- Conversation continues normally
- Interaction stays in drawer with badge
- No blocking or interruption

**Visual Cues**:
- Bell icon badge count
- Drawer tab red dot (if required)
- Subtle avatar pulse (if required + high)

**Re-surfacing**:
- **Required + High**: Gentle reminder after 15-30 min
- **Required + Medium**: Reminder after 1-2 hours
- **Optional**: No automatic reminder

**Example Reminder**:
```
AICO: "By the way, you still have a pending approval 
      for the production deployment. Want to review it?"
```

---

### **Case 2: User Says "Later"**

**User Action**: Taps "Later" button or says "remind me later"

**System Response**:
1. Status → `deferred`
2. Moved to "Deferred" filter tab
3. Removed from "Pending" count
4. Smart reminder scheduled based on urgency

**Drawer Display**:
```
┌─────────────────────────────────┐
│ DEFERRED (1)                    │
├─────────────────────────────────┤
│ ⏰ Deferred 10m ago             │
│ "Deploy approval"               │
│ Expires in: 2h 15m              │
│ [Answer Now]                    │
└─────────────────────────────────┘
```

**Reminder Schedule**:
- **High severity**: 30 minutes
- **Medium severity**: 2 hours
- **Low severity**: 4 hours
- **With expiration**: 15 min before expiry

---

### **Case 3: Interaction Expires**

**Behavior**:
1. Status → `expired`
2. Visual indicator in drawer (grayed out)
3. AICO mentions in conversation

**Conversation Message**:
```
AICO: "The deployment approval has expired. 
      Would you like me to create a new request?"
```

**Drawer Display**:
```
┌─────────────────────────────────┐
│ ⏱️  EXPIRED                     │
│ "Deploy approval"               │
│ Expired 5m ago                  │
│ [Create New Request]            │
└─────────────────────────────────┘
```

---

### **Case 4: Multiple Pending Interactions**

**Drawer Grouping**:
```
┌─────────────────────────────────┐
│ PENDING (5)                     │
├─────────────────────────────────┤
│ 🔴 Required (3)                 │
│   ⚠️  Deploy approval (High)    │
│   ❓ Database choice (Medium)   │
│   ❓ Code review (Medium)       │
├─────────────────────────────────┤
│ ⚪ Optional (2)                 │
│   💬 Architecture discussion    │
│   ❓ Preferred editor           │
└─────────────────────────────────┘
```

**Batch Actions**:
- "Answer All Required" button
- Swipe to defer multiple
- Bulk dismiss for optional

---

### **Case 5: User Scrolls Past Unanswered Interaction**

**Behavior**:
- Interaction bubble stays in conversation history
- Visual indicator shows "unanswered"
- Can scroll back and answer anytime

**Visual State**:
```
┌─────────────────────────────────┐
│ ┌─────────────────────────────┐│
│ │ ❓ UNANSWERED                ││
│ │ "What's your preferred..."  ││
│ │ [Answer Now]                ││
│ └─────────────────────────────┘│
│                                 │
│ [User continued conversation]   │
└─────────────────────────────────┘
```

**Drawer Link**:
- Tapping in drawer scrolls to bubble
- Highlights with pulse animation
- Auto-focuses input if applicable

---

### **Case 6: Offline Mode**

**Behavior**:
- Interactions cached locally
- Answers queued for sync
- Visual indicator shows "pending sync"

**UI State**:
```
┌─────────────────────────────────┐
│ ✓ Answered (Syncing...)         │
│ "Python" • 2m ago               │
│ 📡 Will sync when online        │
└─────────────────────────────────┘
```

---

### **Case 7: Rapid-Fire Interactions**

**Behavior**:
- Group by conversation context
- Show count badge on grouped items
- Expand to show all

**Drawer Display**:
```
┌─────────────────────────────────┐
│ 📦 Feature Planning (3)         │
│ "Database, framework, testing"  │
│ [Expand to Answer All]          │
└─────────────────────────────────┘
```

---

### **Case 8: Interaction During Voice Call**

**Behavior**:
- AICO asks verbally
- Visual card appears
- User can answer verbally or tap

**Voice Flow**:
```
AICO (voice): "I need your approval to deploy 
               version 2.5.0 to production. 
               Should I proceed?"

[Visual card appears with Approve/Reject buttons]

User: "Yes, approve it" OR [taps Approve]
```

---

## Visual Design Specifications

### **Glassmorphic Interaction Cards**

Following design-principles.md:

```dart
Container(
  decoration: BoxDecoration(
    color: isDark 
      ? Colors.white.withOpacity(0.06)
      : Colors.white.withOpacity(0.6),
    borderRadius: BorderRadius.circular(28), // Large radius
    border: Border.all(
      color: accentColor.withOpacity(0.3),
      width: 1.5,
    ),
    boxShadow: [
      BoxShadow(
        color: Colors.black.withOpacity(isDark ? 0.3 : 0.08),
        blurRadius: 20,
        offset: Offset(0, 6),
        spreadRadius: -4,
      ),
    ],
  ),
)
```

### **Urgency Color Coding**

```dart
// Severity colors
final severityColors = {
  'high': Color(0xFFED7867),    // Coral (warning)
  'medium': Color(0xFFB8A1EA),  // Purple (accent)
  'low': Color(0xFF8DD6B8),     // Mint (calm)
};

// Requirement indicators
final requirementIcons = {
  'required': Icons.priority_high,
  'optional': Icons.info_outline,
};
```

### **Status Badges**

```dart
Container(
  padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
  decoration: BoxDecoration(
    color: statusColor.withOpacity(0.15),
    borderRadius: BorderRadius.circular(12),
  ),
  child: Text(
    status.toUpperCase(),
    style: TextStyle(
      fontSize: 10,
      fontWeight: FontWeight.w600,
      color: statusColor,
    ),
  ),
)
```

---

## State Management

### **InteractionProvider** (Riverpod)

```dart
@riverpod
class InteractionNotifier extends _$InteractionNotifier {
  @override
  AsyncValue<List<InteractionRequest>> build() {
    _initWebSocket();
    _loadPending();
    return const AsyncValue.loading();
  }

  // WebSocket real-time updates
  void _initWebSocket() {
    ref.read(webSocketServiceProvider).broadcasts.listen((broadcast) {
      _handleBroadcast(broadcast);
    });
  }

  // Handle new/updated interactions
  void _handleBroadcast(InteractionBroadcastData data) {
    state.whenData((interactions) {
      final updated = _upsertInteraction(interactions, data.interaction);
      state = AsyncValue.data(updated);
      
      // Show notification if new and required
      if (data.event.eventType == 'created' && 
          data.interaction.requirement == 'required') {
        _showNotification(data.interaction);
      }
    });
  }

  // User actions
  Future<void> answerQuestion(String id, String answer) async {
    await ref.read(interactionRepositoryProvider)
        .answerInteraction(id, answerText: answer);
  }

  Future<void> approveInteraction(String id) async {
    await ref.read(interactionRepositoryProvider)
        .approveInteraction(id);
  }

  Future<void> deferInteraction(String id) async {
    // Update local state immediately (optimistic)
    state.whenData((interactions) {
      final updated = interactions.map((i) {
        if (i.interactionId == id) {
          return i.copyWith(status: InteractionStatus.deferred);
        }
        return i;
      }).toList();
      state = AsyncValue.data(updated);
    });
    
    // Schedule reminder based on urgency
    _scheduleReminder(id);
  }
}
```

---

## WebSocket Integration

### **Connection Lifecycle**

```dart
class InteractionWebSocketService {
  Future<void> connect() async {
    final token = await _authRepository.getToken();
    final userUuid = await _authRepository.getUserUuid();
    
    await _channel.connect(
      wsUrl: 'ws://localhost:8772/ws',
      token: token,
      userUuid: userUuid,
    );
    
    // Subscribe to user's interaction topic
    _channel.subscribe('interaction.notifications.$userUuid');
    
    // Handle broadcasts
    _channel.broadcasts.listen(_handleBroadcast);
  }
  
  void _handleBroadcast(InteractionBroadcastData data) {
    // Update state
    _notifier.handleBroadcast(data);
    
    // Show notification
    if (data.event.eventType == 'created') {
      _showLocalNotification(data.interaction);
    }
    
    // Haptic feedback for required
    if (data.interaction.requirement == 'required') {
      HapticFeedback.mediumImpact();
    }
  }
}
```

---

## Notification Strategy

### **Local Notifications**

```dart
// New interaction arrives
void _showLocalNotification(InteractionRequest interaction) {
  final urgency = interaction.requirement == 'required' 
      ? NotificationPriority.high 
      : NotificationPriority.low;
  
  LocalNotifications.show(
    title: _getNotificationTitle(interaction.interactionType),
    body: interaction.prompt,
    priority: urgency,
    actions: _getQuickActions(interaction),
  );
}

List<NotificationAction> _getQuickActions(InteractionRequest interaction) {
  switch (interaction.interactionType) {
    case InteractionType.approval:
      return [
        NotificationAction(id: 'approve', title: 'Approve'),
        NotificationAction(id: 'reject', title: 'Reject'),
      ];
    case InteractionType.question:
      return [
        NotificationAction(id: 'answer', title: 'Answer'),
        NotificationAction(id: 'later', title: 'Later'),
      ];
    default:
      return [
        NotificationAction(id: 'view', title: 'View'),
      ];
  }
}
```

---

## Accessibility

### **Screen Reader Support**

```dart
Semantics(
  label: 'Interaction: ${interaction.interactionType}',
  hint: interaction.requirement == 'required' 
      ? 'Required action' 
      : 'Optional',
  child: InteractionCard(...),
)
```

### **Keyboard Navigation**

- Tab through pending interactions
- Enter to expand/answer
- Escape to defer
- Arrow keys for choice selection

### **High Contrast Mode**

```dart
final isHighContrast = MediaQuery.of(context).highContrast;

if (isHighContrast) {
  // Use solid colors, no transparency
  // Increase border width to 2px
  // Use 100% opacity for all elements
}
```

---

## Performance Considerations

### **Lazy Loading**

- Load only pending on app start
- Fetch history on drawer open
- Paginate historical interactions

### **Caching**

```dart
// Cache pending interactions
final cachedPending = await _cache.get('pending_interactions');

// Sync with backend
final freshPending = await _repository.listInteractions(
  status: InteractionStatus.pending,
);

// Merge and update
_mergeCachedAndFresh(cachedPending, freshPending);
```

### **Optimistic Updates**

```dart
// Update UI immediately
state = AsyncValue.data(updatedList);

// Sync with backend
try {
  await _repository.answerInteraction(id, answer);
} catch (e) {
  // Rollback on error
  state = AsyncValue.data(previousList);
  _showError('Failed to submit answer');
}
```

---

## Testing Strategy

### **Unit Tests**

```dart
test('deferred interaction moves to deferred tab', () {
  final notifier = InteractionNotifier();
  notifier.deferInteraction('test-id');
  
  expect(
    notifier.state.value!.where((i) => i.status == 'deferred'),
    hasLength(1),
  );
});
```

### **Widget Tests**

```dart
testWidgets('approval card shows approve/reject buttons', (tester) async {
  await tester.pumpWidget(
    InteractionApprovalBubble(interaction: mockApproval),
  );
  
  expect(find.text('Approve'), findsOneWidget);
  expect(find.text('Reject'), findsOneWidget);
});
```

### **Integration Tests**

```dart
testWidgets('end-to-end interaction flow', (tester) async {
  // 1. WebSocket receives new interaction
  // 2. Notification appears
  // 3. User taps to view
  // 4. User answers
  // 5. Status updates to answered
});
```

---

## Migration from Old System

### **Phase 1: Data Layer**
- Create new models
- Implement WebSocket service
- Set up state management

### **Phase 2: UI Components**
- Build interaction cards
- Create drawer timeline
- Implement conversation bubbles

### **Phase 3: Integration**
- Replace ProactiveTimeline
- Update drawer tab
- Connect WebSocket

### **Phase 4: Cleanup**
- Remove old proactive system
- Delete obsolete models
- Update documentation

---

## Success Metrics

- ✅ User can see pending interactions in drawer
- ✅ User can answer in conversation context
- ✅ Real-time notifications via WebSocket
- ✅ Deferred interactions resurface appropriately
- ✅ No blocking or interruption of conversation
- ✅ Expired interactions handled gracefully
- ✅ Offline mode works with sync queue
- ✅ Accessibility standards met (WCAG AA+)

---

**Ready for implementation. All edge cases covered. Design principles integrated.**
