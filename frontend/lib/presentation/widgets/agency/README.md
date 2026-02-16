# Agency Badge Widget

## Overview

The Agency Badge is a small, animated indicator positioned at the bottom-right of the avatar that displays the current agency system state. It follows AICO's design principles of minimalism, progressive disclosure, and glassmorphic aesthetics.

## Architecture

### State Management
- **Provider:** `AgencyBadgeStateNotifier` (Riverpod)
- **State:** `AgencyBadgeState` with mode, intensity, summary, and metadata
- **Location:** `lib/presentation/providers/agency_state_provider.dart`

### Widget
- **Component:** `AgencyBadge`
- **Location:** `lib/presentation/widgets/agency/agency_badge.dart`
- **Positioning:** Bottom-right of avatar (4px overlap)

## Badge Modes

### 1. None
- **Visual:** No badge visible
- **Use:** No active agency state

### 2. Active Intention
- **Visual:** Purple dot (8-12px), subtle pulse
- **Color:** `#B8A1EA` (primary accent)
- **Animation:** Breathing pulse (1.5s cycle)
- **Use:** AICO is focused on a specific intention

### 3. Lesson Pending
- **Visual:** Amber dot, attention pulse
- **Color:** `#F59E0B` (attention)
- **Animation:** Prominent pulse (1.5s cycle)
- **Use:** Lessons awaiting review/approval

### 4. Goal Progress
- **Visual:** Progress ring (partial circle), rotating shimmer
- **Color:** `#B8A1EA` (primary accent)
- **Animation:** Clockwise rotation (2s cycle)
- **Use:** Active goal in progress (0-100%)

### 5. Goal Completed
- **Visual:** Green burst, expanding ripple
- **Color:** `#10B981` (success)
- **Animation:** Burst expansion (800ms, one-time)
- **Use:** Goal milestone/completion celebration

### 6. Multiple Items
- **Visual:** Badge with count number
- **Color:** `#B8A1EA` (primary accent)
- **Animation:** Subtle pulse
- **Use:** Multiple pending items (lessons, intentions)

## Usage

### Basic Integration

```dart
import 'package:aico_frontend/presentation/widgets/agency/agency_badge.dart';

// In your avatar widget
Stack(
  children: [
    CompanionAvatar(),
    Positioned(
      right: 4,
      bottom: 4,
      child: AgencyBadge(
        onTap: () {
          // Open agency panel
          showAgencyPanel(context);
        },
      ),
    ),
  ],
)
```

### Updating Badge State

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/presentation/providers/agency_state_provider.dart';

// Show active intention
ref.read(agencyBadgeStateNotifierProvider.notifier)
  .showActiveIntention(
    summary: "Helping with agency module",
    intensity: 0.7,
  );

// Show lesson pending
ref.read(agencyBadgeStateNotifierProvider.notifier)
  .showLessonPending(count: 3);

// Show goal progress
ref.read(agencyBadgeStateNotifierProvider.notifier)
  .showGoalProgress(
    progress: 0.65,
    goalName: "Master agency system",
  );

// Show goal completed
ref.read(agencyBadgeStateNotifierProvider.notifier)
  .showGoalCompleted(
    goalName: "Master agency system",
    duration: Duration(seconds: 3),
  );

// Hide badge
ref.read(agencyBadgeStateNotifierProvider.notifier).hide();
```

## Design Specifications

### Size
- **Text Mode:** 8px diameter dot
- **Voice Mode:** 12px diameter dot
- **Progress Ring:** 14px diameter
- **Count Badge:** 16px min height, auto width

### Colors
- **Purple:** `#B8A1EA` (active intention, progress)
- **Amber:** `#F59E0B` (lesson pending, attention)
- **Green:** `#10B981` (goal completed, success)
- **Border:** White at 30-50% opacity

### Animations
- **Pulse:** 1.5s ease-in-out, scale 0.8-1.0
- **Rotation:** 2.0s linear, continuous
- **Burst:** 800ms ease-out, scale 1.0-1.5, fade out

### Shadows & Glow
- **Ambient Glow:** 16px blur, 30-60% intensity
- **Pulsing Glow:** Animated intensity based on pulse
- **Burst Glow:** Expanding 20px blur with fade

