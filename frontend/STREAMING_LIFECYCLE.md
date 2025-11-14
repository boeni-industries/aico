# Streaming Lifecycle Events

This document describes the streaming lifecycle events in the AICO frontend for hooking into various stages of message streaming.

## Event Flow

```
User sends message
    ↓
[STREAMING_STARTED] - isThinking: true, content: empty
    ↓
    • Glint animation starts (3.5s cycles)
    • Particle animation starts
    • Thinking bubble shows
    ↓
First chunk arrives
    ↓
[STREAMING_CONTENT] - isThinking: false, content: streaming
    ↓
    • Text appears and streams
    • Particles continue over text
    • Glint continues on border
    ↓
Last chunk arrives
    ↓
[STREAMING_ENDED] - isThinking: false, content: complete
    ↓
    • Minimum 3s display time enforced
    • Glint animation stops
    • Particles fade out (600ms)
    • Text remains visible
```

## Current Implementation Hooks

### In `message_bubble.dart`

**Streaming Started:**
```dart
if (!_wasThinking && widget.isThinking) {
  _wasThinking = true;
  _thinkingStartTime = DateTime.now();
  _glintController.repeat(); // Start glint
  // Start particle timer
}
```

**Streaming Ended:**
```dart
if (_wasThinking && !widget.isThinking && widget.content.isNotEmpty) {
  print('🎨 [STREAMING_EVENT] Streaming ended, content received');
  
  // After minimum display time:
  _glintController.stop(); // Stop glint
  _fadeController.forward(); // Fade out particles
}
```

## State Indicators

- `widget.isThinking` - True when waiting for/receiving first chunk
- `widget.content.isEmpty` - True before any content arrives
- `widget.content.isNotEmpty` - True once streaming starts
- `_thinkingStartTime` - Timestamp when thinking began
- `_glintController.isAnimating` - True while glint is active
- `_fadeController.isAnimating` - True during particle fade-out

## Adding New Features

To add features that respond to streaming events:

1. **On Streaming Start:**
   - Add logic in the `if (!_wasThinking && widget.isThinking)` block
   - Start animations/timers here

2. **During Streaming:**
   - Check `widget.content.isNotEmpty && _wasThinking`
   - Update UI as content streams

3. **On Streaming End:**
   - Add logic in the `if (_wasThinking && !widget.isThinking)` block
   - Clean up animations/timers here
   - Respect the minimum display time delay

## Timing Constants

- `_minThinkingDuration`: 3000ms - Minimum time particles/glint show
- Glint cycle: 3500ms - Time for one full border sweep
- Fade duration: 600ms - Particle fade-out time
- Rebuild interval: 100ms - Timer for checking elapsed time

## Future Improvements

Consider creating a dedicated `StreamingState` class or provider to centralize these events:

```dart
enum StreamingPhase {
  idle,
  thinking,      // Waiting for first chunk
  streaming,     // Content arriving
  completing,    // Last chunk received, animations finishing
  complete       // All animations done
}

class StreamingStateNotifier extends StateNotifier<StreamingPhase> {
  // Centralized streaming state management
  // Emit events that widgets can listen to
}
```

This would provide cleaner separation and make it easier to add features that depend on streaming state.