## Interaction

### Text Mode
- **Tap:** Opens bottom sheet with full agency panel
- **Panel Contents:**
  - Current intentions (list)
  - Active goals (progress bars)
  - Pending lessons (approve/reject)
  - Quick stats

### Voice Mode
- **Visual:** Badge visible, larger size
- **Voice Query:** "What are you working on?"
- **Response:** AICO explains current focus
- **Tap:** Switches to text mode with panel

## Integration Points

### WebSocket Updates
```dart
// Listen for agency state changes
socket.on('agency.intention.updated', (data) {
  ref.read(agencyBadgeStateNotifierProvider.notifier)
    .showActiveIntention(
      summary: data['summary'],
      intensity: data['priority'] / 10.0,
    );
});

socket.on('agency.lesson.pending', (data) {
  ref.read(agencyBadgeStateNotifierProvider.notifier)
    .showLessonPending(count: data['count']);
});

socket.on('agency.goal.progress', (data) {
  ref.read(agencyBadgeStateNotifierProvider.notifier)
    .showGoalProgress(
      progress: data['progress'],
      goalName: data['name'],
    );
});
```

### REST API Integration
```dart
// Fetch current agency state
Future<void> fetchAgencyState() async {
  final response = await dio.get('/api/v1/agency/state');
  final state = response.data;
  
  if (state['active_intention'] != null) {
    ref.read(agencyBadgeStateNotifierProvider.notifier)
      .showActiveIntention(
        summary: state['active_intention']['summary'],
        intensity: state['active_intention']['priority'] / 10.0,
      );
  } else if (state['pending_lessons'] > 0) {
    ref.read(agencyBadgeStateNotifierProvider.notifier)
      .showLessonPending(count: state['pending_lessons']);
  } else {
    ref.read(agencyBadgeStateNotifierProvider.notifier).hide();
  }
}
```

## Accessibility

### Screen Reader Support
- Badge announces current state when focused
- Tap action has semantic label
- State changes trigger announcements

### Color Blind Support
- Animations provide non-color differentiation
- Progress ring uses pattern, not just color
- Count badge includes text, not just color

### Voice Description
```dart
String getAccessibilityLabel(AgencyBadgeState state) {
  switch (state.mode) {
    case AgencyBadgeMode.activeIntention:
      return "Agency active: ${state.intentionSummary}";
    case AgencyBadgeMode.lessonPending:
      return "${state.pendingCount} lessons pending review";
    case AgencyBadgeMode.goalProgress:
      return "Goal ${(state.intensity * 100).round()}% complete";
    case AgencyBadgeMode.goalCompleted:
      return "Goal completed!";
    case AgencyBadgeMode.multipleItems:
      return "${state.pendingCount} agency items";
    default:
      return "";
  }
}
```

## Testing

### Unit Tests
```dart
test('badge shows active intention', () {
  final container = ProviderContainer();
  
  container.read(agencyBadgeStateNotifierProvider.notifier)
    .showActiveIntention(summary: "Test", intensity: 0.5);
  
  final state = container.read(agencyBadgeStateNotifierProvider);
  expect(state.mode, AgencyBadgeMode.activeIntention);
  expect(state.isVisible, true);
});
```

### Widget Tests
```dart
testWidgets('badge renders correctly', (tester) async {
  await tester.pumpWidget(
    ProviderScope(
      child: MaterialApp(
        home: AgencyBadge(),
      ),
    ),
  );
  
  // Initially hidden
  expect(find.byType(AgencyBadge), findsOneWidget);
  
  // Show badge
  // ... test interaction
});
```

## Build & Generate

Run code generation after creating/modifying the provider:

```bash
cd frontend
dart run build_runner build --delete-conflicting-outputs
```

## Future Enhancements

- [ ] Haptic feedback on state changes
- [ ] Sound effects for celebrations
- [ ] Custom badge shapes for different modes
- [ ] Badge history/timeline view
- [ ] Gesture controls (swipe to dismiss)
- [ ] Badge clustering for multiple simultaneous states
